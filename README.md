# DevRel-in-a-Box

> Zero-friction API onboarding through personalized, executable workspaces

An AI-powered autonomous Developer Relations platform. A developer types their goal in natural language and the system generates a fully configured, runnable Requestly API workspace — with auth, payload, debugging, and code snippets — in seconds.

---

## Quick Start (Local Demo)

```bash
# 1. Clone and enter the repo
git clone https://github.com/your-org/devrel-in-a-box
cd devrel-in-a-box

# 2. Copy and configure environment variables
cp .env.example .env
# Edit .env with your LLM API keys

# 3. Start everything with Docker Compose
docker compose up --build

# 4. Visit the demo
open http://localhost:3000          # Embeddable widget demo
open http://localhost:3000/dashboard # Analytics dashboard
open http://localhost:8000/docs      # FastAPI Swagger UI
```

---

## Architecture

```
Developer → Widget (HTML/JS)
               ↓
         FastAPI Backend
               ↓
      Agent Orchestrator
       /    |    |    \
   DocAgent  WorkspaceAgent  DebugAgent  CodeAgent
       \    |    |    /
        Vector DB + LLM
               ↓
      Requestly Collection JSON
               ↓
     Developer runs API call instantly
```

---

## Project Structure

```
devrel-in-a-box/
├── backend/          FastAPI application
│   └── app/
│       ├── api/      HTTP route handlers
│       ├── agents/   AI agent implementations
│       ├── services/ Business logic
│       ├── parsers/  OpenAPI spec ingestion
│       ├── models/   Pydantic schemas + DB models
│       ├── db/       Database layer
│       └── telemetry/ Event tracking
├── frontend/
│   ├── widget/       Embeddable docs widget
│   └── dashboard/    Analytics dashboard
├── infra/            Docker + Nginx configs
├── docs/             Architecture docs
└── scripts/          Dev and deploy utilities
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend API | FastAPI (Python 3.11) |
| AI / LLM | OpenAI GPT-4o / Smolify AI |
| Vector Search | ChromaDB (local) / Pinecone (prod) |
| Database | PostgreSQL + SQLAlchemy |
| Cache | Redis |
| Frontend | Vanilla HTML/CSS/JS |
| Containerization | Docker Compose |
| API Parsing | PyYAML + jsonschema |

---

## Core Features

- **Natural language → Requestly workspace** in <5 seconds
- **Live debugging agent** that diagnoses API errors and generates fixes
- **Multi-language code generation** (Node.js, Python, Go)
- **Developer activation funnel** tracking with nudge system
- **OpenAPI spec ingestion** with semantic endpoint search
- **Embeddable widget** — one `<script>` tag in your docs
