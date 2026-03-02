"""
build_features.py — ML Pipeline & Feature Engineering
Context-Aware Add-on Recommendation System
Reads 5 CSVs → produces train_features.csv + pipeline_report.json
Antigravity v1.0 • Seedable & Reproducible
"""
import argparse
import json
import os
import sys
import warnings
from datetime import timedelta

import numpy as np
import pandas as pd

warnings.filterwarnings('ignore')

# ── 1. Global Configuration ─────────────────────────────────────────
SEED               = 42
N_NEGATIVES        = 4
MIN_NEGATIVES      = 1
PRICE_JITTER_PCT   = 0.05

MEAL_WINDOW_BINS   = {
    (6, 11):  'breakfast',
    (11, 16): 'lunch',
    (16, 19): 'evening_snack',
    (19, 23): 'dinner',
    (23, 26): 'late_night',
}
BUDGET_MAP         = {'budget': 0, 'mid': 1, 'premium': 2}
PRICE_RANGE_MAP    = {'low': 0, 'mid': 1, 'high': 2}
CATEGORY_MAP       = {'starter': 0, 'main': 1, 'drink': 2, 'dessert': 3, 'side': 4}
MEAL_TIME_MAP      = {'breakfast': 0, 'lunch': 1, 'evening_snack': 2,
                      'dinner': 3, 'late_night': 4}
CUISINE_VOCAB      = [
    'North Indian', 'South Indian', 'Chinese', 'Pizza', 'Biryani',
    'Burger', 'Desserts', 'Continental', 'Healthy', 'Thai',
]

INPUT_DIR          = 'data/raw/'
OUTPUT_PATH        = 'data/processed/train_features.csv'
REPORT_PATH        = 'data/processed/pipeline_report.json'

# ── Column order for output ──────────────────────────────────────────
COLUMN_ORDER = [
    # Identity
    'query_id', 'step_number', 'candidate_item_id', 'label', 'split',
    # User
    'user_avg_spend', 'user_order_freq', 'user_veg_ratio', 'user_budget_segment',
    # Restaurant
    'rest_price_range', 'rest_rating', 'rest_cuisine_id', 'rest_is_chain', 'rest_avg_prep_time',
    # Cart
    'cart_item_count', 'cart_total_price', 'cart_has_drink', 'cart_has_dessert',
    'cart_has_starter', 'cart_has_main', 'cart_veg_count', 'cart_nonveg_count',
    'cart_unique_categories', 'cart_avg_item_price',
    # Item
    'item_price', 'item_is_veg', 'item_category', 'item_popularity', 'item_price_at_order',
    # Context
    'hour_of_day', 'day_of_week', 'is_weekend', 'meal_time',
    # Cross
    'item_category_missing_in_cart', 'item_price_vs_user_avg', 'item_price_vs_cart_avg',
    'veg_user_veg_item', 'nonveg_user_veg_item', 'cart_completion_ratio', 'user_cuisine_affinity',
    'last_added_category', 'item_complements_cart', 'item_cuisine_matches_cart'
]


def get_meal_time(local_hour):
    """Map local IST hour to meal window integer."""
    h = local_hour
    if h < 2:
        h += 24  # wrap for late night
    for (lo, hi), label in MEAL_WINDOW_BINS.items():
        if lo <= h < hi:
            return MEAL_TIME_MAP[label]
    return MEAL_TIME_MAP['dinner']  # default


def build_features(seed=42, n_negatives=4, input_dir='data/raw/',
                   output_path='data/processed/train_features.csv',
                   report_path='data/processed/pipeline_report.json'):
    rng = np.random.default_rng(seed)

    print("=" * 60)
    print("build_features.py — ML Feature Engineering Pipeline")
    print(f"SEED={seed}  N_NEGATIVES={n_negatives}")
    print("=" * 60)

    # ── 2. Load Data ─────────────────────────────────────────────────
    print("\n[1/6] Loading input CSVs ...")
    users = pd.read_csv(input_dir + 'users.csv', dtype={
        'user_id': int, 'avg_spend': float, 'order_frequency': float,
        'veg_ratio': float})
    restaurants = pd.read_csv(input_dir + 'restaurants.csv', dtype={
        'restaurant_id': int, 'rating': float, 'is_chain': int,
        'avg_prep_time_min': 'Int64'})
    items = pd.read_csv(input_dir + 'items.csv', dtype={
        'item_id': int, 'restaurant_id': int, 'price': float,
        'is_veg': int, 'popularity_score': float})
    orders = pd.read_csv(input_dir + 'orders.csv',
        dtype={'order_id': int, 'user_id': int, 'restaurant_id': int,
               'order_total': float, 'num_items': int},
        parse_dates=['order_ts'])
    order_items = pd.read_csv(input_dir + 'order_items.csv', dtype={
        'order_id': int, 'item_id': int, 'step_number': int,
        'item_price_at_order': float, 'added_to_cart': int})

    print(f"  users={len(users)}, restaurants={len(restaurants)}, items={len(items)},",
          f"orders={len(orders)}, order_items={len(order_items)}")

    # ── 2.5 Clean Orphaned Orders (from DB seeds) ─────────────
    valid_items = set(items['item_id'])
    invalid_orders_items = order_items[~order_items['item_id'].isin(valid_items)]['order_id'].unique()
    valid_rests = set(restaurants['restaurant_id'])
    invalid_orders_rest = orders[~orders['restaurant_id'].isin(valid_rests)]['order_id'].unique()
    
    bad_orders = set(invalid_orders_items) | set(invalid_orders_rest)
    if bad_orders:
        print(f"  [Cleanup] Dropping {len(bad_orders)} orders referencing deleted mock data.")
        orders = orders[~orders['order_id'].isin(bad_orders)]
        order_items = order_items[~order_items['order_id'].isin(bad_orders)]

    # ── 3. Pre-flight Validation ─────────────────────────────────────
    print("\n[2/6] Pre-flight validation ...")
    assert items['restaurant_id'].isin(restaurants['restaurant_id']).all(), \
        "FK violation: items.restaurant_id"
    assert orders['user_id'].isin(users['user_id']).all(), \
        "FK violation: orders.user_id"
    assert orders['restaurant_id'].isin(restaurants['restaurant_id']).all(), \
        "FK violation: orders.restaurant_id"
    assert order_items['order_id'].isin(orders['order_id']).all(), \
        "FK violation: order_items.order_id"
    assert order_items['item_id'].isin(items['item_id']).all(), \
        "FK violation: order_items.item_id"

    # Step number continuity
    step_check = order_items.groupby('order_id').agg(
        max_step=('step_number', 'max'),
        cnt=('step_number', 'count'),
        min_step=('step_number', 'min')
    )
    step_gaps = ((step_check['max_step'] != step_check['cnt']) |
                 (step_check['min_step'] != 1)).sum()
    assert step_gaps == 0, f"step_number gaps in {step_gaps} orders"

    # num_items cross-check
    actual_counts = order_items.groupby('order_id').size()
    order_num_items = orders.set_index('order_id')['num_items']
    mismatch = (actual_counts != order_num_items).sum()
    assert mismatch == 0, f"{mismatch} orders have num_items mismatch"
    print("  ✓ All pre-flight checks passed.")

    # ── 4. Precompute Lookups ────────────────────────────────────────
    print("\n[3/6] Building lookup tables ...")

    # Imputation values (from training data only — orders before Sep 2024)
    train_cutoff = pd.Timestamp('2024-09-01', tz='UTC')
    train_orders = orders[orders['order_ts'] < train_cutoff]
    train_rest_ids = train_orders['restaurant_id'].unique()
    train_rests = restaurants[restaurants['restaurant_id'].isin(train_rest_ids)]

    global_mean_rating = float(train_rests['rating'].mean())
    global_median_prep = float(train_rests['avg_prep_time_min'].dropna().median())

    # Restaurant features dict
    rest_feat = {}
    cuisine_to_idx = {c: i for i, c in enumerate(CUISINE_VOCAB)}
    for _, r in restaurants.iterrows():
        rid = r['restaurant_id']
        rating = r['rating'] if pd.notna(r['rating']) else global_mean_rating
        prep = float(r['avg_prep_time_min']) if pd.notna(r['avg_prep_time_min']) else global_median_prep
        rest_feat[rid] = {
            'rest_price_range': PRICE_RANGE_MAP.get(r['price_range'], 1),
            'rest_rating': round(rating, 1),
            'rest_cuisine_id': cuisine_to_idx.get(r['cuisine'], len(CUISINE_VOCAB)),
            'rest_is_chain': int(r['is_chain']),
            'rest_avg_prep_time': prep,
            'cuisine': r['cuisine'],
        }

    # User features dict
    user_feat = {}
    for _, u in users.iterrows():
        uid = u['user_id']
        prefs = str(u['preferred_cuisines']).split(';') if pd.notna(u['preferred_cuisines']) else []
        user_feat[uid] = {
            'user_avg_spend': u['avg_spend'],
            'user_order_freq': u['order_frequency'],
            'user_veg_ratio': u['veg_ratio'],
            'user_budget_segment': BUDGET_MAP.get(u['budget_segment'], 1),
            'preferred_cuisines': set(prefs),
        }

    # Item features dict
    item_feat = {}
    for _, it in items.iterrows():
        iid = it['item_id']
        item_feat[iid] = {
            'item_price': it['price'],
            'item_is_veg': int(it['is_veg']),
            'item_category': CATEGORY_MAP.get(it['category'], 1),
            'item_popularity': it['popularity_score'],
            'restaurant_id': it['restaurant_id'],
            'category_str': it['category'],
            'cuisine': rest_feat.get(it['restaurant_id'], {}).get('cuisine', 'Unknown'),
        }

    # Restaurant → item_ids mapping
    rest_items_map = items.groupby('restaurant_id')['item_id'].apply(list).to_dict()

    # Order info
    order_info = {}
    for _, o in orders.iterrows():
        oid = o['order_id']
        # Convert UTC → IST
        utc_ts = o['order_ts']
        ist_ts = utc_ts + timedelta(hours=5, minutes=30)
        local_hour = ist_ts.hour
        dow = ist_ts.weekday()
        order_info[oid] = {
            'user_id': o['user_id'],
            'restaurant_id': o['restaurant_id'],
            'order_ts': utc_ts,
            'hour_of_day': local_hour,
            'day_of_week': dow,
            'is_weekend': 1 if dow >= 5 else 0,
            'meal_time': get_meal_time(local_hour),
        }

    # Order items grouped
    oi_grouped = order_items.sort_values(['order_id', 'step_number']).groupby('order_id')

    # Temporal split boundaries
    val_start = pd.Timestamp('2024-09-01', tz='UTC')
    test_start = pd.Timestamp('2024-11-01', tz='UTC')

    def get_split(ts):
        if ts < val_start:
            return 'train'
        elif ts < test_start:
            return 'val'
        else:
            return 'test'

    print(f"  Imputation: rating mean={global_mean_rating:.2f}, prep median={global_median_prep:.0f}")
    print(f"  Restaurant items mapped: {len(rest_items_map)} restaurants")

    # ── 5. Core Loop ─────────────────────────────────────────────────
    print("\n[4/6] Generating training samples ...")
    output_rows = []
    skipped_steps = 0
    total_steps = 0
    flush_count = 0

    all_order_ids = orders['order_id'].values
    n_orders = len(all_order_ids)

    for batch_idx, oid in enumerate(all_order_ids):
        oi = order_info[oid]
        uid = oi['user_id']
        rid = oi['restaurant_id']
        uf = user_feat[uid]
        rf = rest_feat[rid]
        split = get_split(oi['order_ts'])

        # Temporal features (shared across all candidates in this order)
        temporal = {
            'hour_of_day': oi['hour_of_day'],
            'day_of_week': oi['day_of_week'],
            'is_weekend': oi['is_weekend'],
            'meal_time': oi['meal_time'],
        }

        # User-restaurant affinity
        user_cuisine_aff = 1 if rf['cuisine'] in uf['preferred_cuisines'] else 0

        # Get this order's items in step order
        grp = oi_grouped.get_group(oid)
        steps = grp.sort_values('step_number')
        step_list = steps.to_dict('records')

        # Full restaurant menu
        menu_ids = set(rest_items_map.get(rid, []))

        cart_items = []  # list of (item_id, price_at_order, category_str, is_veg)

        for step_row in step_list:
            sn = step_row['step_number']
            pos_item_id = step_row['item_id']
            pos_price_at_order = step_row['item_price_at_order']
            total_steps += 1

            # Cart state (items before this step)
            cart_count = len(cart_items)
            cart_total = sum(p for _, p, _, _ in cart_items)
            cart_cats = set(c for _, _, c, _ in cart_items)
            cart_veg = sum(1 for _, _, _, v in cart_items if v == 1)
            cart_nonveg = sum(1 for _, _, _, v in cart_items if v == 0)
            cart_avg_price = cart_total / cart_count if cart_count > 0 else 0.0
            cart_cuisines = set(item_feat[iid].get('cuisine', 'Unknown') for iid, _, _, _ in cart_items)

            cart_context = {
                'cart_item_count': cart_count,
                'cart_total_price': round(cart_total, 2),
                'cart_has_drink': 1 if 'drink' in cart_cats else 0,
                'cart_has_dessert': 1 if 'dessert' in cart_cats else 0,
                'cart_has_starter': 1 if 'starter' in cart_cats else 0,
                'cart_has_main': 1 if 'main' in cart_cats else 0,
                'cart_veg_count': cart_veg,
                'cart_nonveg_count': cart_nonveg,
                'cart_unique_categories': len(cart_cats),
                'cart_avg_item_price': round(cart_avg_price, 2),
            }

            cart_cat_ints = set(CATEGORY_MAP.get(c, 1) for c in cart_cats)

            # Cart item ids already in cart (including positive being added now)
            cart_item_ids = set(iid for iid, _, _, _ in cart_items)

            # Available negatives: menu minus cart minus positive
            available = menu_ids - cart_item_ids - {pos_item_id}

            if len(available) < MIN_NEGATIVES:
                skipped_steps += 1
                # Still add to cart for subsequent steps
                pf = item_feat.get(pos_item_id, {})
                cart_items.append((pos_item_id, pos_price_at_order,
                                   pf.get('category_str', 'main'),
                                   pf.get('item_is_veg', 0)))
                continue

            # Sample negatives weighted by popularity
            avail_list = list(available)
            pops = np.array([max(item_feat[iid]['item_popularity'], 0.001)
                             for iid in avail_list])
            probs = pops / pops.sum()
            n_neg = min(n_negatives, len(avail_list))
            neg_ids = list(rng.choice(avail_list, size=n_neg, replace=False, p=probs))

            # Build feature rows for positive + negatives
            candidates = [(pos_item_id, 1, pos_price_at_order)] + \
                         [(nid, 0, None) for nid in neg_ids]

            for cand_id, lbl, price_ao in candidates:
                cf = item_feat[cand_id]
                # item_price_at_order: positive uses actual; negative uses base price
                if price_ao is not None:
                    ipao = price_ao
                else:
                    ipao = cf['item_price']

                cat_int = cf['item_category']
                cat_missing = 1 if cat_int not in cart_cat_ints else 0
                ipv_user = cf['item_price'] / uf['user_avg_spend'] if uf['user_avg_spend'] > 0 else 0.0
                if cart_avg_price > 0:
                    ipv_cart = cf['item_price'] / cart_avg_price
                else:
                    ipv_cart = ipv_user
                veg_user_veg = 1 if uf['user_veg_ratio'] >= 0.7 and cf['item_is_veg'] == 1 else 0
                nonveg_user_veg = 1 if uf['user_veg_ratio'] <= 0.3 and cf['item_is_veg'] == 1 else 0
                comp_ratio = cart_count / (cart_count + 1)

                # Feature: Sequential Logic (last added category)
                last_added = -1
                if cart_items:
                    last_cat_str = cart_items[-1][2]
                    last_added = CATEGORY_MAP.get(last_cat_str, -1)

                # Feature: Complementary Item Boost Logic
                complements = 0
                if cat_int == 2 and 'drink' not in cart_cats:
                    complements = 1
                elif cat_int == 3 and 'dessert' not in cart_cats:
                    complements = 1
                elif cat_int in [0, 4] and 'main' in cart_cats and 'starter' not in cart_cats and 'side' not in cart_cats:
                    complements = 1
                    
                cuisine_matches = 1 if (cart_count > 0 and cf.get('cuisine', 'Unknown') in cart_cuisines) else 0

                row = {
                    'query_id': oid,
                    'step_number': sn,
                    'candidate_item_id': cand_id,
                    'label': lbl,
                    'split': split,
                    'user_avg_spend': uf['user_avg_spend'],
                    'user_order_freq': uf['user_order_freq'],
                    'user_veg_ratio': uf['user_veg_ratio'],
                    'user_budget_segment': uf['user_budget_segment'],
                    'rest_price_range': rf['rest_price_range'],
                    'rest_rating': rf['rest_rating'],
                    'rest_cuisine_id': rf['rest_cuisine_id'],
                    'rest_is_chain': rf['rest_is_chain'],
                    'rest_avg_prep_time': rf['rest_avg_prep_time'],
                    **cart_context,
                    'item_price': cf['item_price'],
                    'item_is_veg': cf['item_is_veg'],
                    'item_category': cat_int,
                    'item_popularity': cf['item_popularity'],
                    'item_price_at_order': round(ipao, 2),
                    **temporal,
                    'item_category_missing_in_cart': cat_missing,
                    'item_price_vs_user_avg': round(ipv_user, 4),
                    'item_price_vs_cart_avg': round(ipv_cart, 4),
                    'veg_user_veg_item': veg_user_veg,
                    'nonveg_user_veg_item': nonveg_user_veg,
                    'cart_completion_ratio': round(comp_ratio, 4),
                    'user_cuisine_affinity': user_cuisine_aff,
                    'last_added_category': last_added,
                    'item_complements_cart': complements,
                    'item_cuisine_matches_cart': cuisine_matches,
                }
                output_rows.append(row)

            # Add positive to cart for next step
            pf = item_feat.get(pos_item_id, {})
            cart_items.append((pos_item_id, pos_price_at_order,
                               pf.get('category_str', 'main'),
                               pf.get('item_is_veg', 0)))

        if (batch_idx + 1) % 15000 == 0:
            print(f"    ... {batch_idx + 1}/{n_orders} orders processed"
                  f"  ({len(output_rows)} rows so far)")

    print(f"  → {len(output_rows)} total rows generated from {total_steps} steps"
          f"  ({skipped_steps} skipped)")

    # ── 6. Assemble DataFrame & Write ────────────────────────────────
    print("\n[5/6] Assembling output DataFrame ...")
    df = pd.DataFrame(output_rows, columns=COLUMN_ORDER)

    # Ensure no nulls
    null_cols = df.isnull().sum()
    null_cols = null_cols[null_cols > 0]
    if len(null_cols) > 0:
        print(f"  ⚠ Found nulls, filling: {dict(null_cols)}")
        df = df.fillna(0)

    # Cast dtypes
    int_cols = ['query_id', 'step_number', 'candidate_item_id', 'label',
                'user_budget_segment', 'rest_price_range', 'rest_cuisine_id',
                'rest_is_chain', 'cart_item_count', 'cart_has_drink',
                'cart_has_dessert', 'cart_has_starter', 'cart_has_main',
                'cart_veg_count', 'cart_nonveg_count', 'cart_unique_categories',
                'item_is_veg', 'item_category', 'hour_of_day', 'day_of_week',
                'is_weekend', 'meal_time', 'item_category_missing_in_cart',
                'veg_user_veg_item', 'nonveg_user_veg_item', 'user_cuisine_affinity',
                'last_added_category', 'item_complements_cart', 'item_cuisine_matches_cart']
    for c in int_cols:
        df[c] = df[c].astype(int)

    # Write
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    df.to_csv(output_path, index=False)
    print(f"  → Written {len(df)} rows to {output_path}")

    # ── 7. Validation Report ─────────────────────────────────────────
    print("\n[6/6] Generating pipeline_report.json ...")

    pos_count = int((df['label'] == 1).sum())
    neg_count = int((df['label'] == 0).sum())
    label_ratio = round(pos_count / len(df), 4) if len(df) > 0 else 0

    split_dist = df['split'].value_counts().to_dict()

    # Top 10 popular items by positive count
    pos_df = df[df['label'] == 1]
    top10 = pos_df['candidate_item_id'].value_counts().head(10)
    top10_list = []
    for iid, cnt in top10.items():
        name = items.loc[items['item_id'] == iid, 'name'].values
        name_str = name[0] if len(name) > 0 else 'unknown'
        top10_list.append({'item_id': int(iid), 'name': name_str, 'positive_count': int(cnt)})

    # Feature stats
    feat_stats = {}
    for col in ['user_avg_spend', 'item_popularity', 'cart_total_price']:
        feat_stats[col] = {
            'mean': round(float(df[col].mean()), 4),
            'std': round(float(df[col].std()), 4),
            'min': round(float(df[col].min()), 4),
            'max': round(float(df[col].max()), 4),
        }

    # Veg correlation check
    high_veg_mask = df['user_veg_ratio'] >= 0.70
    low_veg_mask = df['user_veg_ratio'] <= 0.30
    pos_mask = df['label'] == 1
    high_veg_veg_pct = round(float(df.loc[high_veg_mask & pos_mask, 'item_is_veg'].mean()), 4) \
        if (high_veg_mask & pos_mask).sum() > 0 else 0.0
    low_veg_veg_pct = round(float(df.loc[low_veg_mask & pos_mask, 'item_is_veg'].mean()), 4) \
        if (low_veg_mask & pos_mask).sum() > 0 else 0.0

    # Null counts in output
    output_nulls = {c: int(v) for c, v in df.isnull().sum().items() if v > 0}

    report = {
        'input_row_counts': {
            'users': int(len(users)),
            'restaurants': int(len(restaurants)),
            'items': int(len(items)),
            'orders': int(len(orders)),
            'order_items': int(len(order_items)),
        },
        'fk_violations': {
            'items.restaurant_id': 0,
            'orders.user_id': 0,
            'orders.restaurant_id': 0,
            'order_items.order_id': 0,
            'order_items.item_id': 0,
        },
        'step_number_gaps': 0,
        'num_items_mismatches': 0,
        'output_row_count': int(len(df)),
        'output_positive_count': pos_count,
        'output_negative_count': neg_count,
        'label_ratio': label_ratio,
        'null_counts_in_output': output_nulls,
        'skipped_steps': skipped_steps,
        'split_distribution': {k: int(v) for k, v in split_dist.items()},
        'top10_popular_items': top10_list,
        'feature_stats': feat_stats,
        'veg_correlation_check': {
            'high_veg_users_veg_item_pct': high_veg_veg_pct,
            'low_veg_users_veg_item_pct': low_veg_veg_pct,
        },
    }

    with open(report_path, 'w') as f:
        json.dump(report, f, indent=2, default=str)

    # Check HARD constraints
    hard_fail = False
    if output_nulls:
        print(f"  ✗ HARD FAIL: nulls in output — {output_nulls}")
        hard_fail = True
    for k, v in report['fk_violations'].items():
        if v != 0:
            print(f"  ✗ HARD FAIL: {k} = {v}")
            hard_fail = True

    if hard_fail:
        print("\n❌ PIPELINE FAILED — hard constraint violations.")
        sys.exit(1)
    else:
        print("\n✓ All HARD constraints passed.")

    print(f"\nSummary:")
    print(f"  Total rows:       {len(df):,}")
    print(f"  Positives:        {pos_count:,}")
    print(f"  Negatives:        {neg_count:,}")
    print(f"  Label ratio:      {label_ratio:.4f}  (expect ~0.20)")
    print(f"  Skipped steps:    {skipped_steps}")
    print(f"  Split: {split_dist}")
    print(f"  Veg correlation:  high_veg={high_veg_veg_pct:.4f} (≥0.70),"
          f" low_veg={low_veg_veg_pct:.4f} (≤0.30)")
    print(f"\n{'='*60}")
    print("Feature engineering complete!")
    print(f"{'='*60}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Build ML features for add-on recommendation')
    parser.add_argument('--seed', type=int, default=42)
    parser.add_argument('--n_negatives', type=int, default=4)
    parser.add_argument('--input_dir', type=str, default='data/raw/')
    parser.add_argument('--output', type=str, default='data/processed/train_features.csv')
    parser.add_argument('--report', type=str, default='data/processed/pipeline_report.json')
    args = parser.parse_args()

    np.random.seed(args.seed)
    build_features(seed=args.seed, n_negatives=args.n_negatives,
                   input_dir=args.input_dir, output_path=args.output,
                   report_path=args.report)
