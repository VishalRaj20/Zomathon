import sys
from pathlib import Path

# Adjust import path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.inference.recommender import recommend, _get_items, _load_model
import pandas as pd
from datetime import datetime

ts = datetime(2024, 11, 15, 21, 30) # Night time
recs = recommend(1, 0, [], ts, top_k=8)

items_df = _get_items()
print("\nFinal Recommended Items output:")
for iid in recs:
    row = items_df[items_df["item_id"] == iid]
    if not row.empty:
        r = row.iloc[0]
        cat = r.get("category", "?")
        name = r.get("name", "Unknown")
        print(f" - [{cat}] {name}")
