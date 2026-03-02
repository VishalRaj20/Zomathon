"""
api/main.py
-----------
FastAPI demo for the Context-Aware Add-on Recommendation System.

Install:
    pip install fastapi uvicorn

Run:
    uvicorn api.main:app --reload --port 8000
    # or from project root:
    python -m uvicorn api.main:app --reload

Try it:
    curl -X POST http://localhost:8000/recommend \
      -H "Content-Type: application/json" \
      -d '{"user_id": 1, "restaurant_id": 1, "cart_items": [], "timestamp": "2024-11-15T19:30:00"}'

Swagger UI:
    http://localhost:8000/docs
"""

from datetime import datetime
from typing import List

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# ── Adjust import path when running as a module from project root ─────────────
import sys
import importlib
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import src.inference.recommender as _rec_mod
importlib.reload(_rec_mod)
from src.inference.recommender import recommend as _recommend, _get_items

import src.inference.llm_recommender as _llm_mod
importlib.reload(_llm_mod)
from src.inference.llm_recommender import LLMRecommender

_llm = LLMRecommender()

app = FastAPI(
    title="Add-on Recommendation API",
    description="Context-aware food add-on recommender with LLM-powered meal analysis — Zomathon hackathon",
    version="2.0.0",
)


# ── Schemas ───────────────────────────────────────────────────────────────────

class RecommendRequest(BaseModel):
    user_id:       int
    restaurant_id: int
    cart_items:    List[int] = []
    timestamp:     datetime = None
    top_k:         int = 8
    city:          str = ""

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": 1,
                "restaurant_id": 1,
                "cart_items": [101, 205],
                "timestamp": "2024-11-15T19:30:00",
                "top_k": 8,
            }
        }


class RecommendedItem(BaseModel):
    item_id: int
    name: str
    category: str
    price: float
    is_veg: int

class RecommendResponse(BaseModel):
    user_id:          int
    restaurant_id:    int
    cart_items:       List[RecommendedItem]
    recommendations:  List[RecommendedItem]
    pairing_reasons:  list = []
    meal_analysis:    dict = {}
    timestamp_used:   str


class MealAnalysisRequest(BaseModel):
    cart_items: list = []
    cuisine: str = "North Indian"
    meal_time: str = "dinner"

    class Config:
        json_schema_extra = {
            "example": {
                "cart_items": [{"name": "Garlic Naan", "category": "side", "price": 60}],
                "cuisine": "North Indian",
                "meal_time": "dinner",
            }
        }


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/", summary="Health check")
def root():
    return {"status": "ok", "service": "add-on recommender", "version": "2.0.0", "ai_edge": "LLM meal analysis enabled"}


@app.post("/recommend", response_model=RecommendResponse, summary="Get add-on recommendations with LLM analysis")
def recommend_endpoint(req: RecommendRequest):
    ts = req.timestamp or datetime.utcnow()
    try:
        recs = _recommend(
            user_id=req.user_id,
            restaurant_id=req.restaurant_id,
            cart_items=req.cart_items,
            timestamp=ts,
            top_k=req.top_k,
            city=req.city,
        )
        
        items_df = _get_items()
        
        def _enrich(ids):
            res = []
            for iid in ids:
                row = items_df[items_df["item_id"] == iid]
                if not row.empty:
                    r = row.iloc[0]
                    res.append(RecommendedItem(
                        item_id=iid,
                        name=r.get("name", "Unknown"),
                        category=r.get("category", "?"),
                        price=float(r.get("price", 0.0)),
                        is_veg=int(r.get("is_veg", 0))
                    ))
                else:
                    res.append(RecommendedItem(item_id=iid, name="Unknown", category="?", price=0.0, is_veg=0))
            return res

        rich_recs = _enrich(recs)
        rich_cart = _enrich(req.cart_items)
        
        # LLM: Generate pairing reasons
        cart_dicts = [{"name": c.name, "category": c.category, "price": c.price} for c in rich_cart]
        rec_dicts = [{"name": r.name, "category": r.category, "price": r.price, "item_id": r.item_id} for r in rich_recs]
        
        # Detect cuisine from restaurant
        rest_df = items_df[items_df["item_id"].isin(req.cart_items + recs)]
        cuisine = "North Indian"  # default fallback
        
        hour = ts.hour
        meal_time = "breakfast" if hour < 11 else "lunch" if hour < 16 else "evening_snack" if hour < 19 else "dinner" if hour < 23 else "late_night"
        
        pairing_reasons = []
        meal_analysis = {}
        try:
            for rec in rec_dicts:
                reason = _llm.generate_pairing_reason(cart_dicts, rec, cuisine)
                pairing_reasons.append({"item_id": rec["item_id"], "reason": reason})
            meal_analysis = _llm.analyze_meal_completeness(cart_dicts, cuisine, meal_time)
        except Exception:
            pass
                
    except FileNotFoundError as e:
        raise HTTPException(
            status_code=503,
            detail=f"Model not found — run training first. ({e})"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return RecommendResponse(
        user_id=req.user_id,
        restaurant_id=req.restaurant_id,
        cart_items=rich_cart,
        recommendations=rich_recs,
        pairing_reasons=pairing_reasons,
        meal_analysis=meal_analysis,
        timestamp_used=ts.isoformat(),
    )


@app.post("/analyze-meal", summary="LLM-powered meal completeness analysis")
def analyze_meal(req: MealAnalysisRequest):
    """Uses AI to analyze your cart and suggest what's missing for a complete meal."""
    try:
        analysis = _llm.analyze_meal_completeness(req.cart_items, req.cuisine, req.meal_time)
        
        # Also generate contextual boost scores if items provided
        boost_scores = []
        for item in req.cart_items:
            score = _llm.contextual_boost_score(item, req.cart_items, req.cuisine, req.meal_time)
            boost_scores.append({"item": item.get("name", "Unknown"), "contextual_fit": round(score, 2)})
        
        return {
            "analysis": analysis,
            "contextual_scores": boost_scores,
            "ai_model": "LLM Meal Reasoner v1.0",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/recommend/quick", summary="Quick GET-based recommendation (for browser testing)")
def recommend_quick(
    user_id: int = 1,
    restaurant_id: int = 1,
    cart: str = "",
    top_k: int = 8,
):
    ts = datetime.utcnow()
    
    cart_ids = []
    if cart:
        try:
            cart_ids = [int(x.strip()) for x in cart.split(",") if x.strip()]
        except ValueError:
            raise HTTPException(status_code=400, detail="cart parameter must be comma-separated integers")

    try:
        recs = _recommend(user_id, restaurant_id, cart_ids, ts, top_k=top_k)
        
        items_df = _get_items()
        
        def _enrich_dict(ids):
            res = []
            for iid in ids:
                row = items_df[items_df["item_id"] == iid]
                if not row.empty:
                    r = row.iloc[0]
                    res.append({
                        "item_id": iid,
                        "name": r.get("name", "Unknown"),
                        "category": r.get("category", "?"),
                        "price": float(r.get("price", 0.0)),
                        "is_veg": int(r.get("is_veg", 0))
                    })
                else:
                    res.append({"item_id": iid, "name": "Unknown", "category": "?", "price": 0.0, "is_veg": 0})
            return res
            
        rich_recs = _enrich_dict(recs)
        rich_cart = _enrich_dict(cart_ids)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
        
    return {
        "user_id": user_id,
        "restaurant_id": restaurant_id,
        "cart_items": rich_cart,
        "recommendations": rich_recs, 
        "timestamp": ts.isoformat()
    }
