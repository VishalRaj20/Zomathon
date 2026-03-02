"""
train_baseline.py
-----------------
Trains a baseline recommendation model on train_features.csv.

Usage:
    python src/models/train_baseline.py
    python src/models/train_baseline.py --data data/processed/train_features.csv --model-out models/baseline_model.pkl
"""

import argparse
import json
import os
import pickle
import warnings
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score, classification_report
from sklearn.model_selection import GroupShuffleSplit
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

warnings.filterwarnings("ignore")

# ── Try to import LightGBM/XGBoost; fall back to Logistic Regression ─────────
try:
    import lightgbm as lgb
    BACKEND = "lightgbm"
except ImportError:
    try:
        from xgboost import XGBClassifier
        BACKEND = "xgboost"
    except ImportError:
        BACKEND = "logreg"

print(f"[train] Using backend: {BACKEND}")

# ── Column config ─────────────────────────────────────────────────────────────
# Columns that are IDs / metadata — never fed to the model
ID_COLS = ["query_id", "step_number", "candidate_item_id", "label", "split"]

# Columns to drop if present (low-signal or duplicate)
DROP_COLS = []

# Categorical columns that need ordinal/one-hot treatment (if still present as strings)
CAT_COLS = ["user_budget_segment", "rest_price_range", "rest_cuisine_id", "meal_time",
            "item_category", "split"]

# ── Metrics ───────────────────────────────────────────────────────────────────

def precision_at_k(y_true, y_score, groups, k=8):
    """Mean Precision@K across all ranking groups."""
    df = pd.DataFrame({"y": y_true, "s": y_score, "g": groups})
    scores = []
    for _, grp in df.groupby("g"):
        top = grp.nlargest(k, "s")
        scores.append(top["y"].sum() / k)
    return float(np.mean(scores)) if scores else 0.0


def recall_at_k(y_true, y_score, groups, k=8):
    """Mean Recall@K across all ranking groups."""
    df = pd.DataFrame({"y": y_true, "s": y_score, "g": groups})
    scores = []
    for _, grp in df.groupby("g"):
        total_pos = grp["y"].sum()
        if total_pos == 0:
            continue
        top = grp.nlargest(k, "s")
        scores.append(top["y"].sum() / total_pos)
    return float(np.mean(scores)) if scores else 0.0


def ndcg_at_k(y_true, y_score, groups, k=8):
    """Mean NDCG@K across all ranking groups."""
    def dcg(relevances):
        return sum(r / np.log2(i + 2) for i, r in enumerate(relevances))

    df = pd.DataFrame({"y": y_true, "s": y_score, "g": groups})
    scores = []
    for _, grp in df.groupby("g"):
        top = grp.nlargest(k, "s")["y"].tolist()
        ideal = sorted(grp["y"].tolist(), reverse=True)[:k]
        d, ideal_d = dcg(top), dcg(ideal)
        scores.append(d / ideal_d if ideal_d > 0 else 0.0)
    return float(np.mean(scores)) if scores else 0.0


def compute_all_metrics(y_true, y_score, groups, k=8):
    """Compute all ranking metrics at once."""
    return {
        "auc": float(roc_auc_score(y_true, y_score)),
        f"precision@{k}": float(precision_at_k(y_true, y_score, groups, k=k)),
        f"recall@{k}": float(recall_at_k(y_true, y_score, groups, k=k)),
        f"ndcg@{k}": float(ndcg_at_k(y_true, y_score, groups, k=k)),
    }


def segment_evaluation(df_eval, y_score, feature_cols, k=8):
    """Evaluate model performance across key segments."""
    df_eval = df_eval.copy()
    df_eval["_score"] = y_score
    
    segments = {}
    
    # Segment by meal_time
    if "meal_time" in df_eval.columns:
        meal_names = {0: "breakfast", 1: "lunch", 2: "evening_snack", 3: "dinner", 4: "late_night"}
        by_meal = {}
        for mt, grp in df_eval.groupby("meal_time"):
            if len(grp) < 10:
                continue
            label = meal_names.get(int(mt), str(mt))
            metrics = compute_all_metrics(grp["label"].values, grp["_score"].values,
                                          grp["query_id"].values, k=k)
            metrics["sample_count"] = len(grp)
            by_meal[label] = metrics
        segments["by_meal_time"] = by_meal
    
    # Segment by user budget segment
    if "user_budget_segment" in df_eval.columns:
        by_budget = {}
        for bs, grp in df_eval.groupby("user_budget_segment"):
            if len(grp) < 10:
                continue
            metrics = compute_all_metrics(grp["label"].values, grp["_score"].values,
                                          grp["query_id"].values, k=k)
            metrics["sample_count"] = len(grp)
            by_budget[str(bs)] = metrics
        segments["by_user_budget"] = by_budget
    
    # Segment by restaurant cuisine
    if "rest_cuisine_id" in df_eval.columns:
        by_cuisine = {}
        for cid, grp in df_eval.groupby("rest_cuisine_id"):
            if len(grp) < 10:
                continue
            metrics = compute_all_metrics(grp["label"].values, grp["_score"].values,
                                          grp["query_id"].values, k=k)
            metrics["sample_count"] = len(grp)
            by_cuisine[str(cid)] = metrics
        segments["by_cuisine"] = by_cuisine
    
    # Segment by cart size (empty vs small vs medium vs large)
    if "cart_item_count" in df_eval.columns:
        bins = pd.cut(df_eval["cart_item_count"], bins=[-1, 0, 2, 4, 100],
                       labels=["empty", "small(1-2)", "medium(3-4)", "large(5+)"])
        by_cart = {}
        for label, grp in df_eval.groupby(bins, observed=True):
            if len(grp) < 10:
                continue
            metrics = compute_all_metrics(grp["label"].values, grp["_score"].values,
                                          grp["query_id"].values, k=k)
            metrics["sample_count"] = len(grp)
            by_cart[str(label)] = metrics
        segments["by_cart_size"] = by_cart
    
    return segments


def extract_feature_importance(model, feature_cols, backend):
    """Extract and rank feature importances."""
    if backend == "lightgbm":
        importances = model.feature_importances_
    elif backend == "xgboost":
        importances = model.feature_importances_
    elif backend == "logreg":
        # For pipeline (scaler + clf)
        importances = np.abs(model.named_steps["clf"].coef_[0])
    else:
        return []
    
    feat_imp = sorted(zip(feature_cols, importances.tolist()), key=lambda x: x[1], reverse=True)
    return [{"feature": name, "importance": round(imp, 4)} for name, imp in feat_imp]


# ── Data loading & prep ───────────────────────────────────────────────────────

def load_data(csv_path: str):
    print(f"[train] Loading {csv_path} ...")
    df = pd.read_csv(csv_path)
    print(f"[train] Loaded {len(df):,} rows, {df.shape[1]} columns")
    print(f"[train] Label distribution:\n{df['label'].value_counts().to_string()}")

    # Fill nulls defensively
    for col in df.select_dtypes(include="number").columns:
        df[col] = df[col].fillna(df[col].median())
    for col in df.select_dtypes(include="object").columns:
        df[col] = df[col].fillna("unknown")

    return df


def get_feature_cols(df: pd.DataFrame):
    skip = set(ID_COLS) | set(DROP_COLS)
    return [c for c in df.columns if c not in skip]


def encode_categoricals(df: pd.DataFrame, feature_cols):
    """Label-encode any remaining string columns."""
    from sklearn.preprocessing import LabelEncoder
    encoders = {}
    for col in feature_cols:
        if df[col].dtype == object:
            le = LabelEncoder()
            df[col] = le.fit_transform(df[col].astype(str))
            encoders[col] = le
    return df, encoders


def make_split(df: pd.DataFrame):
    """
    If a 'split' column exists, use it (temporal split).
    Otherwise fall back to GroupShuffleSplit by query_id (80/20).
    """
    if "split" in df.columns:
        train = df[df["split"] == "train"].copy()
        val   = df[df["split"] == "val"].copy()
        test  = df[df["split"] == "test"].copy() if "test" in df["split"].values else pd.DataFrame()
        print(f"[train] Temporal split → train={len(train):,}  val={len(val):,}  test={len(test):,}")
    else:
        gss = GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=42)
        groups = df["query_id"].values
        idx_tr, idx_va = next(gss.split(df, groups=groups))
        train, val = df.iloc[idx_tr].copy(), df.iloc[idx_va].copy()
        test = pd.DataFrame()
        print(f"[train] GroupShuffleSplit → train={len(train):,}  val={len(val):,}")
    return train, val, test


# ── Model builders ────────────────────────────────────────────────────────────

def build_lightgbm(X_tr, y_tr, X_va, y_va):
    model = lgb.LGBMClassifier(
        objective="binary",
        n_estimators=1000,
        learning_rate=0.03,
        num_leaves=127,
        min_child_samples=15,
        subsample=0.85,
        colsample_bytree=0.85,
        reg_alpha=0.1,
        reg_lambda=0.5,
        random_state=42,
        n_jobs=-1,
        verbose=-1,
    )
    model.fit(
        X_tr, y_tr,
        eval_set=[(X_va, y_va)],
        callbacks=[lgb.early_stopping(100, verbose=False), lgb.log_evaluation(200)],
    )
    return model


def build_xgboost(X_tr, y_tr, X_va, y_va):
    model = XGBClassifier(
        n_estimators=1000,
        learning_rate=0.03,
        max_depth=8,
        subsample=0.85,
        colsample_bytree=0.85,
        reg_alpha=0.1,
        reg_lambda=0.5,
        eval_metric="logloss",
        early_stopping_rounds=100,
        random_state=42,
        n_jobs=-1,
        verbosity=0,
    )
    model.fit(X_tr, y_tr, eval_set=[(X_va, y_va)], verbose=200)
    return model


def build_logreg(X_tr, y_tr):
    pipe = Pipeline([
        ("scaler", StandardScaler()),
        ("clf", LogisticRegression(max_iter=2000, C=0.5, class_weight='balanced', random_state=42, n_jobs=-1)),
    ])
    pipe.fit(X_tr, y_tr)
    return pipe


# ── Main ──────────────────────────────────────────────────────────────────────

def train(data_path: str, model_out: str, k: int = 8):
    df = load_data(data_path)
    df, encoders = encode_categoricals(df, get_feature_cols(df))

    train_df, val_df, test_df = make_split(df)
    feature_cols = get_feature_cols(df)

    X_tr, y_tr = train_df[feature_cols].values, train_df["label"].values
    X_va, y_va = val_df[feature_cols].values,   val_df["label"].values
    q_va = val_df["query_id"].values

    print(f"[train] Feature count: {len(feature_cols)}")

    if BACKEND == "lightgbm":
        model = build_lightgbm(X_tr, y_tr, X_va, y_va)
    elif BACKEND == "xgboost":
        model = build_xgboost(X_tr, y_tr, X_va, y_va)
    else:
        print("[train] LightGBM/XGBoost not found — using Logistic Regression")
        model = build_logreg(X_tr, y_tr)

    probs_va = model.predict_proba(X_va)[:, 1]

    # ── Validation Metrics
    val_metrics = compute_all_metrics(y_va, probs_va, q_va, k=k)

    print("\n" + "=" * 50)
    print("  VALIDATION SET RESULTS")
    print("=" * 50)
    for name, val in val_metrics.items():
        print(f"  {name:<20}: {val:.4f}")
    print("=" * 50)

    # ── Test Set Metrics (if available)
    test_metrics = {}
    if len(test_df) > 0:
        X_te = test_df[feature_cols].values
        y_te = test_df["label"].values
        q_te = test_df["query_id"].values
        probs_te = model.predict_proba(X_te)[:, 1]
        test_metrics = compute_all_metrics(y_te, probs_te, q_te, k=k)

        print("\n" + "=" * 50)
        print("  TEST SET RESULTS (holdout)")
        print("=" * 50)
        for name, val in test_metrics.items():
            print(f"  {name:<20}: {val:.4f}")
        print("=" * 50)

    # ── Feature Importance
    feat_importance = extract_feature_importance(model, feature_cols, BACKEND)
    print(f"\n[train] Top 10 features:")
    for fi in feat_importance[:10]:
        print(f"  {fi['feature']:<35} {fi['importance']:.4f}")

    # ── Segment-level Evaluation
    print("\n[train] Running segment-level evaluation...")
    seg_eval = segment_evaluation(val_df, probs_va, feature_cols, k=k)
    for seg_name, seg_data in seg_eval.items():
        print(f"\n  {seg_name}:")
        for label, metrics in seg_data.items():
            auc_val = metrics.get("auc", 0)
            pk_val = metrics.get(f"precision@{k}", 0)
            rk_val = metrics.get(f"recall@{k}", 0)
            n = metrics.get("sample_count", 0)
            print(f"    {label:<18} AUC={auc_val:.3f}  P@{k}={pk_val:.3f}  R@{k}={rk_val:.3f}  (n={n})")

    # ── Save Model
    payload = {
        "model": model,
        "feature_cols": feature_cols,
        "encoders": encoders,
        "backend": BACKEND,
        "metrics": val_metrics,
    }
    Path(model_out).parent.mkdir(parents=True, exist_ok=True)
    with open(model_out, "wb") as f:
        pickle.dump(payload, f)
    print(f"\n[train] Model saved → {model_out}")

    # ── Save Evaluation Report
    report = {
        "timestamp": datetime.now().isoformat(),
        "backend": BACKEND,
        "dataset": {
            "total_rows": len(df),
            "train_rows": len(train_df),
            "val_rows": len(val_df),
            "test_rows": len(test_df),
            "feature_count": len(feature_cols),
            "positive_ratio": float(df["label"].mean()),
        },
        "validation_metrics": val_metrics,
        "test_metrics": test_metrics,
        "feature_importance": feat_importance,
        "segment_evaluation": seg_eval,
    }
    report_path = str(Path(model_out).parent / "evaluation_report.json")
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)
    print(f"[train] Evaluation report saved → {report_path}")

    return payload


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data",      default="data/processed/train_features.csv")
    parser.add_argument("--model-out", default="models/baseline_model.pkl")
    parser.add_argument("--k",         type=int, default=8)
    args = parser.parse_args()
    train(args.data, args.model_out, args.k)
