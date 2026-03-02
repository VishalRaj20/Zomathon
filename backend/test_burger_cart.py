import sys
from pathlib import Path

ROOT = Path(r"d:\zomathon")
sys.path.insert(0, str(ROOT))

from src.inference.recommender import recommend, _get_items, _get_restaurants
from datetime import datetime
import pandas as pd

items_df = _get_items()
rests_df = _get_restaurants()

burger = items_df[items_df["name"].str.contains("Classic Cheese Burger", case=False, na=False)].head(1)
if burger.empty:
    print("Burger not found")
    sys.exit(1)

burger_id = int(burger.iloc[0]["item_id"])
burger_rid = int(burger.iloc[0]["restaurant_id"])

print(f"Burger ID: {burger_id}, Rest ID: {burger_rid}")

rest_info = rests_df[rests_df["restaurant_id"] == burger_rid]
print("Burger Restaurant Cuisine:", rest_info.iloc[0]["cuisine"] if not rest_info.empty else "None")

# Recommend with Burger
ts = datetime(2024, 11, 15, 12, 30) # Daytime
recs = recommend(27, burger_rid, [burger_id], ts, top_k=8)

print("\nRecommendations with Burger in Cart:")
for iid in recs:
    row = items_df[items_df["item_id"] == iid]
    if not row.empty:
        r = row.iloc[0]
        cat = r.get("category", "?")
        name = r.get("name", "Unknown")
        rid = r.get("restaurant_id")
        rc_info = rests_df[rests_df["restaurant_id"] == rid]
        cand_cuis = rc_info.iloc[0]["cuisine"] if not rc_info.empty else "Unknown"
        pop = r.get("popularity_score", 0)
        print(f" - [{cat}] {name} | Pop: {pop} | Rest: {rid} | Cuisine: {cand_cuis}")
