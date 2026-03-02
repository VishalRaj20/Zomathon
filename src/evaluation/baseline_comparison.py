"""
baseline_comparison.py
----------------------
Compares the trained LightGBM model against baseline strategies to demonstrate
model lift. Required for Evaluation Criteria 4 & 6.

Baselines:
  1. Random — shuffle candidates randomly
  2. Popularity — rank by global popularity score only
  3. Same-Category — rank by popularity within missing categories
  4. Our Model — LightGBM + re-ranking

Usage:
    python src/evaluation/baseline_comparison.py
"""

import sys
import json
import pickle
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

warnings.filterwarnings("ignore")

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

ROOT = Path(__file__).resolve().parents[2]


def precision_at_k(y_true, y_score, groups, k=8):
    df = pd.DataFrame({"y": y_true, "s": y_score, "g": groups})
    scores = []
    for _, grp in df.groupby("g"):
        top = grp.nlargest(k, "s")
        scores.append(top["y"].sum() / k)
    return float(np.mean(scores)) if scores else 0.0


def recall_at_k(y_true, y_score, groups, k=8):
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
    def dcg(rels):
        return sum(r / np.log2(i + 2) for i, r in enumerate(rels))
    df = pd.DataFrame({"y": y_true, "s": y_score, "g": groups})
    scores = []
    for _, grp in df.groupby("g"):
        top = grp.nlargest(k, "s")["y"].tolist()
        ideal = sorted(grp["y"].tolist(), reverse=True)[:k]
        d, ideal_d = dcg(top), dcg(ideal)
        scores.append(d / ideal_d if ideal_d > 0 else 0.0)
    return float(np.mean(scores)) if scores else 0.0


def evaluate(name, y_true, y_score, groups, k=8):
    try:
        auc = float(roc_auc_score(y_true, y_score))
    except ValueError:
        auc = 0.5
    return {
        "strategy": name,
        "auc": round(auc, 4),
        f"precision@{k}": round(precision_at_k(y_true, y_score, groups, k), 4),
        f"recall@{k}": round(recall_at_k(y_true, y_score, groups, k), 4),
        f"ndcg@{k}": round(ndcg_at_k(y_true, y_score, groups, k), 4),
    }


def main():
    k = 8
    data_path = ROOT / "data" / "processed" / "train_features.csv"
    model_path = ROOT / "models" / "baseline_model.pkl"

    print("=" * 70)
    print("  BASELINE COMPARISON — Model vs Heuristic Strategies")
    print("=" * 70)

    # Load data
    print("\n  Loading data...")
    df = pd.read_csv(data_path)
    for col in df.select_dtypes(include="number").columns:
        df[col] = df[col].fillna(df[col].median())
    for col in df.select_dtypes(include="object").columns:
        df[col] = df[col].fillna("unknown")

    # Use test split
    if "split" in df.columns and "test" in df["split"].values:
        test_df = df[df["split"] == "test"].copy()
    elif "split" in df.columns and "val" in df["split"].values:
        test_df = df[df["split"] == "val"].copy()
    else:
        test_df = df.sample(frac=0.2, random_state=42).copy()

    y_true = test_df["label"].values
    groups = test_df["query_id"].values
    print(f"  Test set: {len(test_df):,} rows, {test_df['query_id'].nunique()} queries")

    results = []

    # ── Baseline 1: Random
    np.random.seed(42)
    random_scores = np.random.rand(len(test_df))
    results.append(evaluate("Random", y_true, random_scores, groups, k))

    # ── Baseline 2: Popularity Only
    if "item_popularity" in test_df.columns:
        pop_scores = test_df["item_popularity"].values
        results.append(evaluate("Popularity-Only", y_true, pop_scores, groups, k))

    # ── Baseline 3: Price-Weighted Popularity
    if "item_popularity" in test_df.columns and "item_price" in test_df.columns:
        max_price = test_df["item_price"].max()
        price_pop = test_df["item_popularity"].values + (1 - test_df["item_price"].values / max(max_price, 1)) * 20
        results.append(evaluate("Price-Weighted Pop", y_true, price_pop, groups, k))

    # ── Baseline 4: Category-Aware Heuristic
    if "item_category" in test_df.columns and "item_popularity" in test_df.columns:
        cat_missing = test_df.get("item_category_missing_in_cart", pd.Series(np.ones(len(test_df))))
        cat_scores = test_df["item_popularity"].values + (cat_missing.values > 0).astype(float) * 30
        results.append(evaluate("Category-Aware Heuristic", y_true, cat_scores, groups, k))

    # ── Our Model: LightGBM
    print("  Scoring with trained model...")
    with open(model_path, "rb") as f:
        payload = pickle.load(f)
    model = payload["model"]
    feature_cols = payload["feature_cols"]
    encoders = payload.get("encoders", {})

    # Encode categoricals same as training
    from sklearn.preprocessing import LabelEncoder
    for col, le in encoders.items():
        if col in test_df.columns and test_df[col].dtype == object:
            known = set(le.classes_)
            test_df[col] = test_df[col].apply(lambda x: le.transform([x])[0] if x in known else 0)

    X_test = test_df[feature_cols].fillna(0).values
    model_scores = model.predict_proba(X_test)[:, 1]
    results.append(evaluate("LightGBM (Ours)", y_true, model_scores, groups, k))

    # ── Print Results
    print("\n" + "=" * 70)
    print(f"  {'Strategy':<25} {'AUC':>8} {'P@'+str(k):>8} {'R@'+str(k):>8} {'NDCG@'+str(k):>8}")
    print("  " + "-" * 63)
    for r in results:
        n = r["strategy"]
        print(f"  {n:<25} {r['auc']:>8.4f} {r[f'precision@{k}']:>8.4f} {r[f'recall@{k}']:>8.4f} {r[f'ndcg@{k}']:>8.4f}")
    print("=" * 70)

    # Compute lift over baselines
    model_r = results[-1]
    print(f"\n  LIFT OVER BASELINES:")
    for r in results[:-1]:
        auc_lift = ((model_r["auc"] - r["auc"]) / max(r["auc"], 0.001)) * 100
        ndcg_lift = ((model_r[f"ndcg@{k}"] - r[f"ndcg@{k}"]) / max(r[f"ndcg@{k}"], 0.001)) * 100
        print(f"    vs {r['strategy']:<25} AUC: +{auc_lift:.1f}%  NDCG: +{ndcg_lift:.1f}%")

    # Save report
    report = {
        "test_rows": len(test_df),
        "test_queries": int(test_df["query_id"].nunique()),
        "results": results,
        "model_lifts": {
            r["strategy"]: {
                "auc_lift_pct": round(((model_r["auc"] - r["auc"]) / max(r["auc"], 0.001)) * 100, 2),
                "ndcg_lift_pct": round(((model_r[f"ndcg@{k}"] - r[f"ndcg@{k}"]) / max(r[f"ndcg@{k}"], 0.001)) * 100, 2),
            }
            for r in results[:-1]
        },
    }
    report_path = ROOT / "models" / "baseline_comparison_report.json"
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)
    print(f"\n  Report saved → {report_path}")


if __name__ == "__main__":
    main()
