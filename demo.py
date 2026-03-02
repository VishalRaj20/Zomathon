"""
demo.py
-------
CLI demo — no FastAPI needed.

Usage:
    python demo.py
    python demo.py --user 42 --restaurant 7 --cart 101 205 --hour 20
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.inference.recommender import recommend, _get_items


def print_recs(user_id, restaurant_id, cart_items, ts, top_k=8):
    print("\n" + "=" * 55)
    print(f"  [Add-on Recommendations]")
    print("=" * 55)
    print(f"  User ID       : {user_id}")
    print(f"  Restaurant ID : {restaurant_id}")
    print(f"  Cart items    : {cart_items or '(empty)'}")
    print(f"  Time          : {ts.strftime('%A %H:%M')}")
    print("-" * 55)

    recs = recommend(user_id, restaurant_id, cart_items, ts, top_k=top_k)

    if not recs:
        print("  No recommendations generated.")
    else:
        items = _get_items()
        print(f"  Top-{top_k} recommended add-ons:\n")
        for rank, item_id in enumerate(recs, 1):
            row = items[items["item_id"] == item_id]
            if not row.empty:
                r = row.iloc[0]
                name  = r.get("name",     "Unknown item")
                cat   = r.get("category", "?")
                price = r.get("price",    0)
                veg   = "[Veg]" if r.get("is_veg", 0) == 1 else "[Non-Veg]"
                print(f"  {rank:2}. {veg}  {name:<35} [{cat:8}]  Rs {price:.0f}")
            else:
                print(f"  {rank:2}.  item_id={item_id}")

    print("=" * 55 + "\n")
    return recs


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Add-on Recommender Demo")
    parser.add_argument("--user",       type=int,  default=1)
    parser.add_argument("--restaurant", type=int,  default=1)
    parser.add_argument("--cart",       type=int,  nargs="*", default=[])
    parser.add_argument("--hour",       type=int,  default=19,
                        help="Hour of day (24h, local IST) to simulate")
    parser.add_argument("--top-k",      type=int,  default=8)
    args = parser.parse_args()

    ts = datetime(2024, 11, 15, args.hour, 30)
    print_recs(args.user, args.restaurant, args.cart, ts, top_k=args.top_k)