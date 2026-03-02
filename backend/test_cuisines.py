import pandas as pd
from pathlib import Path

data_dir = Path(r"d:\zomathon\data\raw")
items = pd.read_csv(data_dir / "items.csv")
restaurants = pd.read_csv(data_dir / "restaurants.csv")

# Find Burger
burger = items[items["name"].str.contains("Burger", case=False, na=False)].head(1)
raita = items[items["name"].str.contains("Raita", case=False, na=False)].head(1)

print("Burger:", burger[["item_id", "name", "restaurant_id"]].to_dict('records'))
print("Raita:", raita[["item_id", "name", "restaurant_id"]].to_dict('records'))

if not burger.empty:
    r_id = burger.iloc[0]["restaurant_id"]
    r_c = restaurants[restaurants["restaurant_id"] == r_id][["name", "cuisine"]]
    print("Burger Restaurant Cuisine:", r_c.to_dict('records'))

if not raita.empty:
    r_id = raita.iloc[0]["restaurant_id"]
    r_c = restaurants[restaurants["restaurant_id"] == r_id][["name", "cuisine"]]
    print("Raita Restaurant Cuisine:", r_c.to_dict('records'))
