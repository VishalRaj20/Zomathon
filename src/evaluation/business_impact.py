"""
business_impact.py
------------------
Simulates business impact metrics for the CSAO recommendation system.
Computes projected AOV lift, acceptance rates, and segment-level breakdown.

Usage:
    python src/evaluation/business_impact.py
"""

import sys
import json
import warnings
from pathlib import Path
from datetime import datetime

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "data" / "raw"
FEATURES_PATH = ROOT / "data" / "processed" / "train_features.csv"
MODEL_PATH = ROOT / "models" / "baseline_model.pkl"


def load_model():
    import pickle
    with open(MODEL_PATH, "rb") as f:
        return pickle.load(f)


def main():
    print("=" * 70)
    print("  CSAO — Business Impact Analysis")
    print("=" * 70)

    # Load data
    items = pd.read_csv(RAW_DIR / "items.csv")
    orders = pd.read_csv(RAW_DIR / "orders.csv")
    order_items = pd.read_csv(RAW_DIR / "order_items.csv")
    users = pd.read_csv(RAW_DIR / "users.csv")

    # ── Baseline Metrics (without CSAO)
    print("\n  1. BASELINE METRICS (without CSAO)")
    print("  " + "-" * 50)

    # Join order_items with items to get prices
    oi = order_items.merge(items[["item_id", "price", "category", "name"]], on="item_id", how="left")
    order_totals = oi.groupby("order_id").agg(
        total_value=("price", "sum"),
        item_count=("item_id", "count"),
    ).reset_index()

    baseline_aov = order_totals["total_value"].mean()
    baseline_items_per_order = order_totals["item_count"].mean()
    total_orders = len(orders)
    
    print(f"    Total orders:          {total_orders:,}")
    print(f"    Baseline AOV:          ₹{baseline_aov:.2f}")
    print(f"    Avg items/order:       {baseline_items_per_order:.2f}")

    # ── Projected CSAO Impact
    print("\n  2. PROJECTED CSAO IMPACT")
    print("  " + "-" * 50)

    # Model-based acceptance rate estimation
    payload = load_model()
    model_metrics = payload.get("metrics", {})
    model_auc = model_metrics.get("auc", 0.80)

    # Conservative acceptance rate based on model AUC
    # Industry benchmark: 15-25% acceptance rate for well-tuned recommendation systems
    # We scale based on our AUC relative to random (0.5)
    if model_auc >= 0.85:
        acceptance_rate = 0.22  # Good model → higher acceptance
    elif model_auc >= 0.80:
        acceptance_rate = 0.18
    elif model_auc >= 0.75:
        acceptance_rate = 0.15
    else:
        acceptance_rate = 0.12

    # Average add-on item price from the most popular add-on categories
    addon_categories = ["drink", "side", "dessert", "starter"]
    addon_items = items[items["category"].isin(addon_categories)]
    avg_addon_price = addon_items["price"].mean() if len(addon_items) > 0 else 100.0

    # Projected metrics
    csao_rail_show_rate = 0.85  # 85% of orders see the CSAO rail
    orders_with_rail = total_orders * csao_rail_show_rate
    accepted_addons = orders_with_rail * acceptance_rate
    total_addon_revenue = accepted_addons * avg_addon_price
    aov_lift = (avg_addon_price * acceptance_rate * csao_rail_show_rate)
    aov_lift_pct = (aov_lift / baseline_aov) * 100
    new_aov = baseline_aov + aov_lift
    csao_attach_rate = acceptance_rate * csao_rail_show_rate
    avg_items_lift = acceptance_rate * csao_rail_show_rate

    print(f"    Model AUC:             {model_auc:.4f}")
    print(f"    Projected acceptance:  {acceptance_rate*100:.0f}%")
    print(f"    CSAO rail show rate:   {csao_rail_show_rate*100:.0f}%")
    print(f"    Avg add-on price:      ₹{avg_addon_price:.2f}")
    print(f"    ─────────────────────────────────────")
    print(f"    AOV Lift:              ₹{aov_lift:.2f} (+{aov_lift_pct:.1f}%)")
    print(f"    New projected AOV:     ₹{new_aov:.2f}")
    print(f"    CSAO attach rate:      {csao_attach_rate*100:.1f}%")
    print(f"    Avg items/order lift:  +{avg_items_lift:.2f}")
    print(f"    Total add-on orders:   {accepted_addons:,.0f}")
    print(f"    Total add-on revenue:  ₹{total_addon_revenue:,.0f}")

    # ── Segment Breakdown
    print("\n  3. SEGMENT-LEVEL BREAKDOWN")
    print("  " + "-" * 50)

    # By meal time
    if "order_time" in orders.columns or "timestamp" in orders.columns:
        time_col = "order_time" if "order_time" in orders.columns else "timestamp"
        orders["_hour"] = pd.to_datetime(orders[time_col], errors="coerce").dt.hour
        meal_map = {
            "breakfast (6-11)": orders["_hour"].between(6, 10),
            "lunch (11-16)": orders["_hour"].between(11, 15),
            "evening (16-19)": orders["_hour"].between(16, 18),
            "dinner (19-23)": orders["_hour"].between(19, 22),
            "late_night (23-6)": (orders["_hour"] >= 23) | (orders["_hour"] < 6),
        }
        print("\n    By Meal Time:")
        for meal, mask in meal_map.items():
            meal_orders = orders[mask]
            if len(meal_orders) > 0:
                meal_oi = oi[oi["order_id"].isin(meal_orders["order_id"])]
                meal_aov = meal_oi.groupby("order_id")["price"].sum().mean()
                pct = len(meal_orders) / total_orders * 100
                projected_aov = meal_aov + aov_lift
                print(f"      {meal:<22} AOV=₹{meal_aov:>7.0f}  →  ₹{projected_aov:>7.0f}  ({pct:.0f}% of orders)")

    # By user segment
    if "budget_segment" in users.columns:
        orders_u = orders.merge(users[["user_id", "budget_segment"]], on="user_id", how="left")
        print("\n    By User Segment:")
        for seg, grp in orders_u.groupby("budget_segment"):
            seg_oi = oi[oi["order_id"].isin(grp["order_id"])]
            if len(seg_oi) == 0:
                continue
            seg_aov = seg_oi.groupby("order_id")["price"].sum().mean()
            seg_pct = len(grp) / total_orders * 100
            # Premium users have higher acceptance rates
            seg_acceptance = acceptance_rate * (1.2 if seg == "premium" else 1.0 if seg == "mid" else 0.8)
            seg_lift = avg_addon_price * seg_acceptance * csao_rail_show_rate
            print(f"      {seg:<12} AOV=₹{seg_aov:>7.0f}  lift=₹{seg_lift:>5.0f}  accept={seg_acceptance*100:.0f}%  ({seg_pct:.0f}% of orders)")

    # ── C2O Impact
    print("\n  4. CART-TO-ORDER (C2O) IMPACT")
    print("  " + "-" * 50)
    baseline_c2o = 0.72  # Industry average
    # Better recommendations → more complete meals → higher C2O
    c2o_lift = 0.03 if model_auc >= 0.80 else 0.01
    new_c2o = baseline_c2o + c2o_lift
    print(f"    Baseline C2O:          {baseline_c2o*100:.0f}%")
    print(f"    Projected C2O:         {new_c2o*100:.0f}% (+{c2o_lift*100:.0f}pp)")
    print(f"    Additional orders:     {total_orders * c2o_lift:,.0f}")

    # ── Save Report
    report = {
        "timestamp": datetime.now().isoformat(),
        "baseline": {
            "total_orders": total_orders,
            "aov": round(baseline_aov, 2),
            "avg_items_per_order": round(baseline_items_per_order, 2),
        },
        "projected_impact": {
            "model_auc": round(model_auc, 4),
            "acceptance_rate": acceptance_rate,
            "csao_rail_show_rate": csao_rail_show_rate,
            "avg_addon_price": round(avg_addon_price, 2),
            "aov_lift": round(aov_lift, 2),
            "aov_lift_pct": round(aov_lift_pct, 2),
            "new_aov": round(new_aov, 2),
            "csao_attach_rate": round(csao_attach_rate, 4),
            "projected_addon_orders": int(accepted_addons),
            "projected_addon_revenue": round(total_addon_revenue, 2),
        },
        "c2o_impact": {
            "baseline_c2o": baseline_c2o,
            "projected_c2o": new_c2o,
            "c2o_lift_pp": c2o_lift * 100,
        },
    }

    report_path = ROOT / "models" / "business_impact_report.json"
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)
    print(f"\n  Report saved → {report_path}")


if __name__ == "__main__":
    main()
