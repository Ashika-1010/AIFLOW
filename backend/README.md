# AIFlow Backend

Real AI routing middleware with per-request energy accounting.

## Quick Start

```bash
# From the backend/ directory

# 1. Create & activate a virtual environment
python -m venv .venv
.venv\Scripts\activate        # Windows PowerShell
# source .venv/bin/activate   # macOS/Linux

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
copy .env.example .env        # Windows
# cp .env.example .env        # macOS/Linux
# Edit .env — at minimum, leave defaults. Add GROQ_API_KEY for live model calls.

# 4. Generate training data
python scripts/generate_training_data.py

# 5. Train the complexity classifier
python scripts/train_classifier.py

# 6. Seed the demo database
python scripts/seed_demo.py

# 7. Start the server
uvicorn main:app --reload --port 8000
```

Then in the Frontend/ directory:
```bash
npm install
npm run dev          # runs at http://localhost:5173
```

## Architecture

```
POST /v1/complete → 6-stage pipeline:
  Stage 1: Deterministic gate   (arithmetic, units, dates — sympy/pint/dateutil)
  Stage 2: Exact cache          (SHA-256, 24h TTL)
  Stage 3: Semantic cache       (MiniLM cosine ≥ 0.95, or ≥ 0.90 for stable factual)
  Stage 4: Retrieval            (local corpus, cosine ≥ 0.55)
  Stage 5: Complexity classifier (LogisticRegression on MiniLM + 5 handcrafted features)
  Stage 6: Tier execution + verification + optional escalation
```

## Energy Methodology

Coefficients from energy_profiles.json (aiflow-em-1.0):
- **Small model (8B)**: 0.09–0.24 Wh / 1k output tokens
- **Large model (70B)**: 0.28–1.10 Wh / 1k output tokens
- **PUE**: 1.09–1.25 (central 1.15)

Three bands (low / central / high) are computed independently using actual coefficients.

Sources:
- ML.ENERGY Benchmark v3.0 (2025)
- Google, "Measuring the environmental impact of AI inference" (Aug 2025)
- arXiv 2407.16893 — per-token energy scaling

## Training Data Note

`data/training_prompts.json` contains ~360 synthetically authored prompts across
6 categories (arithmetic, stable factual, short generative, reasoning/complex,
long-document, ambiguous). No real user data is included. Labels were assigned by
category heuristic (see `scripts/generate_training_data.py`).

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `GROQ_API_KEY` | No | Enables live Groq API calls (llama-3.1-8b, llama-3.3-70b) |
| `GEMINI_API_KEY` | No | Reserved for future Gemini tier |
| `ELECTRICITY_MAPS_API_KEY` | No | Live carbon intensity (falls back to static table) |
| `DEV_MODE` | No | Set `false` in production to restrict CORS |
| `DEBUG_FORCE_ESCALATE` | No | Set `1` to force escalation on all small-model attempts |

## Acceptance Test

```bash
# Arithmetic
curl -s -X POST http://localhost:8000/v1/complete \
  -H "Content-Type: application/json" \
  -d '{"query":"What is 27 × 43?","qualityFloor":0.6,"region":"IN"}' \
  | python -m json.tool | grep -E '"pathway"|"response"|"energyWh"'

# Should return: "pathway": "deterministic", "response": "1161", energyWh.central ~1e-6

# Health
curl http://localhost:8000/v1/health
# {"status":"ok"}
```
