# AI Shopping Agent: Intelligent Footwear Recommendation (CIA-2)
Free, offline, no API keys. Data: Myntra India footwear listings from a Kaggle dataset, May-2023 snapshot.

## Run (Windows PowerShell)
    python -m venv .venv; .\.venv\Scripts\Activate.ps1
    pip install -r requirements.txt
    python backend/database.py            # builds data/footwear.db from data/footwear_clean.csv
    cd backend; uvicorn main:app --reload
    # API: http://localhost:8000/api/health   |  docs: http://localhost:8000/docs
    python backend/evaluation.py          # 34-query evaluation (constraint violation rate must be 0)
    pytest -q

## AI Processing Simulator (animated)
Open the AI Processing page, pick a Demo and press Run Full AI Simulation. Every stage animates the REAL data of that request: words become tokens and fill requirement slots, constraints lock, a product grid shows retrieval and hard filtering (green valid, red rejected, with reasons and real product photos), score bars grow per component, and the explanation streams word by word beside the database facts it was built from.
Controls: Previous / Next / Play / Pause / Replay stage / Restart, speed 0.5x to 4x (also scales the animations), keyboard: left/right arrows, Space.

## Pipeline
Query -> Security -> Domain check -> Intent -> Hard constraints -> Retrieval -> Hard filter -> Ranking -> Explanation.
Hard constraints (type, colour, gender, brand, budget, availability) are never relaxed. If nothing matches: NO EXACT MATCH FOUND.

## Data limitations (documented honestly)
Prices are a May-2023 snapshot. Colour is known for ~66% of products and gender for ~89%; unknown values never satisfy a requested colour/gender.
The dataset has no size or live-stock fields; the app therefore treats records as catalogue listings, not confirmed live inventory. Ratings exist for ~38% of products. Product images and listing links are hosted/owned by Myntra. Use this dataset only in accordance with the dataset/platform terms; this project is intended as an academic, non-commercial demo.

## Test checklist (open http://localhost:8000)
1. Shop: click each demo chip. Queries 1-6 show products, 7 shows NO EXACT MATCH FOUND, "laptop" shows OUTSIDE CURRENT CATALOGUE.
2. AI Processing: pick a demo, press "Run full simulation", open "Hard Filter" to see the "Why was this product rejected?" list.
3. Security: press each attack button, each must show BLOCKED (or INVALID for oversized input).
4. About: the evaluation must show 0% constraint violation rate.
5. Terminal: `python backend/evaluation.py` and `pytest -q`.
