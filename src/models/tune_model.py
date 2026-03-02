"""
tune_model.py
-------------
Optuna-based hyperparameter tuning for LightGBM.

Usage:
    python src/models/tune_model.py
    python src/models/tune_model.py --n-trials 50 --data data/processed/train_features.csv
"""

import argparse
import json
import pickle
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score
from sklearn.preprocessing import LabelEncoder

warnings.filterwarnings("ignore")

try:
    import optuna
    optuna.logging.set_verbosity(optuna.logging.WARNING)
except ImportError:
    print("[tune] Optuna not installed. Run: pip install optuna")
    exit(1)

try:
    import lightgbm as lgb
except ImportError:
    print("[tune] LightGBM not installed. Run: pip install lightgbm")
    exit(1)


ID_COLS = ["query_id", "step_number", "candidate_item_id", "label", "split"]


def load_and_split(csv_path):
    df = pd.read_csv(csv_path)

    # Fill nulls
    for col in df.select_dtypes(include="number").columns:
        df[col] = df[col].fillna(df[col].median())
    for col in df.select_dtypes(include="object").columns:
        df[col] = df[col].fillna("unknown")

    # Encode categoricals
    encoders = {}
    feature_cols = [c for c in df.columns if c not in ID_COLS]
    for col in feature_cols:
        if df[col].dtype == object:
            le = LabelEncoder()
            df[col] = le.fit_transform(df[col].astype(str))
            encoders[col] = le

    if "split" in df.columns:
        train = df[df["split"] == "train"].copy()
        val = df[df["split"] == "val"].copy()
    else:
        from sklearn.model_selection import GroupShuffleSplit
        gss = GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=42)
        idx_tr, idx_va = next(gss.split(df, groups=df["query_id"].values))
        train, val = df.iloc[idx_tr].copy(), df.iloc[idx_va].copy()

    return train, val, feature_cols, encoders


def precision_at_k(y_true, y_score, groups, k=8):
    df = pd.DataFrame({"y": y_true, "s": y_score, "g": groups})
    scores = []
    for _, grp in df.groupby("g"):
        top = grp.nlargest(k, "s")
        scores.append(top["y"].sum() / k)
    return float(np.mean(scores)) if scores else 0.0


def objective(trial, X_tr, y_tr, X_va, y_va, q_va):
    params = {
        "objective": "binary",
        "n_estimators": trial.suggest_int("n_estimators", 300, 2000, step=100),
        "learning_rate": trial.suggest_float("learning_rate", 0.005, 0.1, log=True),
        "num_leaves": trial.suggest_int("num_leaves", 31, 255),
        "min_child_samples": trial.suggest_int("min_child_samples", 5, 50),
        "subsample": trial.suggest_float("subsample", 0.6, 1.0),
        "colsample_bytree": trial.suggest_float("colsample_bytree", 0.6, 1.0),
        "reg_alpha": trial.suggest_float("reg_alpha", 1e-3, 10.0, log=True),
        "reg_lambda": trial.suggest_float("reg_lambda", 1e-3, 10.0, log=True),
        "max_depth": trial.suggest_int("max_depth", -1, 12),
        "random_state": 42,
        "n_jobs": -1,
        "verbose": -1,
    }

    model = lgb.LGBMClassifier(**params)
    model.fit(
        X_tr, y_tr,
        eval_set=[(X_va, y_va)],
        callbacks=[lgb.early_stopping(50, verbose=False)],
    )
    probs = model.predict_proba(X_va)[:, 1]
    auc = roc_auc_score(y_va, probs)
    p_at_k = precision_at_k(y_va, probs, q_va, k=8)

    # Composite objective: AUC + Precision@8
    return 0.6 * auc + 0.4 * p_at_k


def tune(data_path, n_trials=30, model_out="models/baseline_model.pkl"):
    print(f"[tune] Loading data...")
    train_df, val_df, feature_cols, encoders = load_and_split(data_path)

    X_tr, y_tr = train_df[feature_cols].values, train_df["label"].values
    X_va, y_va = val_df[feature_cols].values, val_df["label"].values
    q_va = val_df["query_id"].values

    print(f"[tune] Features: {len(feature_cols)}, Train: {len(train_df):,}, Val: {len(val_df):,}")
    print(f"[tune] Starting Optuna with {n_trials} trials...\n")

    study = optuna.create_study(direction="maximize",
                                 sampler=optuna.samplers.TPESampler(seed=42))
    study.optimize(lambda trial: objective(trial, X_tr, y_tr, X_va, y_va, q_va),
                   n_trials=n_trials, show_progress_bar=True)

    print(f"\n[tune] Best trial:")
    print(f"  Score: {study.best_trial.value:.4f}")
    print(f"  Params:")
    for k, v in study.best_trial.params.items():
        print(f"    {k}: {v}")

    # Retrain with best params
    print(f"\n[tune] Retraining final model with best params...")
    best_params = study.best_trial.params
    best_params.update({"objective": "binary", "random_state": 42, "n_jobs": -1, "verbose": -1})

    final_model = lgb.LGBMClassifier(**best_params)
    final_model.fit(
        X_tr, y_tr,
        eval_set=[(X_va, y_va)],
        callbacks=[lgb.early_stopping(100, verbose=False), lgb.log_evaluation(200)],
    )

    probs = final_model.predict_proba(X_va)[:, 1]
    auc = roc_auc_score(y_va, probs)
    p_at_k = precision_at_k(y_va, probs, q_va, k=8)

    print(f"\n  Final Validation AUC: {auc:.4f}")
    print(f"  Final Precision@8:   {p_at_k:.4f}")

    # Save
    payload = {
        "model": final_model,
        "feature_cols": feature_cols,
        "encoders": encoders,
        "backend": "lightgbm",
        "metrics": {"auc": auc, "precision@8": p_at_k},
        "tuning": {
            "best_params": study.best_trial.params,
            "best_score": study.best_trial.value,
            "n_trials": n_trials,
        },
    }
    Path(model_out).parent.mkdir(parents=True, exist_ok=True)
    with open(model_out, "wb") as f:
        pickle.dump(payload, f)
    print(f"[tune] Tuned model saved → {model_out}")

    # Save tuning results
    tuning_report = {
        "best_params": study.best_trial.params,
        "best_score": study.best_trial.value,
        "n_trials": n_trials,
        "final_auc": auc,
        "final_precision@8": p_at_k,
        "all_trials": [
            {"number": t.number, "value": t.value, "params": t.params}
            for t in study.trials
        ],
    }
    report_path = str(Path(model_out).parent / "tuning_report.json")
    with open(report_path, "w") as f:
        json.dump(tuning_report, f, indent=2, default=str)
    print(f"[tune] Tuning report saved → {report_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", default="data/processed/train_features.csv")
    parser.add_argument("--model-out", default="models/baseline_model.pkl")
    parser.add_argument("--n-trials", type=int, default=30)
    args = parser.parse_args()
    tune(args.data, args.n_trials, args.model_out)
