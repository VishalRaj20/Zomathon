# Zomathon — Context-Aware Cart Super Add-On (CSAO) Recommendation System

> Intelligent add-on recommendation engine that suggests complementary food items based on cart composition, contextual signals, and user preferences. Built for the Zomathon hackathon.

---

## 🚀 Live Demos
- **Frontend (React)**: [https://zomathon-nine.vercel.app](https://zomathon-nine.vercel.app)
- **Node.js API (Render)**: [https://zomathon-backend-tdn3.onrender.com](https://zomathon-backend-tdn3.onrender.com)
- **Python ML API (Render)**: [https://zomathon-ml.onrender.com](https://zomathon-ml.onrender.com)

---

## Project Structure

```
zomathon/
├── data/
│   ├── raw/                   ← users, restaurants, items, orders, order_items CSVs
│   └── processed/
│       ├── train_features.csv ← ML-ready dataset (142K rows, 38 features)
│       └── pipeline_report.json
├── models/                    ← saved model + evaluation reports
│   ├── baseline_model.pkl
│   ├── evaluation_report.json     ← AUC, P@K, R@K, NDCG, segment analysis
│   ├── baseline_comparison_report.json ← model vs baselines
│   ├── latency_report.json        ← p50/p95/p99 latency benchmarks
│   ├── business_impact_report.json
│   └── tuning_report.json         ← Optuna hyperparameter tuning results
├── src/
│   ├── models/
│   │   ├── train_baseline.py  ← Model training with full evaluation
│   │   └── tune_model.py      ← Optuna hyperparameter tuning
│   ├── inference/
│   │   ├── recommender.py     ← Real-time inference engine with re-ranking
│   │   └── llm_recommender.py ← LLM-powered AI Edge (meal analysis, pairing)
│   └── evaluation/
│       ├── benchmark_latency.py    ← Latency benchmarking (8 scenarios)
│       ├── business_impact.py      ← AOV lift & business projections
│       └── baseline_comparison.py  ← Model vs heuristic baselines
├── api/
│   └── main.py                ← FastAPI v2.0 (ML + LLM endpoints)
├── frontend/                  ← React web app
├── backend/                   ← Node.js Express API
├── build_features.py          ← Feature engineering pipeline (576 lines)
├── generate_dataset.py        ← Synthetic data generation (791 lines)
└── requirements.txt
```

---

## System Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                        CLIENT (React)                            │
│  Cart UI → "Add" button → CartContext.jsx → /api/cart/add        │
│  ← Recommendations Rail ← CartContext.jsx ← /api/recommendations │
└───────────────────────────────┬──────────────────────────────────┘
                                │ HTTP
┌───────────────────────────────▼──────────────────────────────────┐
│                   NODE.JS BACKEND (Express)                      │
│  authMiddleware → cartRoutes → recommendRoutes                   │
│  MongoDB (User.cart[]) ← JWT Auth ← axios proxy to ML service   │
└───────────────────────────────┬──────────────────────────────────┘
                                │ HTTP POST /recommend
┌───────────────────────────────▼──────────────────────────────────┐
│                   ML SERVICE (FastAPI / uvicorn)                  │
│  api/main.py → src/inference/recommender.py                      │
│  1. Load user, restaurant, items from CSV (cached)               │
│  2. Build 38 features (user + restaurant + cart + item + context) │
│  3. Score all candidates with LightGBM                           │
│  4. Re-rank with business rules (cuisine, complementarity)       │
│  5. Return top-K item_ids with metadata                          │
└──────────────────────────────────────────────────────────────────┘
```

### Data Flow for Each Recommendation Request

1. **User adds item to cart** → Frontend calls `/api/cart/add`
2. **Backend updates MongoDB** → Atomic `$push` update via `User.findByIdAndUpdate`
3. **Frontend fetches recommendations** → Backend proxies to ML service at `/recommend`
4. **ML service builds features** → User, restaurant, cart, item, temporal context
5. **LightGBM scores all candidates** → Probability of add-on acceptance
6. **Re-ranking layer applies business rules** → Cross-cuisine penalty, complementary pairing, category diversity
7. **Top-K results returned** → Enriched with item metadata (name, price, category)

---

## Quick Start (3 steps)

### Step 0 — Install dependencies
```bash
pip install -r requirements.txt
pip install optuna  # for hyperparameter tuning
```

### Step 1 — Train the model
```bash
python src/models/train_baseline.py
```

### Step 2 — Start the API server
```bash
uvicorn api.main:app --reload --port 8000
```

### Step 3 — Test
```bash
curl -X POST http://localhost:8000/recommend \
  -H "Content-Type: application/json" \
  -d '{"user_id": 1, "restaurant_id": 1, "cart_items": [101, 205], "top_k": 8}'
```

---

## Problem Formulation

### Mathematical Framing

We frame CSAO recommendation as a **pointwise learning-to-rank** problem:

> Given a context tuple **(user, restaurant, cart_state, timestamp)** and a set of candidate items **C**, learn a scoring function **f(x) → [0, 1]** that predicts the probability of a user accepting each candidate as an add-on.

**Training Signal:** Binary label — 1 if the item was actually added to the cart at this step, 0 otherwise (with 4× negative sampling).

**Ranking:** At inference time, all candidates are scored independently, then sorted by **f(x)** descending. A re-ranking layer applies business rules (diversity, complementary pairing, cuisine compatibility) before returning top-K.

### Why Pointwise Ranking + Re-Ranking?

1. **Scalability** — Pointwise scoring parallelizes across candidates; no expensive pairwise comparisons
2. **Feature Richness** — 38 cross-features capture user×item, cart×item, and time×item interactions
3. **Interpretability** — Feature importances directly explain decisions to stakeholders
4. **Flexibility** — The re-ranking layer allows injecting business rules without retraining

### Handling Key Constraints

| Challenge | Solution |
|---|---|
| **Cold Start (new users)** | Popularity-weighted fallback with demographic priors |
| **Cold Start (new restaurants)** | Global item pool augmentation for small menus |
| **Incomplete Meal Patterns** | `cart_completion_ratio`, `item_category_missing_in_cart`, `last_added_category` features + complementary pairing rules |
| **Sparse User Histories** | `user_order_freq`, `user_veg_ratio`, `user_budget_segment` aggregated from order history |
| **Diversity** | Category diversity penalty in re-ranking; max 3 items per category |
| **Cross-Cuisine Incompatibility** | Macro-cuisine grouping with semantic name overrides |

---

## The AI Edge — LLM-Powered Meal Analysis

Beyond the core ML model, we integrate an **LLM-powered reasoning layer** that provides:

### 1. Meal Completeness Reasoning (`/analyze-meal` endpoint)
Analyzes cart composition against culturally-aware meal templates (Indian, Western, Asian) and identifies:
- Missing categories (main course, side, drink, dessert)
- Completeness score (0–100%)
- Natural-language suggestions: *"Your cart needs a main course! Try a curry or biryani to complete your meal."*

### 2. Pairing Explanations (in `/recommend` response)
Each recommendation now includes a human-readable reason:
- *"Classic pairing! Butter Chicken goes perfectly with Garlic Naan."*
- *"Complete your meal with Lassi — a refreshing addition!"*

### 3. Contextual Boost Scores
LLM scores each candidate [0.0–1.0] for contextual fit, considering:
- Meal-time appropriateness (avoid biryani at breakfast)
- Category completeness (boost missing categories)
- Cultural pairing knowledge (naan→curry, biryani→raita)

```bash
# Test the LLM meal analysis endpoint
curl -X POST http://localhost:8000/analyze-meal \
  -H "Content-Type: application/json" \
  -d '{"cart_items": [{"name": "Garlic Naan", "category": "side", "price": 60}], "cuisine": "North Indian", "meal_time": "dinner"}'
```

---

## Baseline Comparison (Model vs Heuristics)

| Strategy | AUC | P@8 | R@8 | NDCG@8 |
|---|---|---|---|---|
| Random | 0.5041 | 0.176 | 0.746 | 0.471 |
| Popularity-Only | 0.4631 | 0.167 | 0.716 | 0.464 |
| Price-Weighted Pop | 0.4596 | 0.166 | 0.714 | 0.457 |
| Category-Aware Heuristic | 0.4645 | 0.166 | 0.712 | 0.456 |
| **LightGBM (Ours)** | **1.0000** | **0.287** | **0.997** | **1.000** |

**Model Lift:** +98–119% AUC over all baselines, +112–119% NDCG improvement.

---

## A/B Testing Design

### Traffic Allocation
```
Control (A):  50% — No CSAO rail (or popularity-based recommendations)
Treatment (B): 50% — LightGBM + LLM-powered CSAO rail
```

### Primary Success Metrics
| Metric | Definition | Target |
|---|---|---|
| **AOV Lift** | (Avg order value Treatment − Control) / Control | > +5% |
| **CSAO Acceptance Rate** | # add-ons accepted / # recommendations shown | > 15% |
| **Cart-to-Order (C2O)** | # completed orders / # carts with items | No decrease |
| **Items per Order** | Avg items in completed orders | > +0.3 |

### Guardrail Metrics (must not degrade)
| Metric | Threshold |
|---|---|
| Cart abandonment rate | < +1pp vs control |
| Time to checkout | < +10s vs control |
| Customer satisfaction (NPS) | No significant drop |
| App crash rate | < 0.1% |
| p95 latency (recommendations) | < 300ms |

### Statistical Framework
- **Test duration:** Minimum 2 weeks for seasonal stability
- **Significance:** p < 0.05 with Bonferroni correction for multiple comparisons
- **Power:** 80% to detect ≥3% AOV lift
- **Stratification:** By city, meal-time, user-segment to control confounders
- **Ramp-up:** 5% → 20% → 50% traffic over 3 days to catch early regressions

### Monitoring
- Real-time dashboard tracking all primary and guardrail metrics
- Automated alerts if any guardrail breaches threshold
- Daily segment-level breakdowns (city, cuisine, meal-time)

---

## Model Details


### Features (38 total)

| Category | Features | Count |
|---|---|---|
| **User** | avg_spend, order_frequency, veg_ratio, budget_segment | 4 |
| **Restaurant** | price_range, rating, cuisine_id, is_chain, avg_prep_time | 5 |
| **Cart State** | item_count, total_price, has_drink/dessert/starter/main, veg/nonveg counts, unique_categories, avg_item_price | 10 |
| **Item** | price, is_veg, category, popularity, price_at_order | 5 |
| **Context** | hour_of_day, day_of_week, is_weekend, meal_time | 4 |
| **Cross** | category_missing_in_cart, price_vs_user/cart_avg, veg_alignment, cart_completion, cuisine_affinity, last_added_category, complements_cart, cuisine_matches_cart | 10 |

### Top 10 Feature Importances (LightGBM)

| Rank | Feature | Importance |
|---|---|---|
| 1 | item_price_at_order | 24,395 |
| 2 | item_price | 21,199 |
| 3 | item_popularity | 14,680 |
| 4 | rest_rating | 8,534 |
| 5 | item_price_vs_cart_avg | 4,768 |
| 6 | user_order_freq | 4,727 |
| 7 | rest_cuisine_id | 4,448 |
| 8 | user_veg_ratio | 3,968 |
| 9 | rest_avg_prep_time | 3,295 |
| 10 | user_avg_spend | 3,281 |

### Re-Ranking Business Rules

The ML model score is post-processed by a rule-based re-ranker that enforces:

1. **Macro-Cuisine Compatibility** — Items must match the cart's food culture (Indian, Western, Asian)
2. **Complementary Pairing** — Bread→Curry, Biryani→Raita, Main→Drink
3. **Category Diversity** — Penalize duplicate categories, ensure drink/side representation
4. **Cold Start Fallback** — Popularity-weighted scoring for new users
5. **Night-Time Guarantee** — Main courses prioritized for dinner/late-night empty carts
6. **Semantic Name Override** — Correct cuisine classification for misattributed items

---

## Evaluation Results

### Model Performance Metrics

| Metric | Validation | Test (Holdout) |
|---|---|---|
| **AUC** | 0.9999 | 0.9999 |
| **Precision@8** | 0.2864 | 0.2873 |
| **Recall@8** | 0.9973 | 0.9973 |
| **NDCG@8** | 1.0000 | 1.0000 |

### Segment-Level Performance

#### By Meal Time
| Segment | AUC | P@8 | R@8 | Samples |
|---|---|---|---|---|
| Breakfast | 0.999 | 0.299 | 0.997 | 2,075 |
| Lunch | 1.000 | 0.280 | 0.997 | 6,945 |
| Evening Snack | 1.000 | 0.284 | 0.998 | 3,805 |
| Dinner | 0.999 | 0.294 | 0.997 | 10,850 |
| Late Night | 1.000 | 0.274 | 0.998 | 4,055 |

#### By Cart Size
| Segment | AUC | P@8 | R@8 | Samples |
|---|---|---|---|---|
| Empty | 1.000 | 0.125 | 1.000 | 11,875 |
| Small (1-2) | 1.000 | 0.192 | 1.000 | 11,970 |
| Medium (3-4) | 1.000 | 0.171 | 1.000 | 2,950 |
| Large (5+) | 1.000 | 0.486 | 0.912 | 935 |

### Latency Benchmark (SLA: < 300ms)

| Scenario | p50 | p95 | p99 | Status |
|---|---|---|---|---|
| Empty Cart (global) | 183ms | 194ms | 194ms | ✓ PASS |
| Single Item Cart | 152ms | 212ms | 212ms | ✓ PASS |
| Small Cart (3 items) | 159ms | 185ms | 185ms | ✓ PASS |
| Full Cart (5+ items) | 163ms | 219ms | 219ms | ✓ PASS |
| Lunch Time | 156ms | 173ms | 173ms | ✓ PASS |
| Breakfast Time | 158ms | 177ms | 177ms | ✓ PASS |
| Restaurant-specific | 152ms | 184ms | 184ms | ✓ PASS |
| Cold Start User | 182ms | 220ms | 220ms | ✓ PASS |

**Overall: ALL PASS ✓ | Avg p95 = 195.5ms**

---

## Business Impact Analysis

### Projected Metrics

| Metric | Value |
|---|---|
| Baseline AOV | ₹76.01 |
| **Projected AOV** | **₹99.26 (+30.6%)** |
| Acceptance Rate | 22% |
| CSAO Rail Show Rate | 85% |
| CSAO Attach Rate | 18.7% |
| Avg Add-on Price | ₹124.33 |
| C2O Lift | +3pp (72% → 75%) |
| Projected Add-on Revenue | ₹17.4L |

---

## Scalability Considerations

1. **Model Caching** — Model loaded once at startup (`_model_cache` singleton), shared across requests
2. **Data Caching** — CSV data loaded lazily and cached in memory for fast lookups
3. **Candidate Pool Limiting** — Global recommendations limited to top 250–500 items to avoid full-table scans
4. **Latency** — All scenarios under 220ms p99, well within 300ms SLA
5. **Horizontal Scaling** — FastAPI + uvicorn supports multiple workers; stateless design allows load balancing
6. **Feature Computation** — All 38 features computed in-process using NumPy/Pandas vectorization

### Trade-offs & Limitations

- **Synthetic Data** — Model trained on generated data; real-world performance may differ
- **Single-Machine CSV Storage** — Production should migrate to Redis/DynamoDB for item/user lookups
- **No Online Learning** — Model is retrained offline; real-time feedback loop would improve accuracy
- **Cold Start** — New restaurants with < 5 menu items fall back to global popularity

---

## Hyperparameter Tuning

Run Optuna-based tuning (30+ trials):
```bash
python src/models/tune_model.py --n-trials 30
```

Search space: `n_estimators`, `learning_rate`, `num_leaves`, `min_child_samples`, `subsample`, `colsample_bytree`, `reg_alpha`, `reg_lambda`, `max_depth`

Objective: 0.6 × AUC + 0.4 × Precision@8

---

## Troubleshooting

| Error | Fix |
|---|---|
| `ModuleNotFoundError: lightgbm` | `pip install lightgbm` or script auto-falls back to LogReg |
| `FileNotFoundError: models/baseline_model.pkl` | Run Step 1 first |
| `FileNotFoundError: data/raw/items.csv` | Make sure raw CSVs are in `data/raw/` |
| `ModuleNotFoundError: optuna` | `pip install optuna` |
| `KeyError: split` | Fine — script falls back to GroupShuffleSplit automatically |