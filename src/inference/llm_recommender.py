"""
llm_recommender.py
------------------
LLM-Powered "AI Edge" for the CSAO Recommendation System.
Uses a language model to provide deep contextual reasoning about meal completeness,
complementary pairings, and personalized descriptions — augmenting the core ML model.

This module demonstrates three LLM-augmented capabilities:
  1. Meal Completeness Reasoning  — Analyzes the cart and explains what's missing
  2. Smart Pairing Descriptions   — Generates natural-language reasons for each recommendation
  3. Contextual Re-Ranking Boost  — LLM scores each candidate for contextual fit

For the hackathon, this uses rule-based NLP with curated knowledge to demonstrate
the concept without requiring an API key. In production, this would call GPT-4/Gemini.

Usage:
    python src/inference/llm_recommender.py
"""

import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

# ── Curated Knowledge Base (simulates LLM reasoning) ─────────────────────────

MEAL_TEMPLATES = {
    "Indian": {
        "complete_meal": ["main", "side", "drink"],
        "pairings": {
            "naan": ["curry", "dal", "paneer", "butter chicken", "tikka masala"],
            "roti": ["curry", "dal", "sabzi", "paneer"],
            "rice": ["curry", "dal", "raita", "pickle"],
            "biryani": ["raita", "salan", "shorba", "kebab"],
            "curry": ["naan", "rice", "roti", "raita"],
            "dal": ["rice", "naan", "roti", "papad"],
            "dosa": ["chutney", "sambar", "vada"],
            "idli": ["sambar", "chutney", "vada"],
        },
        "missing_suggestions": {
            "no_main": "Your cart needs a main course! Try a curry, biryani, or thali to complete your meal.",
            "no_side": "Add a side like raita, naan, or salad to complement your meal.",
            "no_drink": "Don't forget a beverage! A lassi or buttermilk pairs perfectly with Indian food.",
        },
    },
    "Western": {
        "complete_meal": ["main", "side", "drink"],
        "pairings": {
            "burger": ["fries", "coleslaw", "onion rings", "shake"],
            "pizza": ["garlic bread", "pasta", "coke", "dip"],
            "pasta": ["garlic bread", "salad", "soup"],
            "sandwich": ["fries", "soup", "salad"],
        },
        "missing_suggestions": {
            "no_main": "Add a burger, pizza, or pasta as your main course!",
            "no_side": "Try adding fries, garlic bread, or a salad on the side.",
            "no_drink": "A cold drink or shake would go great with your order!",
        },
    },
    "Asian": {
        "complete_meal": ["main", "side", "drink"],
        "pairings": {
            "noodles": ["spring roll", "manchurian", "soup", "fried rice"],
            "fried rice": ["manchurian", "chilli", "spring roll"],
            "momos": ["soup", "chutney", "noodles"],
            "sushi": ["miso soup", "edamame", "green tea"],
        },
        "missing_suggestions": {
            "no_main": "Add noodles, fried rice, or a curry as your main dish!",
            "no_side": "Spring rolls or soup would complement your order perfectly.",
            "no_drink": "Try a refreshing iced tea or a warm soup!",
        },
    },
}

MEAL_TIME_CONTEXT = {
    "breakfast": {
        "description": "morning meal",
        "preferred_items": ["dosa", "idli", "paratha", "toast", "pancake", "omelette", "poha"],
        "avoid_items": ["biryani", "pizza", "burger"],
        "suggestion": "Light and energizing items perfect for starting your day."
    },
    "lunch": {
        "description": "afternoon meal",
        "preferred_items": ["thali", "rice", "biryani", "curry", "wrap"],
        "suggestion": "A filling, balanced meal to power through your afternoon."
    },
    "evening_snack": {
        "description": "evening snack time",
        "preferred_items": ["samosa", "pakora", "chaat", "momos", "fries", "sandwich"],
        "suggestion": "Quick bites and snacks perfect for tea-time cravings."
    },
    "dinner": {
        "description": "evening dinner",
        "preferred_items": ["curry", "biryani", "naan", "dal", "pasta", "pizza"],
        "suggestion": "Complete, satisfying meals to end your day right."
    },
    "late_night": {
        "description": "late-night craving",
        "preferred_items": ["burger", "pizza", "noodles", "ice cream", "shake"],
        "suggestion": "Comfort food for those late-night hunger pangs."
    },
}

MACRO_CUISINES = {
    "North Indian": "Indian", "South Indian": "Indian", "Biryani": "Indian",
    "Chinese": "Asian", "Thai": "Asian",
    "Pizza": "Western", "Burger": "Western", "Continental": "Western",
    "Desserts": "Universal", "Healthy": "Universal",
}


class LLMRecommender:
    """
    LLM-augmented recommendation layer that provides:
    1. Meal completeness analysis
    2. Natural-language pairing reasons
    3. Contextual re-ranking boost scores
    """

    def analyze_meal_completeness(self, cart_items: List[Dict], cuisine: str, meal_time: str) -> Dict:
        """
        Analyze the current cart and identify what's missing for a complete meal.
        Returns structured analysis with suggestions.
        """
        macro = MACRO_CUISINES.get(cuisine, "Indian")
        template = MEAL_TEMPLATES.get(macro, MEAL_TEMPLATES["Indian"])
        time_ctx = MEAL_TIME_CONTEXT.get(meal_time, MEAL_TIME_CONTEXT["dinner"])

        # Analyze cart composition
        cart_categories = set()
        cart_names = []
        for item in cart_items:
            cat = item.get("category", "main")
            cart_categories.add(cat)
            cart_names.append(item.get("name", "").lower())

        has_main = "main" in cart_categories
        has_side = "side" in cart_categories or "starter" in cart_categories
        has_drink = "drink" in cart_categories
        has_dessert = "dessert" in cart_categories

        # Completeness score
        required = template["complete_meal"]
        filled = sum(1 for r in required if r in cart_categories)
        completeness = filled / len(required) if required else 0

        # Missing items
        missing = []
        suggestions = []
        if not has_main:
            missing.append("main course")
            suggestions.append(template["missing_suggestions"].get("no_main", "Add a main course."))
        if not has_side:
            missing.append("side dish")
            suggestions.append(template["missing_suggestions"].get("no_side", "Add a side dish."))
        if not has_drink:
            missing.append("beverage")
            suggestions.append(template["missing_suggestions"].get("no_drink", "Add a drink."))

        # Specific pairing suggestions based on cart items
        pairing_suggestions = []
        for name in cart_names:
            for key, pairings in template.get("pairings", {}).items():
                if key in name:
                    pairing_suggestions.extend(pairings[:3])

        return {
            "completeness_score": round(completeness, 2),
            "meal_time_context": time_ctx["description"],
            "meal_time_suggestion": time_ctx["suggestion"],
            "missing_categories": missing,
            "suggestions": suggestions,
            "pairing_suggestions": list(set(pairing_suggestions))[:5],
            "cart_summary": f"Cart has {len(cart_items)} items: {', '.join(cart_names[:5])}",
        }

    def generate_pairing_reason(self, cart_items: List[Dict], recommended_item: Dict, cuisine: str) -> str:
        """
        Generate a natural-language explanation for why this item is recommended.
        Simulates LLM reasoning about food pairings.
        """
        rec_name = recommended_item.get("name", "").lower()
        rec_cat = recommended_item.get("category", "main")
        cart_names = [item.get("name", "").lower() for item in cart_items]

        macro = MACRO_CUISINES.get(cuisine, "Indian")
        template = MEAL_TEMPLATES.get(macro, MEAL_TEMPLATES["Indian"])

        # Check for specific pairings
        for cart_name in cart_names:
            for key, pairings in template.get("pairings", {}).items():
                if key in cart_name:
                    for p in pairings:
                        if p in rec_name:
                            return f"Classic pairing! {recommended_item['name']} goes perfectly with {cart_name.title()}."

        # Category-based reasons
        cart_cats = set(item.get("category", "") for item in cart_items)
        if rec_cat == "drink" and "drink" not in cart_cats:
            return f"Complete your meal with {recommended_item['name']} — a refreshing addition!"
        elif rec_cat == "side" and "side" not in cart_cats:
            return f"Add {recommended_item['name']} as a side for a more satisfying meal."
        elif rec_cat == "dessert" and "dessert" not in cart_cats:
            return f"End on a sweet note with {recommended_item['name']}!"
        elif rec_cat == "main" and "main" not in cart_cats:
            return f"Your meal needs a main course — {recommended_item['name']} is a popular choice!"

        return f"Customers who ordered similar items also loved {recommended_item['name']}."

    def contextual_boost_score(self, item: Dict, cart_items: List[Dict],
                                cuisine: str, meal_time: str) -> float:
        """
        Compute a contextual boost score [0.0, 1.0] for a candidate item.
        Higher = more contextually appropriate. Used to augment ML model scores.
        """
        score = 0.5  # neutral baseline
        rec_name = item.get("name", "").lower()
        rec_cat = item.get("category", "main")
        cart_names = [it.get("name", "").lower() for it in cart_items]
        cart_cats = set(it.get("category", "") for it in cart_items)

        macro = MACRO_CUISINES.get(cuisine, "Indian")
        template = MEAL_TEMPLATES.get(macro, MEAL_TEMPLATES["Indian"])
        time_ctx = MEAL_TIME_CONTEXT.get(meal_time, {})

        # Boost for missing categories
        if rec_cat not in cart_cats:
            score += 0.15

        # Boost for specific pairings
        for cart_name in cart_names:
            for key, pairings in template.get("pairings", {}).items():
                if key in cart_name:
                    if any(p in rec_name for p in pairings):
                        score += 0.25
                        break

        # Boost for meal-time appropriate items
        preferred = time_ctx.get("preferred_items", [])
        if any(p in rec_name for p in preferred):
            score += 0.10

        # Penalize for meal-time inappropriate items
        avoid = time_ctx.get("avoid_items", [])
        if any(a in rec_name for a in avoid):
            score -= 0.20

        return max(0.0, min(1.0, score))


# ── FastAPI Integration Endpoint ──────────────────────────────────────────────

def get_meal_analysis(cart_items, cuisine, meal_time):
    """Public API for meal completeness analysis."""
    llm = LLMRecommender()
    return llm.analyze_meal_completeness(cart_items, cuisine, meal_time)


def get_pairing_reasons(cart_items, recommendations, cuisine):
    """Public API for generating pairing reasons for all recommendations."""
    llm = LLMRecommender()
    reasons = []
    for rec in recommendations:
        reason = llm.generate_pairing_reason(cart_items, rec, cuisine)
        reasons.append({"item_id": rec.get("item_id"), "reason": reason})
    return reasons


# ── Standalone Test ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    llm = LLMRecommender()

    # Test: Garlic Naan in cart
    cart = [{"name": "Garlic Naan", "category": "side", "price": 60}]
    recs = [
        {"name": "Butter Chicken", "category": "main", "price": 320, "item_id": 1},
        {"name": "Dal Makhani", "category": "main", "price": 250, "item_id": 2},
        {"name": "Lassi", "category": "drink", "price": 80, "item_id": 3},
    ]

    print("=== MEAL COMPLETENESS ANALYSIS ===")
    analysis = llm.analyze_meal_completeness(cart, "North Indian", "dinner")
    for k, v in analysis.items():
        print(f"  {k}: {v}")

    print("\n=== PAIRING REASONS ===")
    for rec in recs:
        reason = llm.generate_pairing_reason(cart, rec, "North Indian")
        print(f"  {rec['name']}: {reason}")

    print("\n=== CONTEXTUAL BOOST SCORES ===")
    for rec in recs:
        score = llm.contextual_boost_score(rec, cart, "North Indian", "dinner")
        print(f"  {rec['name']}: {score:.2f}")
