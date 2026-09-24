# AIFlow — Intelligent, Energy-Aware AI Routing

> **Making AI more efficient, one request at a time.**

AIFlow is an intelligent AI routing layer that aims to reduce unnecessary computation in AI applications. Instead of sending every prompt directly to a large language model, AIFlow evaluates the request and routes it through the least computationally expensive suitable pathway.

By combining deterministic processing, caching, retrieval, model routing, and response verification, AIFlow helps reduce redundant AI calls while providing transparent, auditable Energy Receipts for each request.

## 🌐 Live Demo

- **Deployed Link:** https://aiflow-drab.vercel.app

*The live demo requires the backend service to be available.*

## 💡 Problem Statement

Many AI applications send every user request to a large language model—even when the request could be answered through simpler computation, a cached result, or relevant existing information.

This can lead to:
- Unnecessary model calls and token usage
- Repeated computation for similar queries
- Increased latency and infrastructure costs
- Additional energy consumption

AIFlow addresses this challenge by introducing an intelligent routing and verification layer between the user and the AI model.

## 🚀 Our Solution

AIFlow analyzes incoming prompts and selects a suitable processing path based on the request and available context.

### How It Works

1. **User submits a prompt** through the AIFlow frontend.
2. **Deterministic processing** handles supported calculations and simple operations without an LLM call.
3. **Exact cache** checks whether the same request has already been processed.
4. **Semantic cache** looks for sufficiently similar previous requests.
5. **Retrieval (RAG)** searches the local knowledge corpus for relevant information.
6. **Model routing** selects an appropriate model pathway when further generation is required.
7. **Verification and escalation** help determine whether a response meets the configured quality requirements.
8. **Energy Receipt generation** records the request's processing path, usage information, verification outcome, and estimated environmental impact.

The pipeline is designed to avoid expensive computation when a simpler, suitable route is available.

## ✨ Key Features

- **Intelligent Request Routing:** Directs prompts through different processing stages.
- **Deterministic Execution:** Handles supported operations without unnecessary LLM calls.
- **Exact & Semantic Caching:** Reuses previously processed results when applicable.
- **Retrieval-Augmented Generation (RAG):** Uses relevant information from a local knowledge corpus.
- **Response Verification:** Supports response quality checks and escalation.
- **Energy Receipts:** Provides an auditable record of request processing.
- **Audit Dashboard:** Helps inspect routing and verification activity.
- **Analytics Dashboard:** Presents request and processing metrics.
- **Document Upload:** Provides a frontend workflow for submitting documents to the backend.

## 🧠 AIFlow Architecture

```text
                User Prompt
                     |
                     v
             Deterministic Gate
                     |
                     v
                Exact Cache
                     |
                     v
              Semantic Cache
                     |
                     v
             Retrieval / RAG
                     |
                     v
               Model Routing
                     |
                     v
             Response Verification
                /           \
          Accepted        Escalate
              |                |
              |          Further Model
              |             Processing
              |                |
              +-------+--------+
                      |
                      v
               Energy Receipt
                      |
                      v
               Audit & Analytics
```

## 🛠️ Tech Stack

| Component | Technology |
|---|---|
| Frontend | React, TypeScript, Vite |
| Styling | Tailwind CSS |
| Backend | Python, FastAPI |
| Data Storage | SQLite |
| Semantic Retrieval | Sentence Transformers |
| Embedding Model | all-MiniLM-L6-v2 |
| AI Model Access | Groq API |
| Frontend Deployment | Vercel |
| Backend Deployment | Railway |
| Version Control | Git & GitHub |

## 📊 Energy Receipts

AIFlow generates Energy Receipts to make request processing more transparent.

Depending on the request and available metrics, a receipt can include:

- Request and route details
- Reason for selecting a processing pathway
- Model calls and token usage
- Verification status
- Estimated energy and carbon impact
- Comparison against a baseline

**Note:** Energy and carbon figures are estimates, not direct measurements of physical power consumption. Actual impact depends on the model, infrastructure, hardware, and workload.

## 🖥️ Run AIFlow Locally

### Prerequisites

- Python 3.12+
- Node.js and npm
- Git
- A Groq API key for live model calls

### 1. Clone the Repository

```bash
git clone https://github.com/Ashika-1010/AIFLOW.git
cd AIFLOW
```

### 2. Set Up the Backend

```bash
cd backend
python -m venv .venv
```

Activate the virtual environment.

**Windows:**

```bash
.venv\Scripts\activate
```

**Linux / macOS:**

```bash
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Configure the required environment variables using your local environment configuration. Never commit API keys or secrets to GitHub.

Start the backend:

```bash
python -m uvicorn main:app --reload --port 8000
```

Backend: http://localhost:8000

Swagger API documentation: http://localhost:8000/docs

### 3. Set Up the Frontend

Open a new terminal:

```bash
cd Frontend
npm install
```

Create a `.env` file inside the `Frontend` directory:

```env
VITE_API_BASE_URL=http://localhost:8000
```

Start the frontend:

```bash
npm run dev
```

Open the local Vite URL shown in the terminal, usually http://localhost:5173.

## ⚙️ Environment Variables

Configure environment variables in your local environment or deployment dashboard.

| Variable | Purpose |
|---|---|
| `VITE_API_BASE_URL` | Backend API base URL used by the frontend |
| `GROQ_API_KEY` | API key for Groq model access |
| `DEV_MODE` | Backend development-mode configuration |
| `DEBUG_FORCE_ESCALATE` | Development/testing option for escalation behavior |

For local development, set `VITE_API_BASE_URL=http://localhost:8000`.

For the deployed frontend, configure `VITE_API_BASE_URL` with the Railway backend's public HTTPS URL.

Vite environment variables are embedded into the frontend at build time. Redeploy the frontend after changing them.

## 🔌 API Endpoints

The backend exposes REST API endpoints, including:

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/health` | Backend health check |
| POST | `/v1/complete` | Process a request through AIFlow |
| GET | `/v1/receipts` | Retrieve request receipts |
| GET | `/v1/receipts/{id}` | Retrieve a specific receipt |
| GET | `/v1/audit` | Retrieve audit information |
| GET | `/v1/analytics` | Retrieve analytics data |
| POST | `/v1/documents` | Upload a document |

Refer to the live Swagger documentation for the available request schemas and response formats.

## 🔐 Security & Privacy

- API keys and secrets should be stored in environment variables.
- The frontend communicates with the backend through HTTP API requests.
- Never expose private API keys in frontend code or commit them to the repository.
- Configure backend CORS to allow only the required frontend origins in production.

## 🚧 Current Scope & Limitations

- AIFlow is a software-based prototype and does not directly measure physical energy consumption.
- Energy and carbon impact values are estimates and depend on the assumptions and baseline used.
- Routing and verification behavior depends on the configured models, thresholds, and available context.
- Live AI generation requires valid model-provider credentials and service availability.
- The retrieval stage operates on the knowledge corpus available to the backend.

## 🔮 Future Scope

- More advanced adaptive routing strategies
- Expanded benchmarking across models and workloads
- Improved verification and confidence-based escalation
- More detailed energy and carbon estimation
- Expanded knowledge ingestion and retrieval capabilities
- Integration with additional model providers

## 👥 Team

**Project:** AIFlow  
**Team:** Stack Overflowed  
**Hackathon:** Global Innovation Hackathon 2026 — Build for a Better Future

## 📄 License

This project was developed as a hackathon prototype. Add a license file if you intend to distribute it under a specific open-source license.

---

**AIFlow — Smarter routing. Less unnecessary computation. More transparent AI.**
