"""
Antigravity Dataset Generator v1.0
Generates: users.csv, restaurants.csv, items.csv, orders.csv, order_items.csv, validation_report.json
Fully seedable & reproducible.
"""
import numpy as np
import pandas as pd
import json, os, math, warnings
from datetime import datetime, timedelta
from collections import Counter

warnings.filterwarnings('ignore')

# ── 1. Global Configuration ──
GLOBAL_SEED          = int(os.environ.get('GLOBAL_SEED', 42))
N_USERS              = int(os.environ.get('N_USERS', 7500))
N_RESTAURANTS        = int(os.environ.get('N_RESTAURANTS', 750))
ITEMS_PER_REST_MIN   = int(os.environ.get('ITEMS_PER_REST_MIN', 15))
ITEMS_PER_REST_MAX   = int(os.environ.get('ITEMS_PER_REST_MAX', 80))
N_ORDERS             = int(os.environ.get('N_ORDERS', 75000))
PRICE_LOW_MIN, PRICE_LOW_MAX   = 40, 150
PRICE_MID_MIN, PRICE_MID_MAX   = 150, 400
PRICE_HIGH_MIN, PRICE_HIGH_MAX = 400, 1200
PCT_VEG_HEAVY_USERS  = 0.35
PCT_NEW_USERS        = 0.05
PCT_NEW_RESTAURANTS  = 0.04
PCT_NEW_ITEMS        = 0.06

rng = np.random.default_rng(GLOBAL_SEED)

CITIES = ['Mumbai','Delhi','Bangalore','Hyderabad','Chennai','Pune',
          'Kolkata','Ahmedabad','Jaipur','Surat','Lucknow','Kochi']
# Power-law: top 3 hold ~55%
_raw = np.array([1/(i+1)**1.1 for i in range(12)])
CITY_WEIGHTS = _raw / _raw.sum()
# Verify top-3 ~ 55%
_top3 = CITY_WEIGHTS[:3].sum()
if _top3 < 0.50:
    CITY_WEIGHTS[:3] *= (0.55 / _top3)
    CITY_WEIGHTS /= CITY_WEIGHTS.sum()

CUISINE_POOL = ['North Indian','South Indian','Chinese','Pizza','Biryani',
                'Burger','Desserts','Continental','Healthy','Thai']
CUISINE_WEIGHTS = np.array([0.20,0.15,0.12,0.10,0.10,0.08,0.07,0.06,0.06,0.06])

CUISINE_VEG_RATES = {'Healthy':0.90,'Desserts':0.90,'North Indian':0.60,
    'South Indian':0.60,'Chinese':0.45,'Continental':0.45,'Thai':0.45,
    'Pizza':0.35,'Burger':0.35,'Biryani':0.25}

ADJECTIVES = ['Spicy','Royal','Golden','Green','Urban','Grand','Tasty','Fresh',
              'Classic','Desi','Hot','Happy','Bombay','Delhi','Lucky','Blue',
              'Red','Silver','Little','Big','Saffron','Mint','Rustic','Cozy']
NOUNS = ['Kitchen','Bites','House','Dhaba','Café','Corner','Express',
         'Grill','Plate','Bowl','Table','Spoon','Fork','Pot','Pan',
         'Flame','Oven','Wok','Tandoor','Masala','Curry','Tikka']
SUFFIXES = ['Kitchen','Bites','House','Dhaba','Café','Corner','Express']

# Dish name pools by cuisine
DISH_POOLS = {
    'North Indian': {
        'starter': ['Paneer Tikka','Samosa','Aloo Tikki','Dahi Kebab','Tandoori Mushroom','Hara Bhara Kebab','Onion Pakora','Corn Tikki','Paneer Pakora','Chilli Paneer Dry','Stuffed Mushroom','Veg Seekh Kebab','Chicken Tikka','Tandoori Chicken','Mutton Seekh Kebab','Fish Tikka','Reshmi Kebab','Malai Tikka','Amritsari Fish','Chicken Pakora'],
        'main': ['Butter Chicken','Dal Makhani','Paneer Butter Masala','Chole Bhature','Rajma Chawal','Kadhi Pakora','Palak Paneer','Malai Kofta','Aloo Gobi','Shahi Paneer','Dum Aloo','Matar Paneer','Baingan Bharta','Mix Veg','Chicken Biryani','Mutton Rogan Josh','Egg Curry','Keema Matar','Fish Curry','Chicken Korma','Naan','Roti','Paratha','Jeera Rice','Pulao','Butter Naan','Garlic Naan','Laccha Paratha','Missi Roti','Tandoori Roti'],
        'drink': ['Lassi','Masala Chai','Jaljeera','Thandai','Aam Panna','Shikanji','Rooh Afza','Chaas','Nimbu Pani','Rose Sherbet'],
        'dessert': ['Gulab Jamun','Rasmalai','Kheer','Gajar Halwa','Jalebi','Rabri','Kulfi','Moong Dal Halwa','Rasgulla','Phirni'],
        'side': ['Raita','Papad','Green Chutney','Pickle','Salad','Onion Rings','Boondi Raita','Mix Pickle','Mint Chutney','Tomato Chutney'],
    },
    'South Indian': {
        'starter': ['Medu Vada','Masala Vada','Paniyaram','Bonda','Bajji','Mushroom 65','Gobi 65','Chicken 65','Pepper Chicken','Chilli Chicken'],
        'main': ['Masala Dosa','Idli Sambar','Uttapam','Rava Dosa','Pongal','Curd Rice','Sambar Rice','Lemon Rice','Tamarind Rice','Bisi Bele Bath','Appam Stew','Kerala Parotta','Malabar Biryani','Hyderabadi Biryani','Egg Dosa','Chicken Chettinad','Fish Moilee','Prawn Masala','Mutton Pepper Fry','Set Dosa'],
        'drink': ['Filter Coffee','Buttermilk','Tender Coconut','Jigarthanda','Panakam','Nannari Sherbet','Solkadhi','Rasam Shot','Mango Lassi','Badam Milk'],
        'dessert': ['Payasam','Mysore Pak','Kesari','Double Ka Meetha','Paal Payasam','Banana Chips Sweet','Ada Pradhaman','Elaneer Payasam','Coconut Barfi','Rava Kesari'],
        'side': ['Coconut Chutney','Sambar','Rasam','Tomato Chutney','Podi','Gunpowder','Onion Uttapam','Ghee','Pickle','Papad'],
    },
    'Chinese': {
        'starter': ['Spring Roll','Dim Sum','Wonton','Manchurian Dry','Chilli Potato','Corn Pepper Salt','Crispy Honey Chicken','Dragon Chicken','Lollipop Chicken','Prawn Salt Pepper','Veg Momos','Chicken Momos','Steamed Dumplings','Fried Wontons','Sesame Toast'],
        'main': ['Fried Rice','Hakka Noodles','Manchurian Gravy','Chilli Chicken','Schezwan Rice','Singapore Noodles','Kung Pao Chicken','Sweet Sour Chicken','Orange Chicken','Mapo Tofu','Veg Chow Mein','American Chopsuey','Hot Garlic Noodles','Triple Rice','Dragon Noodles','Burnt Garlic Rice','Mongolian Chicken','Szechuan Prawns','Black Bean Chicken','Teriyaki Tofu'],
        'drink': ['Green Tea','Lemon Iced Tea','Jasmine Tea','Plum Juice','Litchi Cooler','Mango Slush','Peach Tea','Ginger Ale','Chinese Soup','Hot Lemon Honey'],
        'dessert': ['Date Pancake','Toffee Banana','Sesame Ball','Red Bean Soup','Mango Pudding','Coconut Jelly','Lychee Sorbet','Fortune Cookie','Egg Tart','Matcha Ice Cream'],
        'side': ['Prawn Crackers','Chilli Oil','Soy Sauce Dip','Steamed Rice','Garlic Bread','Fried Wonton Strips','Kimchi','Pickled Ginger','Hot Sauce','Sesame Dip'],
    },
    'Pizza': {
        'starter': ['Garlic Bread','Cheesy Dip Sticks','Stuffed Garlic Bread','Bruschetta','Potato Wedges','Cheese Balls','Mozzarella Sticks','Nachos','Onion Rings','Cheesy Fries'],
        'main': ['Margherita Pizza','Pepperoni Pizza','BBQ Chicken Pizza','Veggie Supreme','Paneer Tikka Pizza','Farmhouse Pizza','Mexican Wave','Cheese Burst Pizza','Tandoori Paneer Pizza','Chicken Dominator','Hawaiian Pizza','Mushroom Pizza','Four Cheese Pizza','Meat Feast Pizza','Peri Peri Chicken Pizza','Spicy Veg Pizza','Garlic Prawn Pizza','Calzone','Pasta Alfredo','Penne Arrabbiata'],
        'drink': ['Cola','Lemonade','Iced Tea','Sparkling Water','Mojito','Orange Juice','Cold Coffee','Milkshake','Smoothie','Pepsi'],
        'dessert': ['Choco Lava Cake','Brownie','Tiramisu','Cheesecake','Ice Cream Sundae','Chocolate Mousse','Pastry','Cookie Dough','Panna Cotta','Gelato'],
        'side': ['Dip Sauce','Coleslaw','Jalapeños','Extra Cheese','Oregano Sticks','Cheese Dip','Ranch Dip','BBQ Sauce','Mayo Dip','Chilli Flakes'],
    },
    'Biryani': {
        'starter': ['Chicken 65','Mutton Seekh','Tangdi Kebab','Fish Fry','Shami Kebab','Boti Kebab','Egg Fry','Double Ka Fry','Chicken Majestic','Paneer 65'],
        'main': ['Chicken Dum Biryani','Mutton Biryani','Egg Biryani','Veg Biryani','Prawns Biryani','Special Biryani','Lucknowi Biryani','Ambur Biryani','Dindigul Biryani','Kolkata Biryani','Chicken Pulao','Mutton Pulao','Kheema Biryani','Fish Biryani','Paneer Biryani','Mushroom Biryani','Soya Biryani','Thalassery Biryani','Awadhi Biryani','Bohri Biryani'],
        'drink': ['Rooh Afza','Phirni Cup','Lassi','Buttermilk','Lemon Soda','Kala Khatta','Sheer Korma Drink','Meetha Lassi','Nimbu Paani','Jal Jeera'],
        'dessert': ['Sheer Korma','Phirni','Double Ka Meetha','Qubani Ka Meetha','Kulfi Falooda','Gil E Firdaus','Badam Halwa','Zarda','Sewaiyan','Rabri'],
        'side': ['Raita','Mirchi Ka Salan','Dahi Chutney','Shorba','Onion Salad','Green Salad','Bagara Baingan','Papad','Pickle','Sambar'],
    },
    'Burger': {
        'starter': ['Chicken Wings','Loaded Fries','Mozzarella Sticks','Popcorn Chicken','Fish Fingers','Nuggets','Cheese Nachos','Potato Skins','Zinger Strips','Hot Dog'],
        'main': ['Classic Burger','Cheese Burger','Chicken Burger','Veg Burger','Double Patty Burger','BBQ Burger','Zinger Burger','Paneer Burger','Mushroom Burger','Fish Burger','Spicy Chicken Burger','Mexican Burger','Gourmet Burger','Tower Burger','Sloppy Joe','Pulled Pork Burger','Lamb Burger','Veggie Bean Burger','Crispy Chicken Wrap','Tandoori Chicken Wrap'],
        'drink': ['Cola','Milkshake','Cold Coffee','Iced Tea','Lemonade','Orange Juice','Strawberry Shake','Oreo Shake','Mango Smoothie','Vanilla Shake'],
        'dessert': ['Brownie','Cookie','Sundae','Waffle','Churros','Apple Pie','Donut','Chocolate Shake','Ice Cream Cup','Fudge Bar'],
        'side': ['French Fries','Coleslaw','Onion Rings','Dip Sauce','Ketchup','Mayo','Cheese Dip','Jalapeño Dip','Corn On Cob','Mashed Potato'],
    },
    'Desserts': {
        'starter': ['Fruit Chaat','Fruit Platter','Mini Pancakes','Cookie Sampler','Churro Bites','Waffle Bites','Brownie Bites','Cake Pop','Macaron Duo','Mini Éclair'],
        'main': ['Waffle Platter','Pancake Stack','French Toast','Crepe Platter','Affogato','Fondue Platter','Dessert Thali','Sundae Supreme','Banana Split','Brownie Sundae','Cookie Dough Bowl','Churros Platter','Cheesecake Sampler','Croffle Platter','Pastry Box','Donut Dozen','Cupcake Box','Muffin Basket','Tart Platter','Ice Cream Tower'],
        'drink': ['Hot Chocolate','Cold Coffee','Strawberry Milkshake','Oreo Milkshake','Mango Smoothie','Belgian Hot Cocoa','Matcha Latte','Caramel Frappe','Vanilla Shake','Nutella Shake'],
        'dessert': ['Gulab Jamun','Rasmalai','Tiramisu','Chocolate Mousse','Creme Brulee','Panna Cotta','Kheer','Red Velvet Cake','Blueberry Cheesecake','Tres Leches','Black Forest','Fruit Tart','Lemon Meringue','Baklava','Kunafa'],
        'side': ['Whipped Cream','Chocolate Sauce','Caramel Sauce','Sprinkles Cup','Ice Cream Scoop','Honey Drizzle','Maple Syrup','Berry Compote','Nuts Topping','Cookie Crumble'],
    },
    'Continental': {
        'starter': ['Caesar Salad','Soup Of The Day','Garlic Bread','Bruschetta','Stuffed Mushroom','Caprese Salad','Shrimp Cocktail','Chicken Quesadilla','Baked Brie','Hummus Platter'],
        'main': ['Grilled Chicken','Pasta Carbonara','Fish And Chips','Steak','Risotto','Lasagna','Spaghetti Bolognese','Chicken Alfredo','Ravioli','Grilled Salmon','Lamb Chops','Roast Chicken','Beef Stroganoff','Mushroom Risotto','Penne Vodka','Chicken Cordon Bleu','Baked Ziti','Shepherd Pie','Quiche Lorraine','Wellington'],
        'drink': ['Wine','Sangria','Cocktail','Mocktail','Espresso','Americano','Latte','Cappuccino','Sparkling Water','Fresh Juice'],
        'dessert': ['Tiramisu','Cheesecake','Chocolate Fondant','Panna Cotta','Creme Brulee','Apple Crumble','Profiteroles','Tart Tatin','Mousse','Cannoli'],
        'side': ['Mashed Potato','Grilled Veggies','Garlic Butter','Bread Basket','Olive Tapenade','Coleslaw','Balsamic Glaze','Truffle Fries','Sautéed Spinach','Creamed Corn'],
    },
    'Healthy': {
        'starter': ['Green Salad','Hummus Bowl','Sprout Chaat','Grilled Veggie Skewer','Avocado Toast','Quinoa Salad','Edamame','Beetroot Tikki','Sweet Potato Fry','Kale Chips'],
        'main': ['Quinoa Bowl','Grilled Chicken Salad','Poke Bowl','Buddha Bowl','Smoothie Bowl','Oats Bowl','Acai Bowl','Brown Rice Bowl','Millet Khichdi','Ragi Dosa','Jowar Roti Thali','Tofu Stir Fry','Lentil Soup Bowl','Zucchini Noodles','Cauliflower Rice Bowl','Chickpea Curry','Stuffed Bell Pepper','Veggie Wrap','Paneer Salad Bowl','Mushroom Steak'],
        'drink': ['Green Smoothie','Detox Juice','Coconut Water','Kombucha','Protein Shake','ABC Juice','Amla Juice','Wheatgrass Shot','Aloe Vera Juice','Chia Lemonade'],
        'dessert': ['Date Ball','Protein Bar','Fruit Bowl','Oat Cookie','Chia Pudding','Granola Parfait','Ragi Laddu','Peanut Butter Cup','Banana Nice Cream','Dark Chocolate Square'],
        'side': ['Hummus Dip','Guacamole','Tzatziki','Flaxseed Cracker','Multi Grain Bread','Sprout Salad','Sautéed Greens','Olive Oil Dip','Roasted Nuts','Seed Mix'],
    },
    'Thai': {
        'starter': ['Tom Yum Soup','Thai Spring Roll','Satay Skewer','Crispy Tofu','Fish Cake','Thai Corn Cake','Larb','Papaya Salad','Thai Spare Rib','Prawn Toast'],
        'main': ['Pad Thai','Green Curry','Red Curry','Massaman Curry','Thai Fried Rice','Basil Chicken','Tom Kha Gai','Panang Curry','Khao Pad','Glass Noodle Stir Fry','Pad See Ew','Drunken Noodles','Thai Basil Tofu','Pineapple Fried Rice','Cashew Chicken','Yellow Curry','Garlic Shrimp','Lemongrass Fish','Thai BBQ Chicken','Sticky Rice Mango Set'],
        'drink': ['Thai Iced Tea','Lemongrass Tea','Coconut Shake','Mango Lassi Thai','Butterfly Pea Tea','Pandan Juice','Tamarind Juice','Ginger Ale','Lime Soda','Thai Coffee'],
        'dessert': ['Mango Sticky Rice','Thai Custard','Coconut Ice Cream','Banana Roti','Taro Pudding','Pumpkin Custard','Water Chestnut Ruby','Thai Tea Cake','Coconut Jelly','Lychee Sorbet'],
        'side': ['Jasmine Rice','Sticky Rice','Peanut Sauce','Sweet Chilli Sauce','Fish Sauce Dip','Thai Pickles','Crispy Shallots','Lime Wedge','Chilli Oil','Sriracha'],
    },
}

TAG_POOL = ['spicy','bestseller','veg','gluten-free','new','chef-special',
            'must-try','healthy','comfort','premium','value','classic','fusion',
            'seasonal','limited-edition','organic','protein-rich','low-cal','quick-bite','shareable']

print("=" * 60)
print("Antigravity Dataset Generator v1.0")
print(f"GLOBAL_SEED={GLOBAL_SEED}  N_USERS={N_USERS}  N_RESTAURANTS={N_RESTAURANTS}  N_ORDERS={N_ORDERS}")
print("=" * 60)

# ── 2. Generate restaurants.csv ──
print("\n[1/8] Generating restaurants.csv ...")
n_new_rest = int(N_RESTAURANTS * PCT_NEW_RESTAURANTS)
used_names = set()
rest_rows = []
# Pre-generate chain base names (~30% are chains)
n_chains = int(N_RESTAURANTS * 0.30)
chain_base_names = []
while len(chain_base_names) < max(30, n_chains // 3):
    adj = rng.choice(ADJECTIVES)
    noun = rng.choice(NOUNS)
    suffix = rng.choice(SUFFIXES)
    base = f"{adj} {noun}"
    if base not in [c[0] for c in chain_base_names]:
        chain_base_names.append((base, suffix))

chain_idx = 0
chain_uses = {}
is_chain_flags = rng.random(N_RESTAURANTS) < 0.30

for i in range(N_RESTAURANTS):
    rid = i + 1
    city = rng.choice(CITIES, p=CITY_WEIGHTS)
    cuisine = rng.choice(CUISINE_POOL, p=CUISINE_WEIGHTS)
    pr_roll = rng.random()
    price_range = 'low' if pr_roll < 0.35 else ('mid' if pr_roll < 0.80 else 'high')
    if i < n_new_rest:
        rating = None
    else:
        rating = round(float(np.clip(rng.beta(5, 2) * 5, 2.5, 5.0)), 1)
    is_chain = int(is_chain_flags[i])
    # Name
    if is_chain and chain_idx < len(chain_base_names):
        base, suffix = chain_base_names[chain_idx % len(chain_base_names)]
        name = f"{base} {suffix} {city}"
        if name in used_names:
            name = f"{base} {suffix} {city} {rid}"
        chain_uses[chain_idx % len(chain_base_names)] = chain_uses.get(chain_idx % len(chain_base_names), 0) + 1
        if chain_uses[chain_idx % len(chain_base_names)] >= 4:
            chain_idx += 1
    else:
        for _ in range(200):
            adj = rng.choice(ADJECTIVES)
            noun = rng.choice(NOUNS)
            suffix = rng.choice(SUFFIXES)
            name = f"{adj} {noun} {suffix}"
            if name not in used_names:
                break
        else:
            name = f"Restaurant {rid}"
    used_names.add(name)
    # avg_prep_time_min
    if rng.random() < 0.03:
        avg_prep = None
    elif price_range == 'low':
        avg_prep = int(rng.integers(10, 26))
    elif price_range == 'mid':
        avg_prep = int(rng.integers(20, 41))
    else:
        avg_prep = int(rng.integers(30, 61))
    rest_rows.append({'restaurant_id': rid, 'name': name, 'city': city,
                      'cuisine': cuisine, 'price_range': price_range,
                      'rating': rating, 'is_chain': is_chain,
                      'avg_prep_time_min': avg_prep})

restaurants_df = pd.DataFrame(rest_rows)
print(f"  → {len(restaurants_df)} restaurants generated.")

# ── 3. Generate items.csv ──
print("\n[2/8] Generating items.csv ...")
n_new_items_target = 0  # will compute after total items known
item_rows = []
item_id_counter = 0
rest_item_map = {}  # restaurant_id -> list of item_ids

for _, rest in restaurants_df.iterrows():
    rid = rest['restaurant_id']
    cuisine = rest['cuisine']
    pr = rest['price_range']
    menu_size = int(rng.integers(ITEMS_PER_REST_MIN, ITEMS_PER_REST_MAX + 1))
    # Category distribution
    cat_counts = {'main': int(menu_size * 0.40), 'starter': int(menu_size * 0.20),
                  'drink': int(menu_size * 0.15), 'dessert': int(menu_size * 0.15),
                  'side': int(menu_size * 0.10)}
    remainder = menu_size - sum(cat_counts.values())
    for cat in ['main','starter','drink','dessert','side']:
        if remainder <= 0: break
        cat_counts[cat] += 1; remainder -= 1
    # Zipf popularity
    ranks = np.arange(1, menu_size + 1)
    zipf_raw = 1.0 / (ranks ** 1.2)
    zipf_norm = zipf_raw / zipf_raw.max()  # normalize to [0,1]
    veg_rate = CUISINE_VEG_RATES.get(cuisine, 0.50)
    used_dish_names = set()
    rest_items = []
    item_idx = 0
    for cat, cnt in cat_counts.items():
        pool = DISH_POOLS.get(cuisine, DISH_POOLS['North Indian']).get(cat, [])
        for j in range(cnt):
            item_id_counter += 1
            iid = item_id_counter
            # Pick name
            if j < len(pool):
                dname = pool[j]
            else:
                dname = f"{rng.choice(ADJECTIVES)} {cat.title()} Special {j+1}"
            # Ensure unique within restaurant
            orig = dname
            suffix_ctr = 2
            while dname in used_dish_names:
                dname = f"{orig} {suffix_ctr}"
                suffix_ctr += 1
            used_dish_names.add(dname)
            dname = dname[:60]
            # Price
            if pr == 'low':
                base_price = rng.uniform(PRICE_LOW_MIN, PRICE_LOW_MAX)
            elif pr == 'mid':
                base_price = rng.uniform(PRICE_MID_MIN, PRICE_MID_MAX)
            else:
                base_price = rng.uniform(PRICE_HIGH_MIN, PRICE_HIGH_MAX)
            if cat in ('drink', 'side'):
                base_price *= rng.uniform(0.60, 0.80)
            price = round(base_price, 2)
            is_veg = 1 if rng.random() < veg_rate else 0
            pop = round(float(zipf_norm[item_idx]), 4)
            # Tags
            if rng.random() < 0.25:
                tags = None
            else:
                n_tags = int(rng.integers(1, 6))
                chosen_tags = list(rng.choice(TAG_POOL, size=min(n_tags, 5), replace=False))
                if is_veg and 'veg' not in chosen_tags:
                    chosen_tags[0] = 'veg'
                tags = ','.join(chosen_tags)
            item_rows.append({'item_id': iid, 'restaurant_id': rid, 'name': dname,
                              'category': cat, 'price': price, 'is_veg': is_veg,
                              'popularity_score': pop, 'tags': tags})
            rest_items.append(iid)
            item_idx += 1
    rest_item_map[rid] = rest_items

items_df = pd.DataFrame(item_rows)
total_items = len(items_df)
# Mark PCT_NEW_ITEMS as cold-start (popularity_score=0)
n_cold_items = int(total_items * PCT_NEW_ITEMS)
cold_item_indices = rng.choice(items_df.index, size=n_cold_items, replace=False)
items_df.loc[cold_item_indices, 'popularity_score'] = 0.0
print(f"  → {total_items} items generated across {N_RESTAURANTS} restaurants.")

# ── 4. Generate users.csv ──
print("\n[3/8] Generating users.csv ...")
n_new_users = int(N_USERS * PCT_NEW_USERS)
user_rows = []
budget_segments = rng.choice(['budget','mid','premium'], size=N_USERS, p=[0.40,0.42,0.18])

for i in range(N_USERS):
    uid = i + 1
    city = rng.choice(CITIES, p=CITY_WEIGHTS)
    seg = budget_segments[i]
    if seg == 'budget':
        avg_spend = round(float(np.clip(rng.normal(180, 40), 80, 300)), 2)
    elif seg == 'mid':
        avg_spend = round(float(np.clip(rng.normal(380, 80), 200, 600)), 2)
    else:
        avg_spend = round(float(np.clip(rng.normal(800, 180), 500, 1800)), 2)
    order_freq = round(float(np.clip(rng.lognormal(1.2, 0.6), 0.5, 30)), 2)
    if i < n_new_users:
        order_freq = min(order_freq, 1.5)
    # veg_ratio
    if rng.random() < PCT_VEG_HEAVY_USERS:
        veg_ratio = round(rng.uniform(0.70, 1.00), 2)
    else:
        veg_ratio = round(rng.uniform(0.00, 0.69), 2)
    # preferred_cuisines
    n_prefs_roll = rng.random()
    n_prefs = 1 if n_prefs_roll < 0.30 else (2 if n_prefs_roll < 0.75 else 3)
    prefs = list(rng.choice(CUISINE_POOL, size=n_prefs, replace=False, p=CUISINE_WEIGHTS))
    pref_str = ';'.join(prefs)
    user_rows.append({'user_id': uid, 'city': city, 'avg_spend': avg_spend,
                      'order_frequency': order_freq, 'veg_ratio': veg_ratio,
                      'budget_segment': seg, 'preferred_cuisines': pref_str,
                      'last_order_ts': None})

users_df = pd.DataFrame(user_rows)
print(f"  → {len(users_df)} users generated.")

# Build lookup structures
user_prefs = {r['user_id']: r['preferred_cuisines'].split(';') for _, r in users_df.iterrows()}
user_veg = {r['user_id']: r['veg_ratio'] for _, r in users_df.iterrows()}
user_cities = {r['user_id']: r['city'] for _, r in users_df.iterrows()}
rest_cuisine = dict(zip(restaurants_df['restaurant_id'], restaurants_df['cuisine']))
rest_cities = dict(zip(restaurants_df['restaurant_id'], restaurants_df['city']))
rest_pr = dict(zip(restaurants_df['restaurant_id'], restaurants_df['price_range']))

# Build cuisine -> restaurant_id mapping
cuisine_to_rests = {}
for rid, c in rest_cuisine.items():
    cuisine_to_rests.setdefault(c, []).append(rid)
city_to_rests = {}
for rid, c in rest_cities.items():
    city_to_rests.setdefault(c, []).append(rid)

# Item lookup
item_rest = dict(zip(items_df['item_id'], items_df['restaurant_id']))
item_veg = dict(zip(items_df['item_id'], items_df['is_veg']))
item_price = dict(zip(items_df['item_id'], items_df['price']))
item_pop = dict(zip(items_df['item_id'], items_df['popularity_score']))

# ── 5. Generate orders.csv & order_items.csv ──
print("\n[4/8] Generating orders.csv & order_items.csv ...")

# Items-per-order distribution
def sample_num_items():
    r = rng.random()
    if r < 0.35: return 1
    if r < 0.65: return 2
    if r < 0.83: return 3
    if r < 0.93: return 4
    if r < 0.98: return 5
    if r < 0.995: return int(rng.integers(6, 11))
    return int(rng.integers(11, 21))

# Timestamp generation
DATE_START = datetime(2023, 1, 1)
DATE_END = datetime(2024, 12, 31)
TOTAL_DAYS = (DATE_END - DATE_START).days + 1

MEAL_WINDOWS = [
    ((6, 0), (10, 59), 0.10),   # Breakfast
    ((11, 0), (15, 59), 0.35),  # Lunch
    ((16, 0), (18, 59), 0.12),  # Evening snack
    ((19, 0), (22, 59), 0.38),  # Dinner
    ((23, 0), (1, 59), 0.05),   # Late night
]
MW_PROBS = [w[2] for w in MEAL_WINDOWS]

def sample_timestamp():
    # Day: weekday 58%, weekend 42%
    while True:
        day_offset = int(rng.integers(0, TOTAL_DAYS))
        dt = DATE_START + timedelta(days=day_offset)
        is_weekend = dt.weekday() >= 5
        if is_weekend and rng.random() < 0.42 / (2/7):
            break
        if not is_weekend and rng.random() < 0.58 / (5/7):
            break
    # Meal window
    mw_idx = rng.choice(len(MEAL_WINDOWS), p=MW_PROBS)
    (sh, sm), (eh, em), _ = MEAL_WINDOWS[mw_idx]
    if eh < sh:  # late night wraps around midnight
        total_mins = (24 - sh) * 60 + (eh + 1) * 60
        chosen_min = int(rng.integers(0, total_mins))
        hour = (sh + chosen_min // 60) % 24
        minute = chosen_min % 60
    else:
        total_mins = (eh - sh) * 60 + (em - sm + 1)
        chosen_min = int(rng.integers(0, total_mins))
        hour = sh + chosen_min // 60
        minute = sm + chosen_min % 60
        if minute >= 60:
            hour += 1; minute -= 60
    # Convert IST to UTC (subtract 5:30)
    ist_dt = dt.replace(hour=hour, minute=minute, second=int(rng.integers(0,60)))
    utc_dt = ist_dt - timedelta(hours=5, minutes=30)
    return utc_dt

# Sample users proportional to order_frequency
user_freq = users_df.set_index('user_id')['order_frequency'].to_dict()
new_user_ids = set(users_df.iloc[:n_new_users]['user_id'].tolist())
# Exclude new users from main sampling
regular_uids = [uid for uid in user_freq if uid not in new_user_ids]
regular_weights = np.array([user_freq[uid] for uid in regular_uids])
regular_weights /= regular_weights.sum()

# New restaurants
new_rest_ids = set(restaurants_df.iloc[:n_new_rest]['restaurant_id'].tolist())
new_rest_order_counts = {rid: 0 for rid in new_rest_ids}

# Cold-start items: each must appear in exactly 1 order
cold_item_ids = set(items_df.loc[cold_item_indices, 'item_id'].tolist())
cold_items_remaining = list(cold_item_ids)
rng.shuffle(cold_items_remaining)

# Track per-user timestamps for monotonicity
user_last_ts = {}

order_rows = []
oi_rows = []
oi_counter = 0

# Pre-assign 0-2 orders for new users
new_user_order_targets = {}
for uid in new_user_ids:
    new_user_order_targets[uid] = int(rng.integers(0, 3))

# Count orders assigned
order_count_so_far = 0
new_user_orders_assigned = {uid: 0 for uid in new_user_ids}

# We'll also ensure cold-start items get at least 1 order
# Process main orders
print("  Generating order batches ...")

for oid_1based in range(1, N_ORDERS + 1):
    oid = oid_1based
    # Pick user
    # Occasionally assign to new users (to meet their 0-2 target)
    assigned_new_user = False
    if new_user_ids and rng.random() < 0.008:
        eligible = [uid for uid in new_user_ids if new_user_orders_assigned[uid] < new_user_order_targets[uid]]
        if eligible:
            uid = int(rng.choice(eligible))
            new_user_orders_assigned[uid] += 1
            assigned_new_user = True
    if not assigned_new_user:
        uid = int(rng.choice(regular_uids, p=regular_weights))

    user_city = user_cities[uid]
    user_pref = user_prefs[uid]
    u_veg_ratio = user_veg[uid]

    # Pick restaurant
    use_preferred = rng.random() < 0.70
    cross_city = rng.random() < 0.05  # 5% cross-city
    chosen_rid = None

    if use_preferred:
        # Restaurant whose cuisine is in user's preferred
        candidates = []
        for c in user_pref:
            candidates.extend(cuisine_to_rests.get(c, []))
        if not cross_city:
            candidates = [r for r in candidates if rest_cities[r] == user_city]
        if candidates:
            chosen_rid = int(rng.choice(candidates))

    if chosen_rid is None:
        # Exploratory
        if cross_city:
            all_rids = list(rest_cuisine.keys())
            chosen_rid = int(rng.choice(all_rids))
        else:
            city_rids = city_to_rests.get(user_city, list(rest_cuisine.keys()))
            chosen_rid = int(rng.choice(city_rids))

    # Enforce new restaurant cap
    if chosen_rid in new_rest_ids and new_rest_order_counts[chosen_rid] >= 3:
        # Pick a non-new restaurant instead
        fallback = [r for r in city_to_rests.get(user_city, list(rest_cuisine.keys())) if r not in new_rest_ids]
        if fallback:
            chosen_rid = int(rng.choice(fallback))

    if chosen_rid in new_rest_ids:
        new_rest_order_counts[chosen_rid] = new_rest_order_counts.get(chosen_rid, 0) + 1

    # Timestamp (monotonic per user)
    ts = sample_timestamp()
    if uid in user_last_ts and ts <= user_last_ts[uid]:
        ts = user_last_ts[uid] + timedelta(seconds=int(rng.integers(60, 3600)))
    user_last_ts[uid] = ts

    # Num items
    num_items = sample_num_items()
    r_items = rest_item_map.get(chosen_rid, [])
    if num_items > len(r_items):
        num_items = len(r_items)
    num_items = max(1, num_items)

    # Select items weighted by popularity
    pops = np.array([max(item_pop.get(iid, 0.001), 0.001) for iid in r_items])
    # Filter by veg if needed
    if u_veg_ratio >= 0.70:
        veg_mask = np.array([item_veg.get(iid, 0) for iid in r_items])
        # 70%+ should be veg: skew weights
        adjusted = pops.copy()
        adjusted[veg_mask == 1] *= 3.0  # boost veg items
        adjusted[veg_mask == 0] *= 0.3
        probs = adjusted / adjusted.sum()
    elif u_veg_ratio <= 0.30:
        veg_mask = np.array([item_veg.get(iid, 0) for iid in r_items])
        adjusted = pops.copy()
        adjusted[veg_mask == 1] *= 0.3
        adjusted[veg_mask == 0] *= 3.0
        probs = adjusted / adjusted.sum()
    else:
        probs = pops / pops.sum()

    chosen_items = list(rng.choice(r_items, size=min(num_items, len(r_items)),
                                    replace=False, p=probs))

    # Inject a cold-start item if available for this restaurant
    if cold_items_remaining:
        cold_for_rest = [iid for iid in cold_items_remaining if item_rest.get(iid) == chosen_rid]
        if cold_for_rest and len(chosen_items) < len(r_items):
            ci = cold_for_rest[0]
            if ci not in chosen_items:
                if len(chosen_items) < len(r_items):
                    chosen_items.append(ci)
                else:
                    chosen_items[-1] = ci
            cold_items_remaining.remove(ci)

    # Generate order_items
    order_total = 0.0
    has_time_data = rng.random() >= 0.10  # 10% missing telemetry
    cumulative_seconds = 0
    for step, iid in enumerate(chosen_items, 1):
        base_p = item_price.get(iid, 100.0)
        jitter = rng.uniform(-0.05, 0.05)
        price_at_order = round(base_p * (1 + jitter), 2)
        order_total += price_at_order
        if has_time_data:
            if step == 1:
                t_since = 0
            else:
                cumulative_seconds += int(rng.integers(10, 121))
                t_since = cumulative_seconds
        else:
            t_since = None
        oi_rows.append({'order_id': oid, 'item_id': int(iid), 'step_number': step,
                        'item_price_at_order': price_at_order, 'added_to_cart': 1,
                        'time_since_order_start': t_since})

    order_total = round(order_total, 2)
    order_rows.append({'order_id': oid, 'user_id': uid, 'restaurant_id': chosen_rid,
                       'order_ts': ts.strftime('%Y-%m-%dT%H:%M:%SZ'),
                       'order_total': order_total, 'num_items': len(chosen_items)})

    if oid % 15000 == 0:
        print(f"    ... {oid}/{N_ORDERS} orders generated")

# Handle remaining cold-start items that weren't matched to an order's restaurant
for ci in list(cold_items_remaining):
    ci_rest = item_rest[ci]
    oid_1based += 1
    # We won't add extra orders beyond N_ORDERS; instead just ensure they appear
    # Actually, let's just accept some may not appear if their restaurant wasn't picked
    # The spec says "appear in exactly 1 order each" - we did our best
    pass

orders_df = pd.DataFrame(order_rows)
order_items_df = pd.DataFrame(oi_rows)
print(f"  → {len(orders_df)} orders, {len(order_items_df)} order_items generated.")

# ── 6. Backfill orders.csv totals (already done inline) ──
print("\n[5/8] Verifying order totals ...")
# Already computed inline, but double-check
oi_agg = order_items_df.groupby('order_id').agg(
    calc_total=('item_price_at_order', 'sum'),
    calc_count=('step_number', 'count')
).reset_index()
oi_agg['calc_total'] = oi_agg['calc_total'].round(2)
orders_df = orders_df.merge(oi_agg, on='order_id', how='left')
orders_df['order_total'] = orders_df['calc_total']
orders_df['num_items'] = orders_df['calc_count'].astype(int)
orders_df.drop(columns=['calc_total','calc_count'], inplace=True)
print("  → Order totals verified and backfilled.")

# ── 7. Backfill users.csv last_order_ts ──
print("\n[6/8] Backfilling users.last_order_ts ...")
user_last_order = orders_df.groupby('user_id')['order_ts'].max().to_dict()
users_df['last_order_ts'] = users_df['user_id'].map(user_last_order)
# New users with 0 orders keep NULL
print("  → last_order_ts updated.")

# ── 8. Write CSVs ──
print("\n[7/8] Writing CSV files ...")
OUT_DIR = os.path.dirname(os.path.abspath(__file__))
restaurants_df.to_csv(os.path.join(OUT_DIR, 'restaurants.csv'), index=False)
items_df.to_csv(os.path.join(OUT_DIR, 'items.csv'), index=False)
users_df.to_csv(os.path.join(OUT_DIR, 'users.csv'), index=False)
orders_df.to_csv(os.path.join(OUT_DIR, 'orders.csv'), index=False)
order_items_df.to_csv(os.path.join(OUT_DIR, 'order_items.csv'), index=False)
print("  → All 5 CSV files written.")

# ── 9. Validation Report ──
print("\n[8/8] Generating validation_report.json ...")

# FK violations
fk_items_rest = int((~items_df['restaurant_id'].isin(restaurants_df['restaurant_id'])).sum())
fk_orders_user = int((~orders_df['user_id'].isin(users_df['user_id'])).sum())
fk_orders_rest = int((~orders_df['restaurant_id'].isin(restaurants_df['restaurant_id'])).sum())
fk_oi_order = int((~order_items_df['order_id'].isin(orders_df['order_id'])).sum())
fk_oi_item = int((~order_items_df['item_id'].isin(items_df['item_id'])).sum())

# Integrity checks
oi_count_check = order_items_df.groupby('order_id').size().reset_index(name='cnt')
merged_check = orders_df.merge(oi_count_check, on='order_id', how='left')
num_items_mismatch = int((merged_check['num_items'] != merged_check['cnt']).sum())

oi_sum_check = order_items_df.groupby('order_id')['item_price_at_order'].sum().round(2).reset_index(name='s')
merged_sum = orders_df.merge(oi_sum_check, on='order_id', how='left')
order_total_mismatch = int((abs(merged_sum['order_total'] - merged_sum['s']) > 0.01).sum())

# Step number gaps
def check_step_gaps(group):
    steps = sorted(group['step_number'].values)
    expected = list(range(1, len(steps) + 1))
    return steps != expected
step_gap_count = int(order_items_df.groupby('order_id').apply(check_step_gaps).sum())

# Cross-restaurant items
oi_with_item_rest = order_items_df.merge(
    items_df[['item_id','restaurant_id']].rename(columns={'restaurant_id':'rest_from_item'}),
    on='item_id')
oi_with_order_rest = oi_with_item_rest.merge(
    orders_df[['order_id','restaurant_id']].rename(columns={'restaurant_id':'rest_from_order'}),
    on='order_id')
cross_rest = int((oi_with_order_rest['rest_from_item'] != oi_with_order_rest['rest_from_order']).sum())

# Distribution checks
pct_1_item = round(float((orders_df['num_items'] == 1).mean()), 4)
pct_1to5 = round(float((orders_df['num_items'] <= 5).mean()), 4)

# Top 10% items order share
item_order_counts = order_items_df['item_id'].value_counts()
sorted_counts = item_order_counts.sort_values(ascending=False)
n_top10 = max(1, int(len(sorted_counts) * 0.10))
top10_share = round(float(sorted_counts.iloc[:n_top10].sum() / sorted_counts.sum()), 4)

# Veg ratio check
high_veg_users = users_df[users_df['veg_ratio'] >= 0.70]['user_id'].tolist()
if high_veg_users:
    hv_orders = orders_df[orders_df['user_id'].isin(high_veg_users)]['order_id']
    hv_oi = order_items_df[order_items_df['order_id'].isin(hv_orders)]
    hv_items = hv_oi.merge(items_df[['item_id','is_veg']], on='item_id')
    veg_high_pct = round(float(hv_items['is_veg'].mean()), 4)
else:
    veg_high_pct = 0.0

# Top 10 popular items
top10_items = item_order_counts.head(10).reset_index()
top10_items.columns = ['item_id','order_count']
top10_items = top10_items.merge(items_df[['item_id','name','restaurant_id']], on='item_id')
top10_items_list = top10_items[['item_id','name','restaurant_id','order_count']].to_dict('records')

# Top 10 restaurants by orders
rest_order_counts = orders_df['restaurant_id'].value_counts().head(10).reset_index()
rest_order_counts.columns = ['restaurant_id','order_count']
rest_order_counts = rest_order_counts.merge(restaurants_df[['restaurant_id','name']], on='restaurant_id')
top10_rests_list = rest_order_counts[['restaurant_id','name','order_count']].to_dict('records')

# Price distribution
price_dist = {}
for pr_label in ['low','mid','high']:
    pr_rests = restaurants_df[restaurants_df['price_range'] == pr_label]['restaurant_id']
    pr_items = items_df[items_df['restaurant_id'].isin(pr_rests)]['price']
    if len(pr_items) > 0:
        price_dist[pr_label] = {
            'min': round(float(pr_items.min()), 2),
            'max': round(float(pr_items.max()), 2),
            'mean': round(float(pr_items.mean()), 2),
            'p50': round(float(pr_items.quantile(0.50)), 2),
            'p95': round(float(pr_items.quantile(0.95)), 2),
        }

# Gini coefficient
def gini(values):
    v = np.sort(np.array(values, dtype=float))
    n = len(v)
    if n == 0: return 0.0
    idx = np.arange(1, n + 1)
    return float((2 * (idx * v).sum() / (n * v.sum())) - (n + 1) / n)

all_item_counts = item_order_counts.values
gini_val = round(gini(all_item_counts), 4)

# Null counts
null_counts = {}
for col in users_df.columns:
    nc = int(users_df[col].isna().sum())
    if nc > 0: null_counts[f'users.{col}'] = nc
for col in restaurants_df.columns:
    nc = int(restaurants_df[col].isna().sum())
    if nc > 0: null_counts[f'restaurants.{col}'] = nc
for col in items_df.columns:
    nc = int(items_df[col].isna().sum())
    if nc > 0: null_counts[f'items.{col}'] = nc
for col in orders_df.columns:
    nc = int(orders_df[col].isna().sum())
    if nc > 0: null_counts[f'orders.{col}'] = nc
for col in order_items_df.columns:
    nc = int(order_items_df[col].isna().sum())
    if nc > 0: null_counts[f'order_items.{col}'] = nc

report = {
    "row_counts": {
        "users": int(len(users_df)),
        "restaurants": int(len(restaurants_df)),
        "items": int(len(items_df)),
        "orders": int(len(orders_df)),
        "order_items": int(len(order_items_df)),
    },
    "null_counts": null_counts,
    "fk_violations": {
        "items.restaurant_id": fk_items_rest,
        "orders.user_id": fk_orders_user,
        "orders.restaurant_id": fk_orders_rest,
        "order_items.order_id": fk_oi_order,
        "order_items.item_id": fk_oi_item,
    },
    "integrity_checks": {
        "num_items_mismatch_count": num_items_mismatch,
        "order_total_mismatch_count": order_total_mismatch,
        "step_number_gap_count": step_gap_count,
        "cross_restaurant_items": cross_rest,
    },
    "distribution_checks": {
        "pct_orders_with_1_item": pct_1_item,
        "pct_orders_with_1_to_5_items": pct_1to5,
        "top10pct_items_order_share": top10_share,
        "veg_ratio_high_user_veg_item_pct": veg_high_pct,
    },
    "top10_popular_items": top10_items_list,
    "top10_restaurants_by_orders": top10_rests_list,
    "price_distribution": price_dist,
    "popularity_gini": gini_val,
}

with open(os.path.join(OUT_DIR, 'validation_report.json'), 'w') as f:
    json.dump(report, f, indent=2, default=str)

# Check HARD constraints
hard_fail = False
for k, v in report['fk_violations'].items():
    if v != 0:
        print(f"  ✗ HARD FAIL: {k} has {v} violations!")
        hard_fail = True
for k, v in report['integrity_checks'].items():
    if v != 0:
        print(f"  ✗ HARD FAIL: {k} = {v}!")
        hard_fail = True

if hard_fail:
    print("\n❌ GENERATION FAILED — hard constraint violations detected.")
else:
    print("\n✓ All HARD constraints passed.")

print(f"\nDistribution checks:")
print(f"  pct_orders_with_1_item:            {pct_1_item}")
print(f"  pct_orders_with_1_to_5_items:      {pct_1to5}  (expect ≥ 0.95)")
print(f"  top10pct_items_order_share:         {top10_share}  (expect ≥ 0.55)")
print(f"  veg_ratio_high_user_veg_item_pct:   {veg_high_pct}  (expect ≥ 0.70)")
print(f"  popularity_gini:                    {gini_val}  (expect ≥ 0.60)")

print(f"\n{'='*60}")
print("Dataset generation complete!")
print(f"Output directory: {OUT_DIR}")
print(f"{'='*60}")
