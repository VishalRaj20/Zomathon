"""
recommender.py
--------------
Loads the trained model and recommends add-on items given a user, restaurant,
current cart, and timestamp.

Usage (standalone test):
    python src/inference/recommender.py
"""

import os
import pickle
import warnings
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

# ── Paths (override via env vars if needed) ───────────────────────────────────
ROOT         = Path(__file__).resolve().parents[2]   # zomathon/
MODEL_PATH   = ROOT / "models" / "baseline_model.pkl"
RAW_DIR      = ROOT / "data" / "raw"

# ── Meal-window map (matches build_features.py) ───────────────────────────────
MEAL_WINDOW_BINS = [
    ((6,  11), "breakfast",    0),
    ((11, 16), "lunch",        1),
    ((16, 19), "evening_snack",2),
    ((19, 23), "dinner",       3),
    ((23, 27), "late_night",   4),   # 23-02 IST (hour 24/25/26 after roll)
]
BUDGET_MAP     = {"budget": 0, "mid": 1, "premium": 2}
PRICE_RANGE_MAP= {"low": 0, "mid": 1, "high": 2}
CATEGORY_MAP   = {"starter": 0, "main": 1, "drink": 2, "dessert": 3, "side": 4}
CUISINE_VOCAB  = ["North Indian","South Indian","Chinese","Pizza","Biryani",
                  "Burger","Desserts","Continental","Healthy","Thai"]

MACRO_CUISINES = {
    "North Indian": "Indian", "South Indian": "Indian", "Biryani": "Indian",
    "Mughlai": "Indian", "Street Food": "Indian", "Punjabi": "Indian",
    "Rajasthani": "Indian", "Gujarati": "Indian", "Maharashtrian": "Indian",
    "Chettinad": "Indian", "Bengali": "Indian", "Desserts": "Universal",
    "Beverages": "Universal", "Chinese": "Asian", "Italian": "Western",
    "Pizza": "Western", "Burger": "Western", "Continental": "Western",
    "Cafe": "Western", "Healthy Food": "Universal", "Lebanese": "Middle Eastern"
}

# ── Sub-cuisine map: item name keywords → regional sub-cuisine ─────────────
# This prevents pairing Dosa (South Indian) with Dal Baati Churma (Rajasthani)
SUB_CUISINE_MAP = {
    # South Indian
    "dosa": "South Indian", "idli": "South Indian", "sambar": "South Indian",
    "uttapam": "South Indian", "vada": "South Indian", "rasam": "South Indian",
    "appam": "South Indian", "upma": "South Indian", "pesarattu": "South Indian",
    "pongal": "South Indian", "puttu": "South Indian", "avial": "South Indian",
    "medu vada": "South Indian", "curd rice": "South Indian", "coconut chutney": "South Indian",
    "filter coffee": "South Indian", "payasam": "South Indian",
    # North Indian / Punjabi
    "naan": "North Indian", "roti": "North Indian", "paratha": "North Indian",
    "butter chicken": "North Indian", "dal makhani": "North Indian",
    "paneer tikka": "North Indian", "paneer butter": "North Indian",
    "chole": "North Indian", "rajma": "North Indian", "kadhai": "North Indian",
    "korma": "North Indian", "kulcha": "North Indian", "tikka masala": "North Indian",
    "shahi paneer": "North Indian", "malai kofta": "North Indian",
    "lassi": "North Indian", "tandoori": "North Indian",
    # Rajasthani
    "dal baati": "Rajasthani", "churma": "Rajasthani", "gatte": "Rajasthani",
    "laal maas": "Rajasthani", "ker sangri": "Rajasthani", "pyaaz kachori": "Rajasthani",
    # Bengali
    "rosogolla": "Bengali", "luchi": "Bengali", "mishti doi": "Bengali",
    "macher jhol": "Bengali", "sandesh": "Bengali", "begun bhaja": "Bengali",
    "kosha mangsho": "Bengali", "phuchka": "Bengali",
    # Hyderabadi
    "biryani": "Hyderabadi", "haleem": "Hyderabadi", "mirchi ka salan": "Hyderabadi",
    "double ka meetha": "Hyderabadi", "lukhmi": "Hyderabadi",
    # Western / Fast Food
    "burger": "Western", "pizza": "Western", "pasta": "Western",
    "fries": "Western", "sandwich": "Western", "wrap": "Western",
    "hot dog": "Western", "nachos": "Western", "taco": "Western",
    # Chinese / Asian
    "noodles": "Chinese", "fried rice": "Chinese", "manchurian": "Chinese",
    "momos": "Chinese", "spring roll": "Chinese", "chow mein": "Chinese",
    "dim sum": "Chinese", "hakka": "Chinese", "schezwan": "Chinese",
}

# Sub-cuisines that pair well together
SUB_CUISINE_COMPAT = {
    "South Indian": {"South Indian"},
    "North Indian": {"North Indian", "Rajasthani", "Hyderabadi"},
    "Rajasthani":   {"Rajasthani", "North Indian"},
    "Bengali":      {"Bengali"},
    "Hyderabadi":   {"Hyderabadi", "North Indian"},
    "Western":      {"Western"},
    "Chinese":      {"Chinese"},
}


# ── Model singleton ───────────────────────────────────────────────────────────
_model_cache = {}

def _load_model(model_path: str = None):
    path = str(model_path or MODEL_PATH)
    if path not in _model_cache:
        with open(path, "rb") as f:
            _model_cache[path] = pickle.load(f)
        print(f"[recommender] Model loaded from {path}")
    return _model_cache[path]


# ── Data loaders (lazy, cached) ───────────────────────────────────────────────
_data_cache = {}

def _load_csv(name: str) -> pd.DataFrame:
    # Disable cache for inference testing to prevent stale top 500 slices
    path = RAW_DIR / f"{name}.csv"
    return pd.read_csv(path)


def _get_users()       -> pd.DataFrame: return _load_csv("users")
def _get_restaurants() -> pd.DataFrame: return _load_csv("restaurants")
def _get_items()       -> pd.DataFrame: return _load_csv("items")


# ── Feature helpers ───────────────────────────────────────────────────────────

def _hour_to_meal_time(hour: int) -> int:
    """IST hour → meal_time integer."""
    for (lo, hi), _, code in MEAL_WINDOW_BINS:
        if lo <= hour < hi:
            return code
    return 3  # default dinner


def _safe_get(row: pd.Series, col: str, default=0):
    v = row.get(col, default)
    return default if pd.isna(v) else v


def _user_features(user_row: pd.Series) -> dict:
    return {
        "user_avg_spend":       float(_safe_get(user_row, "avg_spend", 300)),
        "user_order_freq":      float(_safe_get(user_row, "order_frequency", 3)),
        "user_veg_ratio":       float(_safe_get(user_row, "veg_ratio", 0.5)),
        "user_budget_segment":  BUDGET_MAP.get(str(_safe_get(user_row, "budget_segment", "mid")), 1),
    }


def _restaurant_features(rest_row: pd.Series, global_mean_rating=4.0, global_median_prep=30) -> dict:
    cuisine = str(_safe_get(rest_row, "cuisine", ""))
    cuisine_id = CUISINE_VOCAB.index(cuisine) if cuisine in CUISINE_VOCAB else len(CUISINE_VOCAB)
    return {
        "rest_price_range":  PRICE_RANGE_MAP.get(str(_safe_get(rest_row, "price_range", "mid")), 1),
        "rest_rating":       float(_safe_get(rest_row, "rating", global_mean_rating)),
        "rest_cuisine_id":   int(cuisine_id),
        "rest_is_chain":     int(_safe_get(rest_row, "is_chain", 0)),
        "rest_avg_prep_time":float(_safe_get(rest_row, "avg_prep_time_min", global_median_prep)),
    }


def _cart_features(cart_items_df: pd.DataFrame) -> dict:
    if cart_items_df.empty:
        return {
            "cart_item_count": 0, "cart_total_price": 0.0,
            "cart_has_drink": 0, "cart_has_dessert": 0,
            "cart_has_starter": 0, "cart_has_main": 0,
            "cart_veg_count": 0, "cart_nonveg_count": 0,
            "cart_unique_categories": 0, "cart_avg_item_price": 0.0,
        }
    count = len(cart_items_df)
    total = float(cart_items_df["price"].sum())
    cats  = cart_items_df["category"].tolist() if "category" in cart_items_df else []
    vegs  = cart_items_df["is_veg"].tolist()   if "is_veg"   in cart_items_df else []
    return {
        "cart_item_count":        count,
        "cart_total_price":       total,
        "cart_has_drink":         int("drink"   in cats),
        "cart_has_dessert":       int("dessert" in cats),
        "cart_has_starter":       int("starter" in cats),
        "cart_has_main":          int("main"    in cats),
        "cart_veg_count":         int(sum(v == 1 for v in vegs)),
        "cart_nonveg_count":      int(sum(v == 0 for v in vegs)),
        "cart_unique_categories": int(len(set(cats))),
        "cart_avg_item_price":    total / count,
    }


def _item_features(item_row: pd.Series) -> dict:
    return {
        "item_price":          float(_safe_get(item_row, "price", 150)),
        "item_is_veg":         int(_safe_get(item_row, "is_veg", 0)),
        "item_category":       CATEGORY_MAP.get(str(_safe_get(item_row, "category", "main")), 1),
        "item_popularity":     float(_safe_get(item_row, "popularity_score", 0)),
        "item_price_at_order": float(_safe_get(item_row, "price", 150)),  # no jitter at inference
    }


def _context_features(ts: datetime) -> dict:
    # Convert to IST (UTC+5:30)
    ist_hour = (ts.hour + 5) % 24   # rough IST offset
    dow = ts.weekday()
    return {
        "hour_of_day": ist_hour,
        "day_of_week": dow,
        "is_weekend":  int(dow >= 5),
        "meal_time":   _hour_to_meal_time(ist_hour),
    }


def _cross_features(item_f: dict, user_f: dict, cart_f: dict, rest_f: dict,
                    last_added_category: int,
                    user_preferred_cuisines: str = "",
                    item_cuisine_matches_cart: int = 0) -> dict:
    cart_cats_set = set()  # rebuilt from cart_f flags
    if cart_f["cart_has_drink"]:    cart_cats_set.add(2)
    if cart_f["cart_has_dessert"]:  cart_cats_set.add(3)
    if cart_f["cart_has_starter"]:  cart_cats_set.add(0)
    if cart_f["cart_has_main"]:     cart_cats_set.add(1)

    item_cat   = item_f["item_category"]
    item_price = item_f["item_price"]
    user_avg   = user_f["user_avg_spend"]
    cart_avg   = cart_f["cart_avg_item_price"]
    veg_ratio  = user_f["user_veg_ratio"]
    is_veg     = item_f["item_is_veg"]

    preferred = str(user_preferred_cuisines).lower()
    cuisine_names = [CUISINE_VOCAB[rest_f["rest_cuisine_id"]]
                     if rest_f["rest_cuisine_id"] < len(CUISINE_VOCAB) else ""]
    has_affinity = int(any(c.lower() in preferred for c in cuisine_names))

    # Manual penalty: if the item's category is already in the cart, 
    # force a negative feature value so the linear model heavily downranks it
    cat_missing = int(item_cat not in cart_cats_set)
    penalty = 1.0 if cat_missing else -500.0

    # Feature: Complementary Item Boost Logic
    complements = 0
    if item_cat == 2 and 2 not in cart_cats_set:
        complements = 1
    elif item_cat == 3 and 3 not in cart_cats_set:
        complements = 1
    elif item_cat in [0, 4] and 1 in cart_cats_set and 0 not in cart_cats_set and 4 not in cart_cats_set:
        complements = 1
    # REVERSE: If cart has sides/starters but NO main, boost mains (e.g. naan → curry)
    elif item_cat == 1 and (0 in cart_cats_set or 4 in cart_cats_set) and 1 not in cart_cats_set:
        complements = 1

    return {
        "item_category_missing_in_cart": penalty,
        "item_price_vs_user_avg":        item_price / max(user_avg, 1),
        "item_price_vs_cart_avg":        item_price / max(cart_avg, 1) if cart_avg > 0 else item_price / max(user_avg, 1),
        # Remove the veg penalty on drinks/desserts/sides for non-veg users
        "veg_user_veg_item":             int(veg_ratio >= 0.7 and is_veg == 1 and item_cat <= 1),
        "nonveg_user_veg_item":          int(veg_ratio <= 0.3 and is_veg == 1 and item_cat <= 1),
        "cart_completion_ratio":         cart_f["cart_item_count"] / (cart_f["cart_item_count"] + 1),
        "user_cuisine_affinity":         has_affinity,
        "last_added_category":           last_added_category,
        "item_complements_cart":         complements,
        "item_cuisine_matches_cart":     item_cuisine_matches_cart,
    }


def _build_feature_row(user_f, rest_f, cart_f, item_f, ctx_f, cross_f) -> dict:
    """Merge all feature dicts in the exact column order from train_features.csv."""
    return {
        **user_f,
        **rest_f,
        **cart_f,
        **item_f,
        **ctx_f,
        **cross_f,
    }


def _align_to_model(df: pd.DataFrame, feature_cols: list) -> pd.DataFrame:
    """
    Ensure the candidate DataFrame has exactly the columns the model expects,
    in the right order, with 0-fill for any missing ones.
    """
    for col in feature_cols:
        if col not in df.columns:
            df[col] = 0
    return df[feature_cols]


# ── Public API ────────────────────────────────────────────────────────────────

def recommend(
    user_id: int,
    restaurant_id: int,
    cart_items: List[int],          # list of item_ids already in cart
    timestamp: datetime,
    top_k: int = 8,
    model_path: Optional[str] = None,
    city: str = "",
) -> List[int]:
    """
    Returns list of up to top_k item_ids recommended as add-ons.

    Parameters
    ----------
    user_id       : int   — user primary key from users.csv
    restaurant_id : int   — restaurant primary key from restaurants.csv
    cart_items    : list  — item_ids already added to the cart (can be empty)
    timestamp     : datetime — order time (used for meal context)
    top_k         : int   — number of recommendations to return
    model_path    : str   — override path to model .pkl (optional)
    """
    payload      = _load_model(model_path)
    model        = payload["model"]
    feature_cols = payload["feature_cols"]
    encoders     = payload.get("encoders", {})

    users       = _get_users()
    restaurants = _get_restaurants()
    items       = _get_items()

    # ── Lookup user ─────────────────────────────────────────────────────────
    u_rows = users[users["user_id"] == user_id]
    if u_rows.empty:
        print(f"[recommender] user_id={user_id} not found — using global defaults")
        user_row = pd.Series({"avg_spend": 300, "order_frequency": 3,
                              "veg_ratio": 0.5, "budget_segment": "mid",
                              "preferred_cuisines": ""})
    else:
        user_row = u_rows.iloc[0]

    # ── Lookup restaurant ────────────────────────────────────────────────────
    # Auto-resolve restaurant_id from the cart if 0 is passed to bypass slow MongoDB lookups in Node
    if int(restaurant_id) == 0 and cart_items:
        first_item_row = items[items["item_id"] == cart_items[0]]
        if not first_item_row.empty:
            restaurant_id = int(first_item_row.iloc[0].get("restaurant_id", 0))

    r_rows = restaurants[restaurants["restaurant_id"] == restaurant_id]
    if r_rows.empty:
        print(f"[recommender] restaurant_id={restaurant_id} not found — using defaults")
        rest_row = pd.Series({"price_range": "mid", "rating": 4.0,
                              "cuisine": "North Indian", "is_chain": 0,
                              "avg_prep_time_min": 30})
    else:
        rest_row = r_rows.iloc[0]

    # ── Get candidate items ──────────────────────────────────────────────────
    # CITY-BASED FILTERING: Only recommend items from restaurants in the user's city
    city_str = (city or "").strip()
    if city_str:
        city_rest_ids = restaurants[restaurants["city"].str.lower() == city_str.lower()]["restaurant_id"].tolist()
        city_items = items[items["restaurant_id"].isin(city_rest_ids)]
        print(f"[recommender] City='{city_str}' → {len(city_rest_ids)} restaurants, {len(city_items)} items")
    else:
        city_items = items
        print(f"[recommender] No city filter → using all {len(items)} items")

    # If restaurant_id is STILL 0 (e.g. empty cart), recommend from city pool
    if int(restaurant_id) == 0:
        pool = city_items if city_str else items
        if 'category' in pool.columns:
            mains = pool[pool['category'].astype(str).str.lower() == 'main'].drop_duplicates(subset=["name"]).nlargest(250, "popularity_score")
            others = pool.drop_duplicates(subset=["name"]).nlargest(150, "popularity_score")
            menu = pd.concat([mains, others]).drop_duplicates(subset=["item_id"]).copy()
        else:
            menu = pool.nlargest(500, "popularity_score").copy()
        
        # Fallback: if city pool is too small, augment with global items
        if len(menu) < top_k * 3:
            print(f"[recommender] City pool too small ({len(menu)}) — augmenting with global items")
            global_extras = items.drop_duplicates(subset=["name"]).nlargest(min(top_k * 3, 60), "popularity_score")
            menu = pd.concat([menu, global_extras]).drop_duplicates(subset=["item_id"]).copy()
    else:
        menu = city_items[city_items["restaurant_id"] == restaurant_id].copy()
        if menu.empty:
            menu = items[items["restaurant_id"] == restaurant_id].copy()
            
        # Candidate Pre-Filtering: Keep only top 30 most popular items to guarantee ultra-low latency
        if len(menu) > 30 and 'popularity_score' in menu.columns:
            menu = menu.nlargest(30, "popularity_score").copy()

    # Exclude items already in cart
    if cart_items:
        menu = menu[~menu["item_id"].isin(cart_items)]

    # Fallback: if menu is too small after filtering, use global top popular items
    if len(menu) < top_k * 2:
        print(f"[recommender] Menu size {len(menu)} is small — augmenting with globally popular items")
        # HARD CAP AT 60 TO PREVENT 500 SERVER TIMEOUT CPU EXHAUSTION
        extras = (items[~items["item_id"].isin(cart_items)]
                  .nlargest(min(top_k * 3, 60), "popularity_score"))
        menu = pd.concat([menu, extras]).drop_duplicates(subset=["item_id"])

    if menu.empty:
        print("[recommender] No candidates after filtering cart items")
        return []

    # Drop items with duplicate names to ensure diversity (e.g. only one 'Coke 330ml')
    if "name" in menu.columns:
        menu = menu.drop_duplicates(subset=["name"], keep="first")
        
        # Also ensure we don't recommend an item (from global fallback) that has the same name as a cart item
        if cart_items:
            cart_names = items[items["item_id"].isin(cart_items)]["name"].unique()
            menu = menu[~menu["name"].isin(cart_names)]

    # ── Build features for each candidate ───────────────────────────────────
    cart_items_df = items[items["item_id"].isin(cart_items)] if cart_items else pd.DataFrame()

    last_added_category = -1
    if cart_items:
        last_item_id = cart_items[-1]
        last_item_row = items[items['item_id'] == last_item_id]
        if not last_item_row.empty:
            cat_str = last_item_row.iloc[0].get('category', '')
            last_added_category = CATEGORY_MAP.get(str(cat_str), -1)

    user_f = _user_features(user_row)
    rest_f = _restaurant_features(rest_row)
    cart_f = _cart_features(cart_items_df)
    ctx_f  = _context_features(timestamp)

    cart_cuisines = set()
    if not cart_items_df.empty:
        for _, c_row in cart_items_df.iterrows():
            c_rid = c_row.get("restaurant_id", 0)
            c_r_rows = restaurants[restaurants["restaurant_id"] == c_rid]
            if not c_r_rows.empty:
                cart_cuisines.add(c_r_rows.iloc[0].get("cuisine", "Unknown"))

    rows = []
    for _, item_row in menu.iterrows():
        item_f  = _item_features(item_row)
        
        cand_rid = int(item_row.get("restaurant_id", 0))
        rc = restaurants[restaurants["restaurant_id"] == cand_rid]
        cand_cuisine = rc.iloc[0].get("cuisine", "Unknown") if not rc.empty else "Unknown"
            
        cuisine_matches = 1 if cart_items and cand_cuisine in cart_cuisines else 0
        
        cross_f = _cross_features(item_f, user_f, cart_f, rest_f, last_added_category,
                                  user_row.get("preferred_cuisines", ""), cuisine_matches)
        row = _build_feature_row(user_f, rest_f, cart_f, item_f, ctx_f, cross_f)
        row["_item_id"] = int(item_row["item_id"])
        rows.append(row)

    cand_df = pd.DataFrame(rows)
    cand_df['item_name'] = menu['name'].values if 'name' in menu.columns else ''
    item_ids = cand_df.pop("_item_id").values

    # Apply label encoders from training (for any string columns still present)
    for col, le in encoders.items():
        if col in cand_df.columns and cand_df[col].dtype == object:
            known = set(le.classes_)
            cand_df[col] = cand_df[col].apply(
                lambda x: le.transform([x])[0] if x in known else 0
            )

    X = _align_to_model(cand_df, feature_cols)
    X = X.fillna(0)

    # ── Score & rank ─────────────────────────────────────────────────────────
    # Cold Start Fallback Check
    is_cold_start = (user_row.get("order_frequency", 0) < 1)

    scores = model.predict_proba(X.values)[:, 1]

    candidates = []
    for i, idx in enumerate(cand_df.index):
        item_id = int(item_ids[i])
        # Enforce strict int cast because Pandas float64 arrays break Re-Ranking boolean mappings
        cat = int(cand_df.loc[idx, 'item_category'])
        pop = float(cand_df.loc[idx, 'item_popularity'])
        score = float(scores[i])

        # Apply Time-Based & Popularity Cold-Start Fallback Weighting
        is_night_time_global = ctx_f.get("meal_time", 3) >= 3
        if is_cold_start:
            # If it's night time, let the ML scoring (and Re-Rank layer) keep more weight for mains
            if is_night_time_global and not cart_items and cat == 1:
                score = (score * 0.70) + ((pop / 100) * 0.30)
            else:
                score = (score * 0.4) + ((pop / 100) * 0.6)  # Heavily weigh popularity when sparse
            
        # Look up this candidate's cuisine from its restaurant
        cand_rid = int(menu.iloc[i].get('restaurant_id', 0)) if i < len(menu) else 0
        cand_r_rows = restaurants[restaurants['restaurant_id'] == cand_rid]
        cand_cuisine_val = cand_r_rows.iloc[0].get('cuisine', 'Unknown') if not cand_r_rows.empty else 'Unknown'

        candidates.append({
            'item_id': item_id, 
            'category': cat,
            'name': cand_df.loc[idx, 'item_name'] if 'item_name' in cand_df.columns else str(item_id),
            'score': score,
            'cuisine_matches': cand_df.loc[idx, 'item_cuisine_matches_cart'] if 'item_cuisine_matches_cart' in cand_df.columns else 1,
            'cuisine': cand_cuisine_val,
        })

    # 4️⃣ RE-RANKING LAYER
    
    print("\n[DEBUG] Candidates about to hit Re-Rank:")
    for c in candidates[:15]:
        print(f"  --> {c['name']} | Cat: {c['category']} | Score: {c['score']:.4f}")    

    # To avoid all datatype/encoding bugs, we iterate directly over the dataframe strings/ints
    cart_cats_raw = []
    if not cart_items_df.empty and "category" in cart_items_df:
        cart_cats_raw = cart_items_df["category"].tolist()
        
    cart_macro_cuisines = set()
    for c in cart_cuisines:
        macro = MACRO_CUISINES.get((c or "Unknown").title(), "Unknown")
        if macro != "Universal": # Don't lock a cart to 'Universal' natively
            cart_macro_cuisines.add(macro)
            
    cart_has_main = False
    cart_has_drink = False
    cart_has_side_or_dessert = False
    cart_has_biryani = False
    cart_has_bread = False  # Track if cart has breads (naan, roti, paratha, etc.)
    cart_has_starter = False
    cart_has_curry = False  # Track if cart has curry (dal, paneer, chicken, etc.)
    
    for c in cart_cats_raw:
        cat_int = CATEGORY_MAP.get(str(c).lower(), -1) if isinstance(c, str) else int(c)
        if cat_int == 1: cart_has_main = True
        if cat_int == 2: cart_has_drink = True
        if cat_int in [0, 3, 4]: cart_has_side_or_dessert = True
        if cat_int == 0: cart_has_starter = True
        
    for item_id_val in cart_items:
        i_row = items[items["item_id"] == item_id_val]
        if not i_row.empty:
            name_str = str(i_row.iloc[0].get("name", "")).lower()
            if "biryani" in name_str:
                cart_has_biryani = True
            if any(w in name_str for w in ["naan", "roti", "paratha", "kulcha", "bread", "chapati", "puri"]):
                cart_has_bread = True
            if any(w in name_str for w in ["curry", "dal", "paneer", "chicken", "mutton", "masala", "tikka masala", "korma", "chole", "rajma", "kadhai", "makhani", "shahi", "malai", "keema", "rogan", "fish", "prawn"]):
                cart_has_curry = True
    
    
    print(f"DEBUG RE-RANK: HasMain: {cart_has_main} | HasDrink: {cart_has_drink} | HasSide: {cart_has_side_or_dessert}")
    
    is_night_time = ctx_f.get("meal_time", 3) >= 3
    current_meal_time = ctx_f.get("meal_time", 3)

    seen_cats = set()
    for cand in candidates:
        cat = cand['category']
        score = cand['score']

        # Penalize duplicate categories heavily for diversity
        if cat in seen_cats:
            score *= 0.6
        else:
            seen_cats.add(cat)

        # Heavily penalize multiple mains if there is already a main in the cart
        if cart_has_main and cat == 1:
            score *= 0.1  # Force other mains to drop

        # COMPLEMENTARY PAIRING: If cart has sides/starters but NO main, strongly boost mains (curries)
        if cart_has_side_or_dessert and not cart_has_main and cat == 1:
            score += 0.60  # Major boost to ensure curries appear when cart has naan/sides

        # SPECIFIC BREAD→CURRY PAIRING: If cart has breads (naan, roti, etc), heavily boost curry-like mains
        cand_name_check = str(cand.get('name', '')).lower()
        if cart_has_bread and not cart_has_main and cat == 1:
            if any(w in cand_name_check for w in ['curry', 'dal', 'paneer', 'butter chicken', 'masala', 'tikka masala', 'korma', 'chole', 'rajma', 'kadhai', 'makhani', 'shahi', 'malai', 'keema', 'rogan', 'mutton', 'fish', 'prawn']):
                score += 0.50  # Extra boost for curry-type items when bread is in cart
                
        # SPECIFIC CURRY→BREAD PAIRING: If cart has curry/dal, heavily boost breads and rice
        if cart_has_curry:
            is_bread_or_rice = any(w in cand_name_check for w in ["naan", "roti", "paratha", "kulcha", "bread", "chapati", "puri", "rice", "pulao", "jeera rice"])
            if is_bread_or_rice:
                # MASSIVE boost for breads/rice when curry is in cart
                score = score * 3.0 + 0.70
            elif cat == 1 and not is_bread_or_rice:
                # Heavily dampen other mains (like burgers, pizzas, other curries) so breads/rice win
                score *= 0.10
            
        # ══════════════════════════════════════════════════════════════════
        # EMPTY CART LOGIC: When cart is empty, main courses MUST dominate.
        # The model naturally scores cheap drinks/sides higher (lower price,
        # high popularity), so we apply aggressive multiplicative overrides.
        # ══════════════════════════════════════════════════════════════════
        if not cart_items:
            cand_name_check_mt = str(cand.get('name', '')).lower()
            
            if cat == 1:  # Main course
                # MASSIVE boost for mains on empty cart — multiplicative + additive
                score = score * 3.0 + 0.60
                
                # Extra meal-time keyword boost
                if current_meal_time == 0:  # Breakfast
                    if any(w in cand_name_check_mt for w in ['dosa', 'idli', 'paratha', 'poha', 'upma', 'toast', 'omelette', 'pancake', 'uttapam', 'chole bhature', 'aloo']):
                        score += 0.40
                elif current_meal_time == 1:  # Lunch
                    if any(w in cand_name_check_mt for w in ['thali', 'rice', 'biryani', 'curry', 'dal', 'paneer', 'chicken', 'roti', 'meal', 'combo', 'noodles', 'fried rice', 'butter', 'masala', 'tikka']):
                        score += 0.35
                elif current_meal_time == 2:  # Evening snack
                    if any(w in cand_name_check_mt for w in ['samosa', 'pakora', 'chaat', 'momos', 'sandwich', 'burger', 'fries', 'spring roll', 'tikki', 'bhaji', 'roll', 'pizza']):
                        score += 0.35
                elif current_meal_time >= 3:  # Dinner / Late night
                    score += 0.15  # Everything main is boosted at dinner
                    
            elif cat == 0:  # Starter
                # Allow 1-2 starters but heavily dampened so mains lead
                score = score * 0.25 + 0.05

            elif cat == 2:  # Drink
                # Heavily dampen drinks on empty cart — user needs food first
                score = score * 0.15

            elif cat in [3, 4]:  # Dessert, Side
                # Heavily dampen sides/desserts on empty cart
                score = score * 0.15

        else:
            # NON-EMPTY CART: existing logic for balanced recommendations
            
            # To prevent the EXACT same highly-popular drink (Diet Coke) or side (Boondi Raita) 
            # from dominating every single time, we add a deterministic pseudo-random jitter 
            # based on the user_id, cart length, and item name.
            jitter = 0.0
            if user_id > 0:
                name_hash = sum(ord(c) for c in str(cand.get('name', '')))
                # Generates a pseudo-random float between 0.0 and 0.15
                jitter = ((user_id + len(cart_items) * 7 + name_hash * 13) % 15) / 100.0

            # Ensure at least 1 beverage if missing
            if not cart_has_drink and cat == 2 and cand['cuisine_matches'] == 1:
                score += (0.25 + jitter)  # Was flat 0.40, now 0.25 to 0.40
                
            # MACRO-CUISINE SPECIFIC DIVERSITY BOOSTS
            cand_name_low = str(cand.get('name', '')).lower()
            
            # Identify if the cart has any Indian items
            is_indian_cart = "Indian" in cart_macro_cuisines or cart_has_biryani or cart_has_curry or cart_has_bread
            
            # Ensure at least 1 side/dessert if missing
            if not cart_has_side_or_dessert and cat in [0, 3, 4] and cand['cuisine_matches'] == 1:
                # IMPORTANT FIX: Do NOT artificially boost Indian sides (Raita) if the cart is 100% Western/Asian
                if "raita" in cand_name_low and not is_indian_cart:
                    pass # Skip the boost for Raita on Burger/Pizza carts
                else:
                    score += (0.20 + jitter)  # Was flat 0.35, now 0.20 to 0.35

            # SPECIFIC DIVERSITY: If it's a Raita (and cart is Indian), heavily diversify it
            if "raita" in cand_name_low and is_indian_cart:
                # Give non-Boondi raitas an extra chance occasionally
                if "boondi" not in cand_name_low and jitter > 0.07:
                    score += 0.15

        # ══════════════════════════════════════════════════════════════
        # SUB-CUISINE PENALTY: Prevent culturally irrelevant pairings
        # e.g., Dosa (South Indian) + Dal Baati Churma (Rajasthani)
        # ══════════════════════════════════════════════════════════════
        if cart_items:
            # Detect sub-cuisines of cart items
            cart_sub_cuisines = set()
            for cid in cart_items:
                c_row = items[items["item_id"] == cid]
                if not c_row.empty:
                    c_name_low = str(c_row.iloc[0].get("name", "")).lower()
                    for keyword, sub_cuis in SUB_CUISINE_MAP.items():
                        if keyword in c_name_low:
                            cart_sub_cuisines.add(sub_cuis)
                            break
            
            if cart_sub_cuisines:
                # Detect sub-cuisine of this candidate
                cand_sub = None
                cand_name_for_sub = str(cand.get('name', '')).lower()
                for keyword, sub_cuis in SUB_CUISINE_MAP.items():
                    if keyword in cand_name_for_sub:
                        cand_sub = sub_cuis
                        break
                
                if cand_sub:
                    # Check if candidate's sub-cuisine is compatible with cart
                    compat_set = set()
                    for sc in cart_sub_cuisines:
                        compat_set.update(SUB_CUISINE_COMPAT.get(sc, {sc}))
                    
                    if cand_sub not in compat_set:
                        # HEAVY penalty for incompatible sub-cuisines
                        score *= 0.05
                        print(f"  [sub-cuisine] PENALIZED {cand.get('name')} ({cand_sub}) — cart has {cart_sub_cuisines}")

        # CROSS-CUISINE PENALTY (now macro-cuisine aware)
        # Instead of penalizing based on exact restaurant cuisine match, use macro-cuisine grouping
        # so that Dal Makhani (Biryani restaurant = Indian) still matches Garlic Naan (North Indian = Indian)
        cand_name_low = str(cand.get('name', '')).lower()
        cand_cuisine_for_penalty = cand.get('cuisine', 'Unknown')
        cand_macro_for_penalty = MACRO_CUISINES.get((cand_cuisine_for_penalty or "Unknown").title(), "Unknown")
        
        # Apply semantic name override for cross-cuisine penalty too
        if any(w in cand_name_low for w in ["raita", "naan", "paneer", "tikka", "masala", "roti", "biryani", "dal", "chhole", "curry", "mutton", "butter chicken", "gobi", "kebab", "dosa", "idli", "sambaar", "vada", "paratha"]):
            cand_macro_for_penalty = "Indian"
        elif any(w in cand_name_low for w in ["burger", "pizza", "pasta", "fries", "taco", "nacho", "sandwich", "garlic bread", "wrap", "hot dog"]):
            cand_macro_for_penalty = "Western"
        elif any(w in cand_name_low for w in ["sushi", "noodles", "chowmein", "manchurian", "momos", "dimsum", "fried rice", "chilli", "spring roll"]):
            cand_macro_for_penalty = "Asian"

        if cart_items and cart_macro_cuisines:
            macro_match = cand_macro_for_penalty in cart_macro_cuisines or cand_macro_for_penalty == "Universal"
            if not macro_match:
                if cat in [2, 4]:  # Drinks and Desserts are more universal
                    score *= 0.5
                else:  # Hard penalty for truly mismatched Mains and Sides (e.g., Raita with Burger)
                    score *= 0.0001

        # VERY SPECIFIC BUSINESS RULE: If Biryani is in the cart, Raita MUST be highly recommended
        cand_name_low = str(cand.get('name', '')).lower()
        if cart_has_biryani and "raita" in cand_name_low:
            score *= 3.0
            
        # UNIVERSAL MACRO-CUISINE CLUSTERING PENALTY
        # Checks if the candidate food culture matches the cart food culture
        cand_cuisine_for_macro = cand.get('cuisine', 'Unknown')
        cand_macro = MACRO_CUISINES.get((cand_cuisine_for_macro or "Unknown").title(), "Unknown")
        
        # Semantic Name Override for anomalous DB entries (e.g. "Raita" generated under a "Continental" restaurant)
        if any(w in cand_name_low for w in ["raita", "naan", "paneer", "tikka", "masala", "roti", "biryani", "dal", "chhole", "curry", "mutton", "butter chicken", "gobi", "kebab", "dosa", "idli", "sambaar", "vada", "paratha"]):
            cand_macro = "Indian"
        elif any(w in cand_name_low for w in ["burger", "pizza", "pasta", "fries", "taco", "nacho", "sandwich", "garlic bread", "wrap", "hot dog"]):
            cand_macro = "Western"
        elif any(w in cand_name_low for w in ["sushi", "noodles", "chowmein", "manchurian", "momos", "dimsum", "fried rice", "chilli", "spring roll"]):
            cand_macro = "Asian"

        # We only strictly apply this penalty if the cart actually establishes a specific macro-cuisine 
        # (e.g. an empty cart has no macro-cuisine, so let anything recommend)
        if cart_items and cart_macro_cuisines:
            # Determine if this item is an Indian side that MUST be penalized for non-Indian carts
            is_indian_side = any(w in cand_name_low for w in ["raita", "naan", "roti", "paratha", "kulcha"])
            
            # We explicitly exempt Drinks (2) and Desserts (3) so they can float freely across all carts.
            # Sides (4) are mostly exempt (fries go with anything), EXCEPT specific Indian sides.
            is_exempt = (cat in [2, 3]) or (cat == 4 and not is_indian_side)

            if not is_exempt and cand_macro != "Universal":
                if cand_macro not in cart_macro_cuisines:
                    score = -999.0 # Absolute hard penalty to destroy it from the sorted list

        # ABSOLUTE CEILING FOR DATASET ANOMALIES (Pani Puri, Boondi Raita, Diet Coke)
        # These 3 items have massive synthetic popularity scores that break the engine.
        # We physically cap them at the very end of all evaluation logic so they can never dominate.
        # Lowered to 0.0001 because base LTR model scores are very low for most items (0.01-0.05),
        # so even a 0.10 cap allowed them to easily take the 7th and 8th spots as filler.
        if "pani puri" in cand_name_low:
            score = min(score, 0.0001)
        elif "boondi raita" in cand_name_low:
            score = min(score, 0.0001)
        elif "diet coke" in cand_name_low:
            score = min(score, 0.0001)

        cand['adjusted_score'] = score

    # Strip completely penalized items Out of the final array
    pre_len = len(candidates)
    candidates = [c for c in candidates if c['adjusted_score'] > -100.0]
    print(f"DEBUG FILTER -> Stripped {pre_len - len(candidates)} hard-penalized anomalies. Remaining valid candidates: {len(candidates)}")

    candidates.sort(key=lambda x: x['adjusted_score'], reverse=True)
    
    # FALLBACK REPLENISHMENT CHECK:
    # If the semantic filter destroyed so many candidates that we have fewer than top_k, 
    # we CANNOT blindly append unfiltered global items. We must retrieve globally popular Universal items (drinks/desserts).
    if len(candidates) < top_k:
        print(f"DEBUG FALLBACK -> Filter left {len(candidates)} items, which is less than requested {top_k}. Finding universal fallbacks.")
        # Very simple fallback: just grab the highest scoring items that are Universal (Drinks/Desserts) from the RAW DB
        universal_fallbacks = []
        for _, u_row in items.iterrows():
            if len(candidates) + len(universal_fallbacks) >= top_k: break
            u_cat = u_row['category'] if pd.notna(u_row.get('category')) else -1
            if u_cat in [2, 3]: # Drinks and Desserts
                if not cart_items or u_row['item_id'] not in cart_items:
                    # Make sure it's not already in candidates
                    if not any(c['item_id'] == u_row['item_id'] for c in candidates):
                        # Create dummy candidate
                        universal_fallbacks.append({
                            'item_id': int(u_row['item_id']),
                            'adjusted_score': 0.0,
                            'category': int(u_cat)
                        })
        candidates.extend(universal_fallbacks)

    # ULTIMATE NIGHT TIME GUARANTEE:
    # If it is night time and cart is empty, force the absolute top item to be the highest scoring Main Course 
    # if it fell below position 0.
    if is_night_time and not cart_items:
        best_main_idx = -1
        for i, c in enumerate(candidates):
            if c['category'] == 1:
                best_main_idx = i
                break
        
        if best_main_idx > 0:
            main_item = candidates.pop(best_main_idx)
            candidates.insert(0, main_item)
            
    recommended = [c['item_id'] for c in candidates[:top_k]]

    return recommended


# ── Standalone test ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    from datetime import datetime

    user_id       = 1
    restaurant_id = 1
    cart_items    = []
    ts            = datetime(2024, 11, 15, 19, 30)  # Friday dinner

    print(f"\nRecommending for user={user_id}, restaurant={restaurant_id}")
    print(f"Cart: {cart_items}, Time: {ts}")

    recs = recommend(user_id, restaurant_id, cart_items, ts, top_k=8)
    print(f"\nTop-8 recommended item_ids: {recs}")