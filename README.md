# ✈️ Voyager AI — Production Agentic Travel Planner

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111%2B-009688.svg)](https://fastapi.tiangolo.com/)
[![LangGraph](https://img.shields.io/badge/LangGraph-0.2%2B-FF6F00.svg)](https://github.com/langchain-ai/langgraph)
[![Pydantic v2](https://img.shields.io/badge/Pydantic-v2-E92063.svg)](https://docs.pydantic.dev/)
[![LangSmith](https://img.shields.io/badge/Observability-LangSmith-1C3C3C.svg)](https://smith.langchain.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

An enterprise-grade, autonomous travel planning system powered by **LangGraph**, **Gemini 3.6 Flash**, and **FastAPI**. Unlike naive one-shot LLM generators, Voyager AI implements a **cyclical state machine** with **deterministic mathematical guardrails**, live meteorological tool network integration, Server-Sent Events (SSE) streaming, and full **LangSmith observability**.

---

## 🌟 Key Architecture Highlights

- **Cyclical Self-Correction**: Implements LangGraph state machine routing. If an itinerary fails budget limits or has weather conflicts, it automatically enters a closed correction loop with targeted feedback.
- **Deterministic Guardrails**: 
  - **Budget Arithmetic**: Verifies that the exact sum of all activity costs never exceeds the user's spending limit.
  - **Weather Feasibility**: Cross-checks scheduled activities against live Open-Meteo forecasts. Replaces outdoor itineraries on rainy days with indoor cultural venues.
- **Live Tool Network**:
  - **OpenStreetMap Nominatim**: Resolves destination queries to precise latitude, longitude, and validated addresses.
  - **Open-Meteo API**: Fetches multi-day precipitation probabilities, temperature ranges, and WMO weather codes.
- **Real-Time Streaming**: Delivers node-by-node state transitions and progressive itinerary synthesis to the frontend via Server-Sent Events (`text/event-stream`).
- **Human-in-the-Loop Revisions**: Supports conversational itinerary modifications (e.g. *"swap dinner for a vegan bistro"*) while re-verifying deterministic constraints.
- **Unified Observability**: Native LangSmith integration tracking tokens, latencies, and node transitions nested cleanly under single root trace segments.

---

## 🔄 Agent Workflow Topology

```
                  ┌──────────────────────┐
                  │        START         │
                  └──────────┬───────────┘
                             │
                             ▼
                  ┌──────────────────────┐
                  │     gather_tools     │  ◄── Live Geocoding & Weather
                  └──────────┬───────────┘
                             │
                             ▼
                  ┌──────────────────────┐
       ┌─────────►│      synthesize      │  ◄── Structured LLM Output
       │          └──────────┬───────────┘
       │                     │
       │                     ▼
       │          ┌──────────────────────┐
       │          │ validate_guardrails  │  ◄── Exact Math & Weather Check
       │          └──────────┬───────────┘
       │                     │
[Violations & Retries < 2]   ▼   [Clean or Max Retries]
       │             /───────────────\
       │            / should_continue \ 
       │            \─────────────────/
       │                     │
┌──────┴────────┐            │
│ self_correct  │            ▼
└───────────────┘   ┌──────────────────┐
                    │       END        │
                    └──────────────────┘
```

---

## 📁 Repository Structure

```text
travel-agent-core/
├── backend/
│   ├── app/
│   │   ├── agent/             # LangGraph state machine, nodes, prompts & guardrails
│   │   │   ├── graph.py       # Compiled state machine & SSE runners
│   │   │   ├── guardrails.py  # Deterministic budget & weather validation
│   │   │   ├── nodes.py       # Individual execution node transitions
│   │   │   ├── prompts.py     # System instructions & feedback templates
│   │   │   └── state.py       # AgentState TypedDict schema
│   │   ├── api/               # FastAPI routers & SSE streaming endpoints
│   │   ├── schemas/           # Pydantic v2 data contracts (TripRequest, Itinerary)
│   │   ├── tools/             # Live API clients (Nominatim geocoding & Open-Meteo)
│   │   └── config.py          # Pydantic Settings & environment validation
│   ├── main.py                # Application entrypoint & static frontend mounting
│   ├── requirements.txt       # Pinned dependencies
│   └── .env.example           # Documented configuration template
├── frontend/                  # Modern reactive web interface
│   ├── index.html             # Semantic responsive layout
│   ├── styles.css             # Glassmorphism dark-mode design system
│   └── app.js                 # SSE stream ingestion & state rendering
├── Dockerfile                 # Multi-stage production container
├── render.yaml                # 1-Click Render Blueprint specification
└── README.md
```

---

## 🚀 Quickstart & Local Setup

### 1. Prerequisites
- Python 3.10+
- Google Gemini API Key (or OpenAI API Key)

### 2. Clone and Setup Environment

```bash
# Clone the repository
git clone https://github.com/<your-username>/travel-agent-core.git
cd travel-agent-core

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r backend/requirements.txt
```

### 3. Configure Environment Variables

Create `backend/.env` from the template:

```bash
cp backend/.env.example backend/.env
```

Populate your credentials in `backend/.env`:

```ini
# Application
ENVIRONMENT=development
DEBUG=true
API_PREFIX=/api

# LLM Provider
LLM_PROVIDER=gemini
MODEL_NAME=gemini-3.6-flash
GOOGLE_API_KEY=your_gemini_api_key_here
TEMPERATURE=0.2

# LangSmith Observability (Optional)
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=your_langsmith_key_here
LANGCHAIN_PROJECT=travel-planner-agent
LANGCHAIN_ENDPOINT=https://eu.api.smith.langchain.com
```

### 4. Run the Application

Start the unified server (serves both API and Web UI):

```bash
uvicorn backend.main:app --reload --port 8000
```

Open your browser at:
👉 **`http://localhost:8000`**

---

## 📡 API Endpoints

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/api/trips/plan/stream` | **SSE Streaming**: Yields real-time events as the agent gathers tools, invokes LLMs, and validates guardrails. |
| `POST` | `/api/trips/plan` | **Synchronous**: Executes complete workflow and returns the final verified `Itinerary`. |
| `POST` | `/api/trips/revise` | **Conversational Revision**: Re-runs synthesis with user modification instructions while retaining budget compliance. |
| `GET` | `/api/health` | **System Health**: Returns readiness and model provider status. |

---

## ☁️ Free Cloud Deployment

This project is pre-configured for **Single-Service Free Hosting** (FastAPI serves both the API and frontend UI, eliminating CORS and using only 1 free container).

### Deploying on [Render.com](https://render.com) (Recommended)

1. Fork or push this repository to your GitHub account.
2. Log into [Render](https://render.com) and click **New +** → **Web Service**.
3. Select your repository.
4. Set the build parameters:
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r backend/requirements.txt`
   - **Start Command**: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
   - **Plan**: `Free`
5. Add your environment variables (`GOOGLE_API_KEY`, `LANGCHAIN_API_KEY`, etc.).
6. Click **Create Web Service**. Your app is live with automatic HTTPS!

*Alternatively, deploy with Docker on **Koyeb**, **Hugging Face Spaces**, or **Railway** using the included `Dockerfile`.*

---

## 🔍 Observability with LangSmith

Voyager AI features unified tracing. Every trip request generates a single, clean root trace tree:

```text
▼ Trip Planner: Paris                       (Root Segment)
  ├── gather_tools                          (Coordinates & Weather)
  ├── ▼ synthesize                          (Node Transition)
  │   └── ▼ RunnableSequence                (LLM Structured Chain)
  │       ├── ChatGoogleGenerativeAI        (Gemini 3.6 Flash: prompt/completion tokens)
  │       └── PydanticToolsParser           (Schema validation)
  ├── validate_guardrails                   (Deterministic rule checks)
  └── should_continue                       (Conditional routing decision)
```

---

## 📄 License

Distributed under the MIT License. See `LICENSE` for more information.
