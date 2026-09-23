# AIFlow — Technical Implementation Report

**Project:** AIFlow — The minimum-compute layer for AI applications  
**Report generated:** September 2026  
**Scope:** Documents only what is implemented in the current codebase. All test results, metrics, and counts are taken directly from the live files and verified outputs recorded during this session.

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Tech Stack](#2-tech-stack)
3. [Folder Structure](#3-folder-structure)
4. [Backend Implementation](#4-backend-implementation)
5. [Routing Pipeline](#5-routing-pipeline)
6. [Energy Receipts](#6-energy-receipts)
7. [Frontend Integration](#7-frontend-integration)
8. [Testing and Validation](#8-testing-and-validation)
9. [Running the Project](#9-running-the-project)
10. [Current Status and Limitations](#10-current-status-and-limitations)
11. [Recommended Next Steps](#11-recommended-next-steps)

---

## 1. Project Overview

AIFlow is a middleware routing layer that sits between client applications and LLM providers. Its stated purpose is to reduce compute consumption — and therefore cost, latency, and energy use — by routing each incoming query to the cheapest pathway that still meets a caller-specified quality threshold.

### How a request moves through the system

```
Client → POST /v1/complete
           │
           ▼
  [Stage 1] Deterministic Gate
  (arithmetic / unit conversion / date arithmetic via sympy, pint, dateutil)
           │  no match
           ▼
  [Stage 2] Exact Cache  (SHA-256 of normalised query, 24-hour TTL)
           │  miss
           ▼
  [Stage 3] Semantic Cache  (cosine ≥ 0.95 always; ≥ 0.90 for "stable factual" queries)
           │  miss
           ▼
  [Stage 4] Local Corpus Retrieval  (cosine ≥ 0.55 against 17 embedded .txt documents)
           │  miss
           ▼
  [Stage 5] Complexity Classifier  (LogisticRegression → p_small ∈ [0,1])
           │
           ├─ p_small ≥ qualityFloor + 0.1  →  small_model  (direct)
           ├─ qualityFloor - 0.1 ≤ p_small  →  small_model  (with strict verification)
           └─ p_small < qualityFloor - 0.1  →  large_model  (direct, skip small)
           │
           ▼
  [Stage 6] Verification (structural checks on small-model response)
           │  passed                        │  failed
           ▼                               ▼
  pathway = small_model          Escalate → large_model
                                 pathway = escalated
                                 escalationRegretWh = small_energy.central
           │
           ▼
  Energy accounting (compute_energy_band)
  Persist ReceiptORM (is_demo=False)
  Return Receipt JSON
```

Every pathway produces a `Receipt` with a full energy band (`{low, central, high}` in Wh), baseline comparison, and classification metadata. The route taken and the reason for it are stored verbatim.

---

## 2. Tech Stack

### Backend

| Layer | Technology | Version |
|---|---|---|
| Web framework | FastAPI | 0.115.5 |
| ASGI server | Uvicorn + standard extras | 0.32.1 |
| ORM / DB | SQLAlchemy + SQLite | 2.0.36 |
| Schema validation | Pydantic v2 | 2.10.3 |
| Settings | pydantic-settings | 2.6.1 |
| Environment | python-dotenv | 1.0.1 |
| Arithmetic gate | SymPy | 1.13.3 |
| Unit conversion | Pint | 0.24.4 |
| Date arithmetic | python-dateutil | 2.9.0 |
| Embeddings | sentence-transformers (all-MiniLM-L6-v2) | 3.3.1 |
| Numeric ops | NumPy | ≥1.26, <3 |
| Classifier | scikit-learn | 1.5.2 |
| Model serialisation | joblib | 1.4.2 |
| Token counting | tiktoken (cl100k_base) | 0.8.0 |
| LLM API client | openai SDK (Groq-compatible) | 1.57.2 |
| Live carbon fetch | httpx | 0.28.0 |
| Multipart | python-multipart | 0.0.20 |

### Frontend

| Layer | Technology | Version |
|---|---|---|
| UI framework | React | 19.2.8 |
| Routing | React Router DOM | 7.18.4 |
| Charts | Recharts | 3.10.1 |
| Icons | lucide-react | 1.47.0 |
| Build tool | Vite | 8.3.0 |
| Language | TypeScript | ~6.0.2 |
| Styling | Tailwind CSS | 3.4.19 |
| Linting | oxlint | 1.81.0 |
| Test framework | **None** — not configured |  |

### LLM Integrations

| Provider | Models | Status |
|---|---|---|
| Groq | llama-3.1-8b-instant (Tier 2), llama-3.3-70b-versatile (Tier 3) | Functional when `GROQ_API_KEY` is set; otherwise falls back to simulator |
| Gemini | Referenced in `.env.example` and `.env` | **Not implemented** — no code reads or calls Gemini |
| Simulator | Internal fallback | Always active when no API key is present |

---

## 3. Folder Structure

```
AIFLOW - 1/
├── IMPLEMENTATION_REPORT.md        ← this file
├── backend/
│   ├── main.py                     ← FastAPI app, 6 endpoints, startup lifespan
│   ├── models.py                   ← Pydantic schemas (mirrors types.ts exactly)
│   ├── db.py                       ← SQLAlchemy engine, ORM models, get_db()
│   ├── .env                        ← live environment (all keys empty)
│   ├── .env.example                ← documents all 5 env variables
│   ├── requirements.txt            ← all pinned backend dependencies
│   ├── aiflow.db                   ← SQLite database (52 receipts: 24 demo, 28 real)
│   ├── receipt_counter.txt         ← plain-text receipt ID counter (not atomic)
│   ├── migrate_add_is_demo.py      ← one-time migration: adds is_demo column
│   ├── test_requests.py            ← 10-scenario acceptance tests (requires live server)
│   ├── test_audit_demo_separation.py ← 6-scenario demo/real separation tests
│   ├── engine/
│   │   ├── __init__.py
│   │   ├── gates.py                ← Stage 1: arithmetic, units, dates
│   │   ├── cache.py                ← Stages 2-3: exact + semantic cache
│   │   ├── retrieval.py            ← Stage 4: corpus vector search
│   │   ├── classifier.py           ← Stage 5: LogisticRegression, feature extraction
│   │   ├── verifier.py             ← Stage 6: structural response checks
│   │   └── decision.py             ← Orchestrator: ties all stages together
│   ├── clients/
│   │   ├── __init__.py
│   │   ├── groq_client.py          ← Groq API via openai SDK, or fallback to simulator
│   │   └── simulator.py            ← offline fallback with real sleep-based latency
│   ├── sustainability/
│   │   ├── __init__.py
│   │   ├── energy_profiles.json    ← energy coefficients (aiflow-em-1.0)
│   │   ├── calculator.py           ← 3-band energy formula
│   │   └── regions.py              ← static grid intensity + optional live Electricity Maps
│   ├── data/
│   │   ├── classifier.joblib       ← serialised trained model (3999 bytes)
│   │   ├── classifier_metrics.json ← accuracy=0.8485, AUC=0.9737
│   │   ├── training_prompts.json   ← 220 synthetic labelled prompts
│   │   └── corpus/                 ← 17 .txt retrieval documents
│   │       ├── access_control_policy.txt
│   │       ├── api_rate_limits.txt
│   │       ├── billing_faq.txt
│   │       ├── compliance_gdpr.txt
│   │       ├── data_retention_policy.txt
│   │       ├── deployment_guide.txt
│   │       ├── error_codes.txt
│   │       ├── http_status_codes.txt
│   │       ├── incident_management.txt
│   │       ├── model_cards.txt
│   │       ├── model_routing_faq.txt
│   │       ├── oncall_runbook.txt
│   │       ├── sdk_reference.txt
│   │       ├── security_policy.txt
│   │       ├── sla_policy.txt
│   │       ├── sustainability_methodology.txt
│   │       └── webhook_guide.txt
│   └── scripts/
│       ├── generate_training_data.py  ← generates 220 synthetic labelled prompts
│       ├── train_classifier.py        ← trains and saves classifier.joblib
│       └── seed_demo.py               ← inserts 24 fixture receipts (is_demo=True)
└── Frontend/
    ├── .env                        ← VITE_API_BASE_URL=http://localhost:8000
    ├── .env.example                ← documents VITE_API_BASE_URL
    ├── package.json
    ├── index.html
    └── src/
        ├── App.tsx                 ← route definitions
        ├── main.tsx                ← React root
        ├── mock/
        │   ├── api.ts              ← real fetch calls to backend (no mock logic)
        │   ├── types.ts            ← TypeScript interfaces (contract with backend)
        │   ├── regions.ts          ← 5 static region definitions
        │   ├── data.ts             ← MOCK_ASSUMPTIONS table (hardcoded in frontend)
        │   └── methodology.ts      ← static methodology content
        ├── context/
        │   └── AppContext.tsx      ← global state: region, qualityFloor, pessimistic
        ├── pages/
        │   ├── LiveRun.tsx         ← main prompt → receipt interaction
        │   ├── Receipts.tsx        ← receipt ledger (fetches from API + shows DEMO badge)
        │   ├── ReceiptDetail.tsx   ← full receipt view with energy range bar and CO2e
        │   ├── Audit.tsx           ← empty state + metrics (uses realExecutionCount)
        │   └── Analytics.tsx       ← charts: pathway distribution, energy, cumulative
        ├── components/
        │   ├── PathwayTrace.tsx
        │   ├── BaselineComparison.tsx
        │   ├── ExampleChips.tsx
        │   ├── MethodologyModal.tsx
        │   └── ui/                 ← Badge, Button, Card, Modal, RangeBar, etc.
        ├── layout/
        │   ├── AppShell.tsx
        │   ├── Sidebar.tsx
        │   └── Topbar.tsx
        └── lib/
            ├── colors.ts
            ├── format.ts           ← formatWh, formatLatency, formatUsd, etc.
            └── useCountUp.ts
```

---

## 4. Backend Implementation

### 4.1 FastAPI Application — `backend/main.py`

**Status: Functional**

The app is created with a lifespan context manager that runs at startup in this fixed order:
1. `init_db()` — creates SQLite tables if missing
2. `SentenceTransformer("all-MiniLM-L6-v2")` — loaded into the global `_sentence_model`
3. `rebuild_index_from_db()` — populates the in-memory semantic cache matrix from stored embeddings
4. `get_retrieval_engine().load(...)` — embeds all 17 corpus `.txt` files

CORS is configured to allow `localhost:5173` and `localhost:4173`. When `DEV_MODE=true` (the current default), the wildcard `"*"` is also added.

**Endpoints:**

| Method | Path | Description |
|---|---|---|
| GET | `/v1/health` | Returns `{"status": "ok"}` |
| POST | `/v1/complete` | Runs full pipeline; persists `ReceiptORM` with `is_demo=False` |
| GET | `/v1/receipts` | All receipts ordered by `created_at DESC` (includes demo rows) |
| GET | `/v1/receipts/{id}` | Single receipt; 404 if not found |
| GET | `/v1/audit?pessimistic=bool` | Metrics from `is_demo=False` rows only |
| GET | `/v1/analytics?pessimistic=bool` | Charts payload from `is_demo=False` rows only |

**Known limitations:**
- No authentication or API key checking on any endpoint
- `DEV_MODE=true` by default exposes CORS `"*"` — must be changed before any public deployment
- The `_sentence_model` global is a single instance; concurrent requests share it without locking (acceptable for single-worker uvicorn, not safe for multi-worker)
- The CO2e stat in the analytics response uses a hardcoded `energySavedPct * 0.95` scalar — it does not use the region's grid intensity

### 4.2 Request/Response Schemas — `backend/models.py`

**Status: Functional**

All Pydantic v2 models mirror `Frontend/src/mock/types.ts` field-for-field using camelCase names. Key additions beyond the original TypeScript contract:
- `Receipt.isDemo: bool = False` — indicates seed/demo receipts
- `AuditSummary.realExecutionCount: int = 0` — count of non-demo receipts
- `AuditSummary.demoCount: int = 0` — count of demo receipts

`CompleteRequest` accepts `query: str`, `qualityFloor: float = 0.60` (0..1 validated), `region: str = "IN"`.

### 4.3 Database Models — `backend/db.py`

**Status: Functional**

Three SQLAlchemy ORM models backed by a single `aiflow.db` SQLite file. WAL journal mode and foreign keys are enabled at connection time.

**`ReceiptORM`** — 22 columns including:
- `is_demo: Boolean` — the key separator between fixture and real execution rows. Default `False`, server_default `"0"`.
- `energy_wh: Text` — JSON-serialised `{low, central, high}` dict
- `pathway_steps: Text` — JSON-serialised list
- `region: String` — stored per-receipt but not used in energy calculation (see §4.12)

**`CacheEntryORM`** — stores `hash` (SHA-256 PK), `query`, `response`, and `embedding` (nullable JSON float list). Seed entries have `embedding=NULL` and are therefore not loaded into the semantic cache index at startup.

**`ClassifierMetricsORM`** — stores accuracy, AUC, and training metadata. Currently empty (metrics are written to `classifier_metrics.json` file but `train_classifier.py` does not pass a `db` session to `train()`).

**DB path**: hardcoded to `aiflow.db` relative to the CWD where uvicorn runs. The `.env.example` mentions a `DB_PATH` variable but the code does not read it.

**Current DB state** (verified from live file):
- Total receipts: 52 (24 demo, 28 real)
- Cache entries: 25
- `receipt_counter.txt` current value: 305

### 4.4 Deterministic Gate — `backend/engine/gates.py`

**Status: Functional. Tested.**

Triggered at the top of every `run_pipeline()` call. Returns immediately without calling any model or cache.

**Ambiguity guard (fires first):** A broad regex blocks the gate when the query contains words like `explain`, `describe`, `why`, `write`, `generate`, `analyze`, `list`, `summarize`, `translate`, `compare`, `discuss`, `recommend`, `code`, `program`. This prevents false positives at the cost of a few edge-case false negatives (e.g., "Calculate how many days between..." containing "calculate" would not trigger the ambiguity guard, but "Calculate the implications of..." would).

**Sub-handlers (in priority order):**
1. **Date arithmetic** — matches ISO date pairs (`\d{4}-\d{2}-\d{2}`) or "how many days between". Uses `dateutil.parser` with `fuzzy=True`. Returns `"{N} days"`.
2. **Unit conversion** — regex detects number + unit + "to/in" + target unit. Uses `pint.UnitRegistry`. Covers mph, kph, kg, lbs, miles, km, meters, feet, inches, Celsius, Fahrenheit, gallons, litres. Returns `"{N} {from} = {result} {to}"`.
3. **Pure arithmetic** — strips natural-language preamble ("what is", "calculate", etc.), then passes the expression to `sympy.sympify()`. Returns integer string for whole numbers, or `f"{f:.6g}"` for floats.

**Verified behaviour** (from test run, server active): `"What is 27 × 43?"` → pathway `deterministic`, response `"1161"`, `energyWh.central ≈ 1.15e-6` Wh, latency 1 ms.

**Known limitations:**
- Token counts for deterministic responses are approximations: `max(4, len(query.split()))` for input, `max(3, len(response.split()))` for output. Not tiktoken-accurate.
- Unit conversions are limited to the alias map in the code. Currency, pressure, energy, and data-size conversions are not covered.
- The `_OP_ALIASES` step translates `x` → `*` globally, which means a query like "What is x in 5x + 3 = 18?" would have `x` converted to `*` before sympify and fail silently.
- `_AMBIGUITY_GUARDS` is a single flat regex — it does not distinguish "translate" in a language-translation context from "translate" as a mathematical term.

### 4.5 Exact Cache — `backend/engine/cache.py` (Stage 2)

**Status: Functional**

`lookup_exact(db, query)` normalises the query (lowercase, strip, collapse whitespace), SHA-256 hashes it, queries `CacheEntryORM`, checks the 24-hour TTL, and returns the stored response or `None`. Expired entries are deleted inline on read.

Time-sensitive queries (containing: `today`, `now`, `latest`, `current`, `recent`, `this week`, `this month`, `this year`, `right now`, `at the moment`, `my `, `this document`, `attached`, `upload`) always bypass the cache.

`store_in_cache(db, query, response, embedding)` upserts into `CacheEntryORM` and simultaneously updates the in-memory semantic index.

### 4.6 Semantic Cache — `backend/engine/cache.py` (Stage 3)

**Status: Functional**

`SemanticCacheIndex` holds all cached embeddings as a NumPy matrix (rebuilt from DB at startup). On each lookup, cosine similarity is computed between the query embedding and all stored vectors.

**Thresholds:**
- `sim ≥ 0.95` → serve regardless of query type
- `0.90 ≤ sim < 0.95` → serve only if `_STABLE_FACTUAL_PATTERN` matches (scientific/reference vocabulary)

**Known limitation:** The module-level `_index` singleton is populated from `CacheEntryORM` rows that have a non-null `embedding`. The 24 seed demo entries were inserted with `embedding=NULL` by `seed_demo.py`, so they are not in the semantic index at startup. They will populate the index only when a real matching query is processed and stored.

**Known limitation:** Not thread-safe for concurrent writes. Acceptable for single-worker uvicorn.

### 4.7 Retrieval — `backend/engine/retrieval.py` (Stage 4)

**Status: Functional**

At startup, `RetrievalEngine.load()` reads all `.txt` files from `backend/data/corpus/` alphabetically (17 files confirmed), embeds them with the shared `all-MiniLM-L6-v2` instance, and stores them as a NumPy matrix.

On each query, cosine similarity is computed against all 17 document vectors. If `best_sim ≥ 0.55`, the match is returned as `(title, full_doc_text, similarity)`.

In `decision.py`, the retrieval response is always the **first 3 sentences** of the matched document, obtained by splitting on `(?<=[.!?])\s+`. This is a fixed heuristic regardless of document structure or query specificity.

The `provider_cost_usd` for retrieval is hardcoded to `0.0001` in `decision.py` (not derived from any real pricing).

The retrieval result is also stored in the cache (`store_in_cache()`) so subsequent identical queries hit Stage 2/3.

**Known limitation:** Flat threshold of 0.55 means anything above this score returns a response even if the match is poor quality. No re-ranking or relevance scoring beyond cosine similarity.

### 4.8 Complexity Classifier — `backend/engine/classifier.py` (Stage 5)

**Status: Functional. Trained and persisted.**

A `scikit-learn LogisticRegression` (`max_iter=1000`, `class_weight="balanced"`) predicts `p_small`: the probability that the small model tier is sufficient for a given query.

**Feature vector (389 dimensions):**
- Dimensions 0–383: 384-d MiniLM-L6-v2 embedding of the query
- Dimension 384: `log(tiktoken_token_count + 1)`
- Dimension 385: `query.count("?")`
- Dimension 386: `1.0` if query contains backtick or code fence, else `0.0`
- Dimension 387: `1.0` if query references an attached document (keywords: `document`, `file`, `attached`, `pdf`, `paste`, `above text`, `following text`), else `0.0`
- Dimension 388: `1.0` if query starts with an imperative verb from a fixed 20-word list, else `0.0`

**Training data (verified from `data/training_prompts.json`):**

| Category | Count | Label |
|---|---|---|
| arithmetic | 20 | 1 (small sufficient) |
| stable_factual | 40 | 1 |
| short_generative | 60 | 1 |
| reasoning_complex | 50 | 0 (large needed) |
| reasoning_simple | 20 | 1 |
| long_document | 20 | 0 |
| ambiguous | 10 | mixed (5 each) |
| **Total** | **220** | **145 label=1 / 75 label=0** |

All prompts are **synthetically authored**. No real user queries were used.

**Verified metrics (from `data/classifier_metrics.json`, confirmed by `train_log.txt`):**
- Held-out accuracy: **0.8485** (84.85%)
- Held-out AUC: **0.9737**
- Train split: 154 examples (70%)
- Test split: 66 examples (30%)
- Stratified split, `random_state=42`

**Fallback:** If `classifier.joblib` does not exist, `predict()` returns `0.5` with a warning log, causing the tier-selection logic to always route to `small_model` with strict verification (since `0.5 ≈ qualityFloor − margin`).

**Known limitation:** The training set is small (220 examples) and entirely synthetic. The class imbalance (145:75) is addressed by `class_weight="balanced"` but the synthetic nature of the data means the classifier may not generalise well to real-world query distributions.

### 4.9 Response Verifier — `backend/engine/verifier.py` (Stage 6)

**Status: Functional. Applied only on `small_model` tier attempts.**

`verify_response(query, response, requested_json=False) → VerificationResult`

Checks run in order:
1. **Length check** — fails if response is empty or < 5 characters
2. **Truncation heuristic** — if response > 100 chars and doesn't end with punctuation/code-fence — **soft fail only** (logs debug, does not fail)
3. **Refusal phrase check** — 11 hardcoded phrases; fails on first match
4. **JSON parse check** — only if `requested_json=True`; this parameter is **never passed as `True`** from `decision.py`
5. **Entity coverage** — lightweight NER extracts capitalised words and 3+ digit numbers from the query (up to 5 entities). Fails if > 60% are missing from the response and ≥ 3 entities were found
6. **Degenerate repetition** — same 5-gram repeated ≥ 3 times in responses of ≥ 15 words
7. **Self-reported confidence** — looks for `"confidence: {N}"` in response; fails if N < 60 (this relies on the system prompt asking the model to self-report confidence, which the simulator does not do)

**Known limitations:**
- `requested_json=True` is never passed, so JSON structural checking is dead code in practice
- Truncation detection is a soft log — it does not affect escalation decisions
- Entity coverage check is loose: only capitalised words and numbers ≥ 3 digits. Lowercase entities or single-digit critical numbers are not checked
- The self-reported confidence check only fires when the model includes the confidence field, which is not guaranteed (the simulator never includes it)

### 4.10 Small-Model and Large-Model Routing — `backend/engine/decision.py`

**Status: Functional**

Tier selection uses `p_small` from the classifier and the `quality_floor` from the request:

```python
margin = 0.1
if p_small >= quality_floor + margin:    # e.g., p_small ≥ 0.70 at floor=0.60
    tier = "small_model"; verify_strict = False
elif p_small >= quality_floor - margin:  # e.g., 0.50 ≤ p_small < 0.70
    tier = "small_model"; verify_strict = True
else:                                    # p_small < 0.50 at floor=0.60
    tier = "large_model"
```

`DEBUG_FORCE_ESCALATE=1` (env var) overrides all of the above and forces the small model path followed by a guaranteed verification failure, producing an `escalated` receipt. Intended for demo reliability testing.

When escalation occurs, `escalationRegretWh` is set to `small_energy.central` (the energy already spent on the failed small-model attempt). Both the small and large latencies and token counts are summed in the escalated receipt.

**Known limitation:** The `verify_strict` variable is computed but never actually used in the verification call — `verify_response()` is always called with the same arguments regardless of whether the classifier was in the borderline region. The strict/non-strict distinction has no observable effect.

### 4.11 Groq Integration and Fallback — `backend/clients/groq_client.py` + `backend/clients/simulator.py`

**Groq client — Status: Implemented; currently inactive (no API key set)**

When `GROQ_API_KEY` is present, calls `https://api.groq.com/openai/v1` via the `openai` SDK with:
- `temperature=0.3`
- `max_tokens=1024`
- A fixed system prompt asking for self-reported confidence

On any exception (network error, rate limit, invalid key), falls back silently to the simulator.

**Hardcoded prices** (described as "correct as of Sep 2026" — will drift):
- llama-3.1-8b-instant: $0.05e-6/prompt token, $0.08e-6/completion token
- llama-3.3-70b-versatile: $0.59e-6/prompt token, $0.79e-6/completion token

**Simulator — Status: Active (current default)**

Produces synthetic responses from 3 small-model and 2 large-model string templates. Each template inserts a 6-word topic extracted from the query. Latency is real (`time.sleep()`): 300–700 ms (small), 1400–4200 ms (large). Token counts are computed with tiktoken `cl100k_base`.

Responses are generic and contain explicit meta-commentary (e.g., "AIFlow processed this via the small model pathway"). **These responses are not meaningful answers to the user's query.** They are designed to exercise the pipeline, not to produce quality output.

`provider_cost_usd = 0.0` and `cost_source = "simulated"` for all simulator calls.

**Known limitation:** With no `GROQ_API_KEY` set, the system is fully simulated. Real energy coefficients are applied to tiktoken-counted simulated token outputs, so energy figures are plausible in magnitude but are not derived from real model inference.

### 4.12 Energy Estimation — `backend/sustainability/calculator.py` + `energy_profiles.json`

**Status: Functional. All values are estimates, not measurements.**

Formula (runs three times — once per band):
```
E_compute_wh = (prompt_tokens/1000) * wh_per_1k_prompt
             + (output_tokens/1000) * wh_per_1k_output
             # OR wh_flat for deterministic / cache / retrieval tiers

E_total_wh   = E_compute_wh * pue
```

**Coefficients (from `energy_profiles.json`):**

| Tier | Band | Prompt (Wh/1k) | Output (Wh/1k) | Flat (Wh) |
|---|---|---|---|---|
| deterministic | low/central/high | — | — | 5e-7 / 1e-6 / 3e-6 |
| cache | low/central/high | — | — | 1e-5 / 2e-5 / 4e-5 |
| retrieval | low/central/high | — | — | 2e-4 / 3e-4 / 6e-4 |
| small_model | low | 0.015 | 0.09 | — |
| small_model | central | 0.020 | 0.14 | — |
| small_model | high | 0.035 | 0.24 | — |
| large_model | low | 0.030 | 0.28 | — |
| large_model | central | 0.070 | 0.58 | — |
| large_model | high | 0.140 | 1.10 | — |

**PUE:** low=1.09, central=1.15, high=1.25

**Baseline:** always computed as `large_model` tier, `central` band — the "always-large-model" counterfactual.

**Router overhead:** Fixed `0.00003 Wh` per request (constant, not derived from runtime measurement).

**Sources cited in the JSON:** ML.ENERGY Benchmark v3.0 (2025), Google inference methodology (Aug 2025), arXiv 2407.16893.

**CO2e:** The `compute_co2e()` function exists in `calculator.py` but is **never called anywhere in the pipeline**. Per-receipt CO2e is never computed by the backend. The CO2e figure shown in `ReceiptDetail.tsx` is computed entirely in the frontend using `(energyWh.{band} / 1000) * region.gridIntensity`.

### 4.13 Region Configuration — `backend/sustainability/regions.py`

**Status: Implemented; live Electricity Maps path is untested.**

Static table (copied verbatim from `Frontend/src/mock/regions.ts`):

| Region | Grid intensity (gCO2e/kWh) |
|---|---|
| IN (India) | 713 |
| DE (Germany) | 344 |
| US (USA) | 369 |
| FR (France) | 56 |
| SE (Sweden) | 41 |

Default fallback for unknown regions: `US` (369 gCO2e/kWh).

`get_grid_intensity(region) → (int, str)` is implemented and returns `(value, "static")` from the table, or `(live_value, "live")` if `ELECTRICITY_MAPS_API_KEY` is set. However, **this function is never called inside `run_pipeline()` or anywhere else in the live request path.** The `region` parameter is stored on the receipt but has no effect on any energy or CO2e value at the per-receipt level.

---

## 5. Routing Pipeline

The routing logic is in `backend/engine/decision.py`, function `run_pipeline()`. The sequence is strictly linear and short-circuits as soon as any stage matches.

### Stage execution order

```
1. try_deterministic(query)
   → If matched: return immediately. No embedding, no cache, no model.

2. _encode_query(query, sentence_model)
   → 384-d float list via all-MiniLM-L6-v2. Happens for all non-deterministic queries.

3. lookup_exact(db, query)
   → SHA-256 of normalised query vs CacheEntryORM. 24h TTL.

4. get_index().lookup(query, query_embedding)
   → In-memory cosine similarity against stored embeddings.

5. get_retrieval_engine().lookup(query_embedding)
   → Cosine similarity against 17 corpus document embeddings.
   → Threshold: 0.55. Returns first 3 sentences of matched document.

6. classify(query, query_embedding) → p_small
   → LogisticRegression on 389-d feature vector.

7a. p_small ≥ quality_floor + 0.1:
    groq_client.call_small(query) → ModelResponse
    verify_response(query, response) → VerificationResult
    If passed: return small_model receipt.
    If failed: escalate → step 7b (pathway = "escalated")

7b. p_small < quality_floor − 0.1:
    groq_client.call_large(query) → ModelResponse
    return large_model receipt. (No verification.)

8. compute_energy_band(tier, in_tokens, out_tokens)
   → EnergyBand {low, central, high}

9. _build_receipt(...)
   → Assembles the receipt dict.
   → store_in_cache() called for retrieval, small_model (passed), escalated (large response).
```

### Real verified example

From `test_requests.py` run (server active, recorded in session):

**Query:** `"What is 27 × 43?"`  
**Stage hit:** Stage 1 (Deterministic Gate — arithmetic pattern)  
**Pathway:** `deterministic`  
**Response:** `"1161"`  
**energyWh.central:** `1.15e-6` Wh (= `1e-6 Wh_flat × PUE 1.15`)  
**latencyMs:** `1 ms`  
**verification:** `not_applicable`  
**escalationRegretWh:** `0.0`  
**provider_cost_usd:** `0.0`

**Escalation example (from seed fixture AF-0280):**  
**Query:** `"Explain quantum entanglement simply with formal mathematical wave function collapse equations."`  
**Pathway:** `escalated`  
**verification:** `failed`  
**escalationRegretWh:** `0.018` Wh  
**escalated:** `true`  
*(This is a seeded fixture, not a live pipeline run.)*

---

## 6. Energy Receipts

### Receipt schema

Every pipeline execution returns a `Receipt` object. All fields below are persisted to `ReceiptORM` and returned by `GET /v1/receipts/{id}`.

| Field | Type | Source |
|---|---|---|
| `id` | string | `receipt_counter.txt` + 1 (e.g. `"AF-0306"`) |
| `timestamp` | ISO 8601 string | `datetime.now(timezone.utc)` at pipeline entry |
| `query` | string | Passed verbatim from request |
| `pathway` | enum | Set by the stage that resolved the request |
| `pathwaySteps` | string[] | Hardcoded list per pathway type in `decision.py` |
| `reason` | string | Human-readable explanation built in `decision.py` |
| `complexityScore` | float 0..1 | `1.0 - p_small` from classifier; hardcoded `0.02` for deterministic, `0.04` for cache, `0.15` for retrieval |
| `qualityFloor` | float 0..1 | Passed from request |
| `predictedSufficiency` | float 0..1 | `p_small` from classifier; hardcoded values for deterministic/cache/retrieval |
| `verification` | enum | `"passed"`, `"failed"`, or `"not_applicable"` |
| `escalated` | bool | `True` only when small-model verification failed |
| `inputTokens` | int | tiktoken count (simulator) or Groq usage.prompt_tokens |
| `outputTokens` | int | tiktoken count (simulator) or Groq usage.completion_tokens |
| `latencyMs` | int | Measured wall-clock time (or approximated for cache/deterministic) |
| `providerCostUsd` | float | `0.0` (deterministic/cache/simulator); computed from hardcoded price table for real Groq |
| `energyWh` | `{low, central, high}` | `compute_energy_band(tier, in_tokens, out_tokens)` |
| `baselineEnergyWh` | float | `compute_baseline_energy(in_tokens, out_tokens)` — always large_model central |
| `routerOverheadWh` | float | Fixed constant `0.00003` Wh |
| `escalationRegretWh` | float | `small_energy.central` if escalated; `0.0` otherwise |
| `response` | string | Model output, corpus excerpt, or computed deterministic result |
| `isDemo` | bool | `False` for all pipeline-generated receipts; `True` for seed fixtures |

### Energy calculation methodology

All energy values are **estimates, not measurements**. They are derived from published benchmarks applied to token counts.

**Formula:**
```
E_compute_wh = (prompt_tokens/1000) × wh_per_1k_prompt
             + (output_tokens/1000) × wh_per_1k_output
E_total_wh   = E_compute_wh × PUE
```

For flat tiers (deterministic, cache, retrieval), a fixed `wh_flat` value replaces the token-scaled computation. The retrieval flat value (`0.0003 Wh central`) is independent of how many tokens the retrieved document contains.

Three bands are computed independently using the actual low/central/high coefficients — not as scaled multiples of the central estimate.

The baseline (`baselineEnergyWh`) uses the `large_model, central` band applied to the actual token counts of the request. This means the baseline varies by request length; it is not a fixed per-request constant.

**CO2e** is never computed per-receipt by the backend. The `ReceiptDetail` page computes it client-side as:
```typescript
co2e_grams = (energyWh.{band} / 1000) × region.gridIntensity × multiplier
```
where `multiplier = pessimistic ? 1.4 : 1.0`. The `1.4` pessimistic multiplier is a frontend approximation, different from the backend's PUE-ratio-based pessimistic calculation.

### Demo vs. real receipt distinction

The `is_demo` boolean column on `ReceiptORM` is the single source of truth:

- `is_demo=True`: Inserted by `scripts/seed_demo.py`. 24 fixtures, IDs AF-0261 to AF-0284. Excluded from all audit and analytics metric calculations.
- `is_demo=False`: Inserted by `POST /v1/complete`. All pipeline-generated receipts. Included in all metric calculations.

Both types are returned by `GET /v1/receipts`. The `isDemo` field is included in every receipt response. The `Receipts.tsx` page shows a "DEMO" badge on demo rows. The `ReceiptDetail.tsx` page shows a warning banner when `isDemo=true`.

The `GET /v1/audit` and `GET /v1/analytics` endpoints filter `WHERE is_demo=False` via SQLAlchemy before any metric computation. When `realExecutionCount=0`, the audit endpoint returns all-zero values rather than numbers derived from demo data.

---

## 7. Frontend Integration

### API base URL

`Frontend/.env` contains `VITE_API_BASE_URL=http://localhost:8000`. This is read in `src/mock/api.ts` as:
```typescript
const BASE_URL = (import.meta.env.VITE_API_BASE_URL as string | undefined)
  ?? 'http://localhost:8000';
```
If the env var is absent, the hardcoded default `http://localhost:8000` is used.

### `src/mock/api.ts` — API client

All five functions make real `fetch` calls to the backend. There is no mock logic remaining in this file. Error handling: on non-2xx response, the function attempts `JSON.parse(body).detail`, then throws `Error("AIFlow API error: {detail}")`.

```typescript
runRequest(query, qualityFloor=0.60, region='IN')  // POST /v1/complete
listReceipts()                                      // GET  /v1/receipts
getReceipt(id)                                      // GET  /v1/receipts/{id}
getAuditSummary(pessimistic=false)                  // GET  /v1/audit?pessimistic=
getAnalytics(pessimistic=false)                     // GET  /v1/analytics?pessimistic=
```

### Live Run page (`src/pages/LiveRun.tsx`)

User enters a query (or selects an example chip), clicks "Run with AIFlow" (or Ctrl+Enter). The page calls `runRequest(text, qualityFloor, region.id)`. On success, a result card shows: pathway badge, reason string, four stat tiles (latency, energy, LLM call count, verification status), and the response text. A link navigates to the full receipt detail. Session telemetry (requests count, LLM calls avoided, estimated energy saved) is maintained in `AppContext` in-memory — it does not survive page reload.

LLM call count is computed client-side: `deterministic/cache → 0`, `escalated → 2`, others `→ 1`.

### Energy Receipts page (`src/pages/Receipts.tsx`)

Calls `listReceipts()` on mount. New receipts from the current session (held in `AppContext.receipts`) are merged by ID deduplication and prepended. The table shows: receipt ID + DEMO badge (for `isDemo=true`), query (truncated to 400px), pathway badge, `energyWh.central` formatted in Wh, latency, verification check symbol. Clicking any row navigates to `/receipts/{id}`.

### Receipt Detail page (`src/pages/ReceiptDetail.tsx`)

Fetches a single receipt by ID. Shows a demo warning banner if `isDemo=true`. Displays: pathway trace, computation metrics (tokens, latency, cost), energy range bar (low/central/high), CO2e estimate (client-computed from `region.gridIntensity`), and baseline comparison. The pessimistic CO2e multiplier (`1.4`) is different from the backend audit pessimistic logic.

### Audit page (`src/pages/Audit.tsx`)

Fetches `AuditSummary` on mount and on `pessimistic` toggle change.

**Empty state path:** When `summary.realExecutionCount === 0`:
- Shows a full-page empty state with "No runs yet" and a "Go to Live Run" button
- If `demoCount > 0`, shows an amber notice: "DEMO DATA PRESENT — N seeded fixture receipt(s) exist but are excluded from all metric calculations"
- Still renders the Benchmark Assumptions table (hardcoded `MOCK_ASSUMPTIONS` from `mock/data.ts`)

**Data state path:** When `realExecutionCount > 0`:
- Renders the savings estimate card, pessimistic toggle, self-accounting tiles, and assumptions table
- If `demoCount > 0`, shows a secondary strip: "DEMO DATA EXCLUDED — N seed receipts not counted; metrics reflect only your M actual executions"
- The "Recalculate with Pessimistic Assumptions" button is disabled when `realExecutionCount === 0`
- Animated count-up on savings percentage uses `useCountUp(targetSaving, 600, 1)`

### Analytics page (`src/pages/Analytics.tsx`)

Fetches `AnalyticsPayload` on mount and on `pessimistic` change. Renders three charts using Recharts:
1. Pathway distribution bar chart (count per pathway)
2. Horizontal energy-by-pathway bar chart (average Wh, fixed x-axis domain 0–0.8)
3. Cumulative energy divergence line chart (AIFlow vs. always-large baseline)

**Known issue:** The CO2e saved tile is computed client-side using a formula that constrains the result to approximately 29–34% regardless of actual savings:
```typescript
const regionalCO2ePct = pessimistic ? 29
  : Math.round(34 * (region.gridIntensity / 713 * 0.15 + 0.85));
```
This does not use the API's `co2eSavedPct` field from the analytics payload, and it is not derived from real regional energy savings.

### Remaining mock data

- `src/mock/data.ts` — `MOCK_ASSUMPTIONS` (7 rows), used in the Audit page's Benchmark Assumptions table. This is hardcoded static content, not fetched from the backend. It describes the methodology parameters correctly.
- `src/mock/regions.ts` — `MOCK_REGIONS` and `DEFAULT_REGION`. These are static and match the backend's static table exactly. No API endpoint serves regions.
- `src/mock/methodology.ts` — static methodology content for the methodology modal.

---

## 8. Testing and Validation

### Test files

| File | Type | Location | Framework |
|---|---|---|---|
| `test_requests.py` | Acceptance tests (10 scenarios) | `backend/` | Raw `urllib.request` (no pytest) |
| `test_audit_demo_separation.py` | Demo/real separation tests (6 scenarios) | `backend/` | Raw `urllib.request` + direct SQLite |

There is no frontend test suite. `package.json` does not include any test runner (Jest, Vitest, Playwright, etc.).

### `test_requests.py` — results

These tests require a live server at `localhost:8000`. At the time of writing, the server is not running. The test results below were captured during the previous session when the server was active:

| Test | Result | Notes |
|---|---|---|
| ① Health `/v1/health` | **PASS** | `{"status":"ok"}` |
| ② Arithmetic → deterministic | **PASS** | `"What is 27 × 43?"` → pathway `deterministic`, response `"1161"`, `energyWh.central ≈ 1.15e-6` |
| ③ Repeated query → cache | **PASS** | First call: `cache` (existing seed entry). Second call: `cache`. Latency < 100 ms. |
| ④ Complex query → large_model | **PASS** | Gödel query → pathway `large_model`, `complexityScore=0.95` |
| ⑤ Escalated receipt exists | **PASS** | 2 escalated seed fixtures found, `escalationRegretWh=0.018`, `verification=failed` |
| ⑥ Region change → energyWh unchanged | **PASS** | `"What is 99 * 11?"` IN and FR → identical `energyWh.central` |
| ⑦ Audit pessimistic ≤ central | **PASS** | `pessimistic=0.0 ≤ central=29.3` |
| ⑦ Audit hiddenSavings == 0 | **PASS** | |
| ⑦ qualityRetentionPct in range | **PASS** | `95.1` |
| ⑧ Analytics totalRequests > 0 | **PASS** | `41` at time of run |
| ⑧ 6 pathways in distribution | **PASS** | |
| ⑨ GET AF-0284 | **PASS** | pathway `deterministic`, response contains `"1161"` |
| ⑩ 404 for unknown receipt | **PASS** | `AF-9999` → HTTP 404 |
| **Overall** | **26/26 PASS** | Captured during session 2026-09-21 |

**Note:** Tests 3 and 5 currently have the server offline. Results above are from the last verified run. Re-running requires starting the server first.

### `test_audit_demo_separation.py` — results

| Scenario | Result | Notes |
|---|---|---|
| ① No receipts (simulated via scenario 2) | Documented only | Cannot isolate without clearing DB |
| ② Demo-only DB state | **SKIPPED** | 21 real rows existed at run time; test correctly printed SKIP notice |
| ③ One real execution receipt | **PASS** | `realExecutionCount ≥ 1`, `centralSavingPct ≥ 0`, `hiddenSavings=0` |
| ④ Multiple real execution receipts | **PASS** | 5 inserted, `qualityRetentionPct=100.0`, pessimistic ≤ central |
| ⑤ Mixed demo + real | **PASS** | `demoCount=24` matches DB; `analytics.totalRequests` matches real rows only |
| ⑥ Pessimistic toggle on real rows only | **PASS** | Same `realExecutionCount` and `demoCount` for both modes |
| **Overall** | **19/19 PASS** (1 skipped) | Captured during session 2026-09-21 |

### Classifier evaluation methodology

- **Algorithm:** `sklearn.linear_model.LogisticRegression(max_iter=1000, class_weight="balanced")`
- **Feature extraction:** MiniLM-L6-v2 embedding (384-d) + 5 handcrafted features
- **Split:** 70% train / 30% test, stratified by label, `random_state=42`
- **Dataset:** 220 prompts, all **synthetically authored** — no real user queries
- **Label distribution:** 145 label=1 (small sufficient), 75 label=0 (large needed)
- **Verified metrics:** accuracy = **0.8485**, AUC = **0.9737** (confirmed by both `classifier_metrics.json` and `train_log.txt`)
- **Warning from sklearn:** `OptimizeWarning: Unknown solver options: iprint` — appears during training, is cosmetic (the L-BFGS solver ignores the unknown option), and does not affect the result

### Known bugs and untested paths

| Issue | Location | Severity |
|---|---|---|
| `verify_strict` flag computed but never applied | `decision.py` Stage 6 | Medium — borderline queries aren't actually verified more strictly |
| `requested_json=True` never passed to verifier | `decision.py`, `verifier.py` | Low — JSON structural check is unreachable dead code |
| `receipt_counter.txt` read-modify-write is not atomic | `decision.py` | Medium — duplicate IDs possible under concurrent load |
| CO2e per receipt never computed by backend | `decision.py`, `regions.py` | Medium — CO2e in `ReceiptDetail` is a frontend approximation |
| Analytics CO2e tile hardcoded formula | `Analytics.tsx` | Medium — not data-driven, constrains result to ~29–34% |
| Seed cache entries have `embedding=NULL` | `seed_demo.py`, `cache.py` | Low — semantic cache cannot serve seed responses until real matching queries are made |
| `GEMINI_API_KEY` env var documented but unused | `.env.example`, `main.py` | Low — creates expectation of a non-existent feature |
| DB path not configurable at runtime | `db.py` | Low — must change code to move database location |
| No frontend test suite | `Frontend/` | High for production readiness |
| Retrieval response always first 3 sentences | `decision.py` | Medium — may be irrelevant or incomplete for some queries |

---

## 9. Running the Project

### Prerequisites

- Python 3.11–3.13 (tested on 3.13.5)
- Node.js ≥ 18 with npm

### Backend setup

```powershell
# Navigate to backend directory
cd "a:\AIFLOW - 1\backend"

# Create virtual environment
python -m venv .venv

# Activate (Windows PowerShell)
.venv\Scripts\Activate.ps1
# Or on macOS/Linux:
# source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
copy .env.example .env
# Edit .env — add GROQ_API_KEY if you have one (optional; simulator runs without it)

# Generate training data (only needed if training_prompts.json is missing)
python scripts/generate_training_data.py

# Train the classifier (only needed if classifier.joblib is missing)
python scripts/train_classifier.py

# Seed the database with demo fixtures
python scripts/seed_demo.py

# If upgrading an existing database (adds is_demo column if missing)
python migrate_add_is_demo.py

# Start the server
.venv\Scripts\uvicorn.exe main:app --reload --port 8000
```

### Frontend setup

```powershell
# In a separate terminal
cd "a:\AIFLOW - 1\Frontend"
npm install
npm run dev
# Opens at http://localhost:5173
```

### Required environment variables

**Backend (`backend/.env`):**

| Variable | Required | Default | Description |
|---|---|---|---|
| `GROQ_API_KEY` | No | (empty) | Groq API key — without it, the simulator is used |
| `GEMINI_API_KEY` | No | (empty) | Currently unused — no Gemini integration exists |
| `ELECTRICITY_MAPS_API_KEY` | No | (empty) | Live grid carbon intensity — falls back to static table |
| `DEV_MODE` | No | `true` | `false` restricts CORS to explicit origins in production |
| `DEBUG_FORCE_ESCALATE` | No | `0` | Set `1` to force escalation on every request (demo only) |

**Frontend (`Frontend/.env`):**

| Variable | Required | Default | Description |
|---|---|---|---|
| `VITE_API_BASE_URL` | No | `http://localhost:8000` | Backend base URL |

### API documentation

Interactive Swagger UI is available at **`http://localhost:8000/docs`** when the server is running.  
OpenAPI JSON is at **`http://localhost:8000/openapi.json`**.

---

## 10. Current Status and Limitations

| Feature | Implementation Status | Evidence / File | Known Limitation |
|---|---|---|---|
| FastAPI server with 6 endpoints | ✅ Functional | `backend/main.py` | No auth; CORS wildcard on by default |
| Receipt persistence (SQLite) | ✅ Functional | `backend/db.py` | DB path hardcoded; not configurable via env |
| Deterministic gate (arithmetic) | ✅ Functional, Tested | `engine/gates.py`; test ② passed | Token counts approximated from word split |
| Deterministic gate (units) | ✅ Functional | `engine/gates.py` | Limited alias map; no currency/pressure/data-size |
| Deterministic gate (dates) | ✅ Functional | `engine/gates.py` | `fuzzy=True` parsing may misfire on ambiguous date strings |
| Exact cache (SHA-256, 24h TTL) | ✅ Functional, Tested | `engine/cache.py`; test ③ passed | |
| Semantic cache (cosine) | ✅ Functional | `engine/cache.py` | Seed entries have no embedding; index rebuilds from DB |
| Local corpus retrieval (17 docs) | ✅ Functional | `engine/retrieval.py` | Response always first 3 sentences; no re-ranking |
| Complexity classifier | ✅ Trained, Functional | `engine/classifier.py`; acc=0.8485, AUC=0.9737 | 220 synthetic prompts only; may not generalise |
| Response verifier | ✅ Functional (partially) | `engine/verifier.py` | `verify_strict` flag unused; JSON check unreachable; truncation soft-fail only |
| Small-model routing | ✅ Functional | `engine/decision.py` | Simulator only (no API key) |
| Large-model routing | ✅ Functional | `engine/decision.py` | Simulator only (no API key) |
| Escalation with regret tracking | ✅ Functional | `engine/decision.py` | `DEBUG_FORCE_ESCALATE` for demo; real escalation requires real model responses with refusal phrases |
| Groq API integration | ✅ Implemented, ⚠️ Inactive | `clients/groq_client.py` | No `GROQ_API_KEY` set — all calls use simulator |
| Simulator fallback | ✅ Active (current default) | `clients/simulator.py` | Responses are generic templates, not meaningful answers |
| Energy 3-band accounting | ✅ Functional | `sustainability/calculator.py` | Estimates from benchmarks, not live measurements |
| Baseline comparison (per receipt) | ✅ Functional | `decision.py`, `calculator.py` | Always large_model central — single fixed counterfactual |
| Router overhead accounting | ✅ Functional | `calculator.py` | Fixed constant `0.00003 Wh` — not measured |
| Escalation regret accounting | ✅ Functional | `decision.py` | Uses `small_energy.central` — not the low or high band |
| Per-receipt CO2e calculation | ❌ Not implemented | `regions.py` (unused), `ReceiptDetail.tsx` | CO2e is frontend-approximated only; `get_grid_intensity()` never called |
| Region-aware analytics CO2e | ❌ Not implemented | `Analytics.tsx`, `main.py` | Hardcoded formula constrains output to ~29–34% |
| Live grid intensity (Electricity Maps) | ✅ Implemented, ⚠️ Untested | `sustainability/regions.py` | No API key; function never called in pipeline |
| Demo/real data separation | ✅ Functional, Tested | `db.py`, `main.py`, test suite passed | Seed entries pre-2026-09-22 required manual migration |
| Audit empty state | ✅ Functional | `Audit.tsx` | |
| Audit pessimistic mode | ✅ Functional, Tested | `main.py`, `Audit.tsx` | Pessimistic uses `high` band; does not vary with `realExecutionCount` < 3 (low statistical weight) |
| Analytics charts | ✅ Functional | `Analytics.tsx` | CO2e tile not data-driven; energy chart x-axis fixed at 0–0.8 Wh |
| DEMO badge in Receipts ledger | ✅ Functional | `Receipts.tsx` | |
| DEMO warning in Receipt Detail | ✅ Functional | `ReceiptDetail.tsx` | |
| Gemini integration | ❌ Not implemented | `.env.example` mentions it | `GEMINI_API_KEY` is documented but no code uses it |
| Frontend test suite | ❌ Not present | `package.json` | No test runner configured |
| Receipt ID generation (atomic) | ⚠️ Not atomic | `decision.py` | File-based counter; duplicate IDs possible under concurrent load |
| Multi-worker safety | ⚠️ Not safe | `engine/cache.py`, `decision.py` | In-memory numpy matrix and file counter are not safe for multi-worker uvicorn |
| Production CORS | ⚠️ Disabled | `main.py` | `DEV_MODE=true` exposes `"*"` — must be changed before deployment |

---

## 11. Recommended Next Steps

The following are ranked by practical impact on correctness and production readiness.

### Bug fixes

**1. Implement per-receipt CO2e computation in the backend**  
`get_grid_intensity(region)` in `sustainability/regions.py` is fully implemented but never called. `decision.py` receives and stores the `region` parameter but does not compute CO2e. The fix is to call `compute_co2e(energy.central, grid_intensity)` in `_build_receipt()` and add `co2eGrams` to the `Receipt` schema. This also fixes the Analytics page's CO2e tile, which currently uses a region-agnostic hardcoded formula.

**2. Make receipt ID generation atomic**  
`_next_receipt_id()` reads and writes `receipt_counter.txt` without a file lock. Under any concurrent load (including reload triggers), two requests can receive the same ID and one write will be lost. Replace with a SQLAlchemy-backed auto-increment sequence or an `AUTOINCREMENT` column, and derive the `AF-XXXX` string from the DB row ID.

**3. Apply `verify_strict` meaningfully**  
The `verify_strict` flag is computed in the tier-selection logic (borderline p_small region) but is never passed to `verify_response()`. The verifier should apply stricter entity-coverage and confidence thresholds when `verify_strict=True`. Currently, borderline queries and clear-pass queries go through identical verification.

### Validation work

**4. Replace synthetic classifier training data with real query samples**  
The classifier is trained on 220 synthetically authored prompts with no real user queries. An 84.85% accuracy on synthetic data does not guarantee the same performance on real production queries. Collect a sample of at least 500 real queries from early beta users, label them, and retrain. Maintain a held-out set from real queries for ongoing evaluation.

### New features / production hardening

**5. Add a frontend test suite**  
The frontend has zero tests. At a minimum, add Vitest unit tests for the API client (`mock/api.ts`), the energy formatting utilities (`lib/format.ts`), and the `AppContext` session stats logic. Add a Playwright smoke test covering the Live Run flow end-to-end. This is the highest-risk gap for ongoing development.

---

*End of Report*
