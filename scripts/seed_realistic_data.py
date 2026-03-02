import pymongo
import pandas as pd
import random
import os
from dotenv import load_dotenv

# Load env variables from backend
backend_env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'backend', '.env')
load_dotenv(dotenv_path=backend_env_path)

# Top 30 Indian Cities
cities = [
    "Bangalore", "Mumbai", "Delhi", "Hyderabad", "Chennai", "Kolkata", 
    "Pune", "Ahmedabad", "Jaipur", "Chandigarh", "Lucknow", "Kanpur", 
    "Nagpur", "Indore", "Bhopal", "Visakhapatnam", "Patna", "Vadodara", 
    "Ghaziabad", "Ludhiana", "Agra", "Nashik", "Faridabad", "Meerut", 
    "Rajkot", "Kalyan", "Vasai-Virar", "Varanasi", "Srinagar", "Aurangabad"
]

# Procedural Name Generation Assets
restaurant_prefixes = ["The Great", "Royal", "Spicy", "Golden", "Red", "Blue", "New", "Famous", "Urban", "Vintage", "Grand", "Modern", "Classic", "Authentic"]
restaurant_nouns = ["Kitchen", "Diner", "Bistro", "Cafe", "Grill", "Tandoor", "Palace", "Bowl", "Plate", "Oven", "Wok", "Spoon", "Fork", "Table", "House", "Hut"]
regional_names_north = ["Punjab", "Delhi", "Amritsar", "Chandni Chowk", "Dhaba", "Mughal", "Nawab"]
regional_names_south = ["Madras", "Chettinad", "Malabar", "Andhra", "Mysore", "Deccan", "Udupi"]
modern_names = ["Eats", "Bites", "Cravings", "Munch", "Feast", "Savour", "Zest", "Spice", "Taste", "Flavor"]

cuisines = ["Biryani", "Burger", "Pizza", "South Indian", "North Indian", "Desserts", "Healthy", "Continental", "Bengali", "Gujarati", "Street Food", "Rajasthani", "Chinese", "Italian", "Mexican", "Lebanese"]

# Map typical cuisines to cities (for slight regional weighting)
city_cuisine_bias = {
    "Bangalore": ["South Indian", "Biryani", "Burger", "Healthy"],
    "Mumbai": ["Street Food", "Continental", "Pizza", "North Indian"],
    "Delhi": ["North Indian", "Mughlai", "Street Food", "Burger"],
    "Hyderabad": ["Biryani", "Mughlai", "South Indian"],
    "Chennai": ["South Indian", "Biryani", "Chettinad"],
    "Kolkata": ["Bengali", "Chinese", "Desserts", "Biryani"],
    "Ahmedabad": ["Gujarati", "Street Food", "Healthy", "Pizza"],
    "Jaipur": ["Rajasthani", "North Indian", "Street Food"]
}

generic_restaurant_images = [
    "https://images.unsplash.com/photo-1517248135467-4c7edcad34c4?w=400&q=80",
    "https://images.unsplash.com/photo-1552566626-52f8b828add9?w=400&q=80",
    "https://images.unsplash.com/photo-1555396273-367ea4eb4db5?w=400&q=80",
    "https://images.unsplash.com/photo-1514933651103-005eec06c04b?w=400&q=80",
    "https://images.unsplash.com/photo-1414235077428-338989a2e8c0?w=400&q=80",
    "https://images.unsplash.com/photo-1424847651672-bf20a4b0982b?w=400&q=80",
    "https://images.unsplash.com/photo-1466978913421-bac2e104d72b?w=400&q=80",
    "https://images.unsplash.com/photo-1578474846511-04245941c4d9?w=400&q=80"
]

item_templates = {
    "Biryani": [
        ("Chicken Dum Biryani", "main", 299, 0, "https://images.unsplash.com/photo-1563379091339-03b21ab4a4f8?w=300&q=80"),
        ("Mutton Zafrani Biryani", "main", 399, 0, "https://images.unsplash.com/photo-1631515243349-e0cb75fb8d3a?w=300&q=80"),
        ("Paneer Special Biryani", "main", 249, 1, "https://images.unsplash.com/photo-1505253758473-96b7015fcd40?w=300&q=80"),
        ("Chicken Tikka Kebab", "starter", 220, 0, "https://images.unsplash.com/photo-1606491956689-2ea866880c84?w=300&q=80"),
        ("Mirchi Ka Salan", "side", 90, 1, "https://images.unsplash.com/photo-1589302168068-964664d93cb0?w=300&q=80"),
        ("Boondi Raita", "side", 75, 1, "https://images.unsplash.com/photo-1546833999-b9f581a1996d?w=300&q=80"),
        ("Onion Cucumber Raita", "side", 80, 1, "https://images.unsplash.com/photo-1546833999-b9f581a1996d?w=300&q=80"),
        ("Coke 330ml", "drink", 60, 1, "https://images.unsplash.com/photo-1622483767028-3f66f32aef97?w=300&q=80"),
        ("Diet Coke Can", "drink", 75, 1, "https://images.unsplash.com/photo-1622483767028-3f66f32aef97?w=300&q=80"),
    ],
    "Burger": [
        ("Classic Cheese Burger", "main", 149, 1, "https://images.unsplash.com/photo-1568901346375-23c9450c58cd?w=300&q=80"),
        ("Crispy Chicken Burger", "main", 189, 0, "https://images.unsplash.com/photo-1594212686125-9f5cefb6a827?w=300&q=80"),
        ("Double Patty Overload", "main", 259, 0, "https://images.unsplash.com/photo-1586816001966-79b736744398?w=300&q=80"),
        ("French Fries", "side", 99, 1, "https://images.unsplash.com/photo-1576107232684-1279f3908581?w=300&q=80"),
        ("Chocolate Thickshake", "drink", 180, 1, "https://images.unsplash.com/photo-1572490122747-3968b75cc699?w=300&q=80"),
    ],
    "Pizza": [
        ("Margherita Pizza", "main", 299, 1, "https://images.unsplash.com/photo-1513104890138-7c749659a591?w=300&q=80"),
        ("Pepperoni Pizza", "main", 499, 0, "https://images.unsplash.com/photo-1628840042765-356cda07504e?w=300&q=80"),
        ("Farmhouse Pizza", "main", 399, 1, "https://images.unsplash.com/photo-1574071318508-1cbbab50d00c?w=300&q=80"),
        ("Garlic Breadsticks", "starter", 149, 1, "https://images.unsplash.com/photo-1573140247632-f8fd74997d5c?w=300&q=80"),
        ("Choco Lava Cake", "dessert", 110, 1, "https://images.unsplash.com/photo-1551024601-bec78aea704b?w=300&q=80"),
    ],
    "South Indian": [
        ("Masala Dosa", "main", 120, 1, "https://images.unsplash.com/photo-1589301760014-d929f39ce9b0?w=300&q=80"),
        ("Idli Sambar", "starter", 80, 1, "https://images.unsplash.com/photo-1610192244261-3f3388cd26f3?w=300&q=80"),
        ("Medu Vada", "starter", 90, 1, "https://images.unsplash.com/photo-1626804475297-4160fab1ccfa?w=300&q=80"),
        ("Filter Coffee", "drink", 50, 1, "https://images.unsplash.com/photo-1521302200778-33500795e128?w=300&q=80"),
    ],
    "North Indian": [
        ("Butter Chicken", "main", 350, 0, "https://images.unsplash.com/photo-1604908176997-125f25cc6f3d?w=300&q=80"),
        ("Dal Makhani", "main", 250, 1, "https://images.unsplash.com/photo-1544026229-2ceec1a86827?w=300&q=80"),
        ("Garlic Naan", "side", 60, 1, "https://images.unsplash.com/photo-1626082927389-6cd097cdc6ec?w=300&q=80"),
        ("Paneer Tikka", "starter", 220, 1, "https://images.unsplash.com/photo-1567158780131-7e614bbd2109?w=300&q=80"),
        ("Lassi", "drink", 90, 1, "https://images.unsplash.com/photo-1498654877395-865dcbf0802c?w=300&q=80"),
    ],
    "Desserts": [
        ("Chocolate Brownie", "dessert", 150, 1, "https://images.unsplash.com/photo-1603513361099-2eeb2be05c86?w=300&q=80"),
        ("Belgian Waffle", "dessert", 220, 1, "https://images.unsplash.com/photo-1562376552-0d1f143c08f1?w=300&q=80"),
        ("Red Velvet Cupcake", "dessert", 120, 1, "https://images.unsplash.com/photo-1614707267537-b85aaf00c4b7?w=300&q=80"),
        ("Vanilla Ice Cream", "dessert", 90, 1, "https://images.unsplash.com/photo-1551024601-bec78aea704b?w=300&q=80"),
        ("Cold Coffee", "drink", 140, 1, "https://images.unsplash.com/photo-1461023058943-07fcbe16d735?w=300&q=80"),
    ],
    "Healthy": [
        ("Quinoa Salad bowl", "main", 250, 1, "https://images.unsplash.com/photo-1512621776951-a57141f2eefd?w=300&q=80"),
        ("Grilled Chicken Breast", "main", 299, 0, "https://images.unsplash.com/photo-1626082927389-6cd097cdc6ec?w=300&q=80"),
        ("Avocado Toast", "starter", 199, 1, "https://images.unsplash.com/photo-1588137378633-dea1336ce1e2?w=300&q=80"),
        ("Green Detox Juice", "drink", 149, 1, "https://images.unsplash.com/photo-1622483767028-3f66f32aef97?w=300&q=80"),
    ],
    "Continental": [
        ("Chicken Alfredo Pasta", "main", 320, 0, "https://images.unsplash.com/photo-1621996346565-e3dbc646d9a9?w=300&q=80"),
        ("Fish and Chips", "main", 380, 0, "https://images.unsplash.com/photo-1555396273-367ea4eb4db5?w=300&q=80"),
        ("Mushroom Risotto", "main", 340, 1, "https://images.unsplash.com/photo-1529042410759-befb1204b468?w=300&q=80"),
        ("Lemon Iced Tea", "drink", 110, 1, "https://images.unsplash.com/photo-1498654877395-865dcbf0802c?w=300&q=80")
    ],
    "Bengali": [
        ("Kosha Mangsho", "main", 450, 0, "https://images.unsplash.com/photo-1604908176997-125f25cc6f3d?w=300&q=80"),
        ("Fish Curry", "main", 350, 0, "https://images.unsplash.com/photo-1596797038530-2c107229654b?w=300&q=80"),
        ("Luchi", "side", 60, 1, "https://images.unsplash.com/photo-1589301760014-d929f39ce9b0?w=300&q=80"),
        ("Rosogolla", "dessert", 50, 1, "https://images.unsplash.com/photo-1551024601-bec78aea704b?w=300&q=80"),
    ],
    "Gujarati": [
        ("Gujarati Thali", "main", 400, 1, "https://images.unsplash.com/photo-1613069150035-7d52f6b8c9df?w=300&q=80"),
        ("Khaman Dhokla", "starter", 100, 1, "https://images.unsplash.com/photo-1563379091339-03b21ab4a4f8?w=300&q=80"),
        ("Thepla", "side", 80, 1, "https://images.unsplash.com/photo-1589301760014-d929f39ce9b0?w=300&q=80"),
        ("Chaash", "drink", 40, 1, "https://images.unsplash.com/photo-1498654877395-865dcbf0802c?w=300&q=80"),
    ],
    "Street Food": [
        ("Pani Puri", "starter", 50, 1, "https://images.unsplash.com/photo-1606491956689-2ea866880c84?w=300&q=80"),
        ("Pav Bhaji", "main", 120, 1, "https://images.unsplash.com/photo-1589301760014-d929f39ce9b0?w=300&q=80"),
        ("Vada Pav", "starter", 40, 1, "https://images.unsplash.com/photo-1626804475297-4160fab1ccfa?w=300&q=80"),
        ("Masala Chai", "drink", 20, 1, "https://images.unsplash.com/photo-1544026229-2ceec1a86827?w=300&q=80"),
    ],
    "Rajasthani": [
        ("Dal Baati Churma", "main", 350, 1, "https://images.unsplash.com/photo-1544026229-2ceec1a86827?w=300&q=80"),
        ("Laal Maas", "main", 450, 0, "https://images.unsplash.com/photo-1604908176997-125f25cc6f3d?w=300&q=80"),
        ("Gatte Ki Sabzi", "side", 200, 1, "https://images.unsplash.com/photo-1589302168068-964664d93cb0?w=300&q=80"),
        ("Jaljeera", "drink", 50, 1, "https://images.unsplash.com/photo-1622483767028-3f66f32aef97?w=300&q=80"),
    ],
    "Chinese": [
        ("Hakka Noodles", "main", 199, 1, "https://images.unsplash.com/photo-1585032226651-759b368d7246?w=300&q=80"),
        ("Chilli Chicken", "starter", 249, 0, "https://images.unsplash.com/photo-1525755662778-989d0524087e?w=300&q=80"),
        ("Veg Manchurian", "starter", 189, 1, "https://images.unsplash.com/photo-1585937421612-70a008356fbe?w=300&q=80"),
        ("Burnt Garlic Fried Rice", "main", 220, 1, "https://images.unsplash.com/photo-1512058564366-18510be2db19?w=300&q=80")
    ],
    "Italian": [
        ("Penne Arrabbiata", "main", 280, 1, "https://images.unsplash.com/photo-1621996346565-e3dbc646d9a9?w=300&q=80"),
        ("Spicy Salami Pizza", "main", 450, 0, "https://images.unsplash.com/photo-1628840042765-356cda07504e?w=300&q=80"),
        ("Garlic Bread With Cheese", "starter", 180, 1, "https://images.unsplash.com/photo-1573140247632-f8fd74997d5c?w=300&q=80"),
        ("Tiramisu", "dessert", 250, 1, "https://images.unsplash.com/photo-1571115177098-24ec2b6e57a5?w=300&q=80")
    ]
}

def generate_restaurant_name(city, cuisine):
    # Base it slightly off city geography
    if city in ["Delhi", "Chandigarh", "Ludhiana", "Patna", "Lucknow", "Agra", "Kanpur"]:
        name_part1 = random.choice(regional_names_north + restaurant_prefixes)
    elif city in ["Chennai", "Bangalore", "Hyderabad", "Visakhapatnam"]:
        name_part1 = random.choice(regional_names_south + restaurant_prefixes)
    else:
        name_part1 = random.choice(restaurant_prefixes + modern_names)

    name_part2 = random.choice(restaurant_nouns + modern_names)
    
    # Randomly append the cuisine
    if random.random() > 0.6:
        return f"{name_part1} {name_part2} {cuisine}"
    elif random.random() > 0.5:
        return f"The {name_part1} {name_part2}"
    else:
        return f"{name_part1} {name_part2}"

def main():
    MONGO_URI = os.getenv("MONGO_URI")
    if not MONGO_URI:
        print("ERROR: Could not find MONGO_URI inside backend/.env")
        return

    print(f"Connecting to MongoDB: {MONGO_URI[:30]}...")
    client = pymongo.MongoClient(MONGO_URI)
    db = client.get_database() # Defaults to db name in URI path

    print("Dropping existing collections in Atlas...")
    db.restaurants.drop()
    db.items.drop()

    print("Generating MASSIVE Seed Data (50 Restaurants per City)...")
    
    gen_restaurants = []
    gen_items = []

    restaurant_id_counter = 1
    item_id_counter = 1
    
    RESTAURANTS_PER_CITY = 50

    for city in cities:
        for i in range(RESTAURANTS_PER_CITY):
            # Pick a cuisine (weighted slightly by city preference)
            if city in city_cuisine_bias and random.random() > 0.4:
                cuisine = random.choice(city_cuisine_bias[city])
            else:
                cuisine = random.choice(cuisines)

            rest_name = generate_restaurant_name(city, cuisine)
            
            # Use specific template images if they exist, else random generic
            if cuisine in item_templates:
                # Use the photo from the first main item of this cuisine as the restaurant photo
                img = item_templates[cuisine][0][4]
            else:
                img = random.choice(generic_restaurant_images)

            r_data = {
                "restaurant_id": restaurant_id_counter,
                "name": rest_name,
                "cuisine": cuisine,
                "price_range": random.choice(["low", "mid", "mid", "high", "premium"]),
                "rating": round(random.uniform(3.0, 5.0), 1),
                "is_chain": random.choice([0, 0, 0, 1]), # 25% chance of being a chain
                "avg_prep_time_min": random.choice([15, 20, 25, 30, 35, 40, 45]),
                "image_url": img,
                "city": city
            }
            gen_restaurants.append(r_data)
            
            # Fetch matching item template
            base_cuisine = cuisine
            if base_cuisine not in item_templates:
                base_cuisine = random.choice(list(item_templates.keys()))
            
            menu = item_templates[base_cuisine]
            for item in menu:
                # Scramble prices slightly so they aren't all perfectly identical menus
                base_price = item[2]
                wiggled_price = base_price + random.randint(-4, 6) * 10
                if wiggled_price < 20: 
                    wiggled_price = 20

                i_data = {
                    "item_id": item_id_counter,
                    "restaurant_id": restaurant_id_counter,
                    "name": item[0],
                    "category": item[1],
                    "price": wiggled_price,
                    "is_veg": item[3],
                    "popularity_score": round(random.uniform(10, 100), 2),
                    "image_url": item[4]
                }
                gen_items.append(i_data)
                item_id_counter += 1
                
            restaurant_id_counter += 1

    print(f"✅ Generated {len(gen_restaurants)} restaurants and {len(gen_items)} items.")
    
    # 1. Insert into MongoDB
    print("Uploading to MongoDB Atlas (This might take a few moments)...")
    db.restaurants.insert_many(gen_restaurants)
    db.items.insert_many(gen_items)
    
    # Create text indices manually
    db.restaurants.create_index([("name", "text"), ("cuisine", "text"), ("city", "text")])
    db.items.create_index([("name", "text"), ("category", "text")])

    print("✅ MongoDB Atlas Seed Successful.")

    # 2. Write to CSV for ML Inference Cache Sync
    print("Syncing ML CSVs...")
    
    df_rest = pd.DataFrame(gen_restaurants)
    df_rest = df_rest[["restaurant_id", "name", "cuisine", "price_range", "rating", "is_chain", "avg_prep_time_min", "image_url", "city"]]
    
    df_items = pd.DataFrame(gen_items)
    df_items = df_items[["item_id", "restaurant_id", "name", "category", "price", "is_veg", "popularity_score", "image_url"]]
    
    raw_dir = os.path.join("d:\\", "zomathon", "data", "raw")
    os.makedirs(raw_dir, exist_ok=True)
    
    rest_csv_path = os.path.join(raw_dir, "restaurants.csv")
    items_csv_path = os.path.join(raw_dir, "items.csv")
    
    df_rest.to_csv(rest_csv_path, index=False)
    df_items.to_csv(items_csv_path, index=False)
    
    print(f"✅ Saved DataFrame to {rest_csv_path}")
    print(f"✅ Saved DataFrame to {items_csv_path}")
    print("ALL SEEDING OPERATIONS COMPLETED SAFELY!")

if __name__ == "__main__":
    main()
