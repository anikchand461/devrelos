# ⚡ DevRelOS – AI DevRel-in-a-Box

> **Fully autonomous AI-powered Developer Relations platform** — chat, voice, API generation, live execution, analytics, and integrations.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    User Interaction Layer                     │
│         Chat (text + voice)  ←→  API Playground              │
└─────────────────────────┬───────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────┐
│                AI Orchestration Layer (FastAPI)               │
│  Intent Agent → Mapping Agent → Workflow Agent → Auth Agent  │
│  Docs Agent | Tutorial Agent | Support Agent | Persona Agent │
└──────┬──────────────────────────────────────┬───────────────┘
       │                                      │
┌──────▼──────┐                    ┌──────────▼──────────────┐
│ Execution   │                    │   Data & Cache Layer      │
│ Engine      │                    │  SQLite + LRU Cache       │
│ (real APIs) │                    │  (intent/schema/session)  │
└──────┬──────┘                    └─────────────────────────┘
       │
┌──────▼───────────────────────────────────────────────────────┐
│           External APIs: Stripe │ Twilio │ GitHub             │
│        Integrations: Slack │ Discord │ Email                  │
└──────────────────────────────────────────────────────────────┘
```

---

## Quick Start

### 1. Clone / Extract the project

```bash
cd devrelos
```

### 2. Configure your `.env` file

```bash
# Required for core AI functionality
GROQ_API_KEY=your_groq_api_key_here

# Add the APIs you want to use
STRIPE_SECRET_KEY=sk_test_xxxx
TWILIO_ACCOUNT_SID=ACxxxx
TWILIO_AUTH_TOKEN=xxxx
TWILIO_FROM_NUMBER=+1234567890
GITHUB_TOKEN=ghp_xxxx

# Optional integrations
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
SMTP_HOST=smtp.gmail.com
SMTP_USER=you@gmail.com
SMTP_PASSWORD=your_app_password
```

### 3. Install & Run

**Option A – Shell script (recommended)**
```bash
bash setup.sh
```

**Option B – Manual**
```bash
python3 -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

**Option C – Docker**
```bash
docker-compose up --build
```

### 4. Open the app

| URL | Description |
|-----|-------------|
| http://localhost:8000 | Main Chat UI |
| http://localhost:8000/analytics | Analytics Dashboard |
| http://localhost:8000/docs-ui | AI-Generated API Docs |
| http://localhost:8000/swagger | FastAPI Swagger UI |

---

## API Keys Setup

### Groq (Required)
1. Go to https://console.groq.com
2. Create an API key
3. Set `GROQ_API_KEY` in `.env`

### Stripe
1. Go to https://dashboard.stripe.com/test/apikeys
2. Copy your **Secret key** (starts with `sk_test_`)
3. Set `STRIPE_SECRET_KEY` in `.env`

### Twilio
1. Go to https://console.twilio.com
2. Copy **Account SID** and **Auth Token** from the dashboard
3. Get or buy a phone number for `TWILIO_FROM_NUMBER`
4. Set all three in `.env`

### GitHub
1. Go to https://github.com/settings/tokens
2. Generate a **Personal Access Token** (Classic)
3. Grant scopes: `repo`, `user`
4. Set `GITHUB_TOKEN` in `.env`

---

## Test Scenarios

### Stripe – Charge a customer

**Type in chat:**
```
Charge $50 to a customer
```

Expected flow:
1. Intent Agent parses → `{action: "create", resource: "payment_intent", amount: 5000, currency: "usd"}`
2. Mapping Agent maps → `POST /v1/payment_intents`
3. Workflow Agent builds request structure
4. Right panel shows the API request with Execute button
5. Click **▶ Execute Request**
6. Real Stripe API is called
7. Response shows PaymentIntent object

---

### Stripe – Create a customer

```
Create a Stripe customer with email john@example.com
```

---

### Stripe – List charges

```
List the last 10 Stripe charges
```

---

### Stripe – Refund

```
Refund payment intent pi_3xxx
```

---

### Twilio – Send SMS

```
Send an SMS to +1234567890 saying "Hello from DevRelOS"
```

---

### Twilio – Make a call

```
Make a call to +1234567890
```

---

### GitHub – Create a repo

```
Create a private GitHub repository called my-project with a README
```

---

### GitHub – List issues

```
List all open issues in my repo username/my-repo
```

---

### Support Mode

Click the **🎧 Support** chip, then ask:
```
What is the difference between a PaymentIntent and a Charge in Stripe?
```

---

### Tutorial Mode

Click the **📚 Tutorial** chip, then ask:
```
How do I accept payments end-to-end with Stripe?
```

---

### Documentation Mode

Click the **📄 Docs** chip, then ask:
```
Show me docs for Stripe create_payment_intent
```

---

## REST API Reference

### POST /api/chat
```json
{
  "query": "Charge $50 to a customer",
  "session_id": "optional-uuid",
  "mode": "chat"
}
```
Returns: intent, api_request, explanation, suggestions

---

### POST /api/execute
```json
{
  "api_provider": "stripe",
  "endpoint": "create_payment_intent",
  "method": "POST",
  "url": "https://api.stripe.com/v1/payment_intents",
  "body": { "amount": 5000, "currency": "usd" },
  "content_type": "application/x-www-form-urlencoded"
}
```

---

### GET /api/docs/{provider}?endpoint_key=create_payment_intent

---

### GET /api/tutorial/{provider}?goal=accept+payments

---

### GET /api/analytics

---

### GET /api/schemas

---

### POST /api/schemas
Add a custom API provider schema.

---

### POST /api/integrations/send
```json
{
  "channel": "slack",
  "message": "New payment received!",
  "session_id": "optional"
}
```

---

## Project Structure

```
devrelos/
├── main.py                   # FastAPI app entry point
├── orchestrator.py           # AI pipeline coordinator
├── database.py               # SQLite + schema seeding
├── models.py                 # Pydantic models
├── cache.py                  # LRU in-memory cache
├── requirements.txt
├── .env                      # Your API keys (gitignored)
├── Dockerfile
├── docker-compose.yml
├── setup.sh
│
├── agents/
│   ├── intent_agent.py       # NLP → structured intent
│   ├── api_mapping_agent.py  # intent → endpoint mapping
│   ├── workflow_agent.py     # builds request structure
│   ├── auth_agent.py         # injects real credentials
│   ├── debug_agent.py        # analyzes failures
│   ├── docs_agent.py         # generates documentation
│   ├── tutorial_agent.py     # generates tutorials
│   ├── support_agent.py      # conversational Q&A
│   └── personalization_agent.py  # session personalization
│
├── routes/
│   ├── chat.py               # POST /api/chat
│   ├── execute.py            # POST /api/execute
│   └── api_routes.py         # docs, tutorial, analytics, schemas
│
├── services/
│   ├── groq_client.py        # Groq API singleton
│   ├── execution_engine.py   # HTTP request executor + retry
│   └── integration_service.py # Slack, Discord, Email
│
├── static/
│   ├── css/style.css
│   └── js/app.js
│
└── templates/
    ├── index.html             # Main chat UI
    ├── analytics.html         # Analytics dashboard
    └── docs.html              # API docs viewer
```

---

## AI Agents

| Agent | Input | Output |
|-------|-------|--------|
| **Intent Agent** | Natural language query | Structured intent JSON |
| **API Mapping Agent** | Intent + schema | Endpoint + params mapping |
| **Workflow Agent** | API mapping | Complete request + curl |
| **Auth Injection Agent** | Provider + request | Authenticated request |
| **Debugging Agent** | Failed response | Root cause + fixes |
| **Docs Agent** | Provider + endpoint | Markdown documentation |
| **Tutorial Agent** | Provider + goal | Step-by-step guide |
| **Support Agent** | Developer question | Conversational answer |
| **Personalization Engine** | Session history | User profile + suggestions |

---

## Analytics Metrics

- **Time to first successful API call** (avg)
- **Drop-off points** (error frequency by endpoint)
- **Error frequency** (by error code)
- **Endpoint usage** (top endpoints by call count)
- **Conversion rate** (success / total executions)
- **Daily activity** (14-day trend)
- **Provider breakdown** (calls per provider)

---

## Integrations

Configure webhook URLs in `.env` to enable:

| Channel | Env Var | Docs |
|---------|---------|------|
| Slack | `SLACK_WEBHOOK_URL` | https://api.slack.com/messaging/webhooks |
| Discord | `DISCORD_WEBHOOK_URL` | https://discord.com/developers/docs/resources/webhook |
| Email | `SMTP_*` vars | Gmail App Passwords |

---

## Adding Custom API Providers

POST to `/api/schemas`:

```json
{
  "provider": "openai",
  "name": "OpenAI API",
  "base_url": "https://api.openai.com/v1",
  "auth_type": "bearer",
  "env_key_name": "OPENAI_API_KEY",
  "schema_json": {
    "description": "OpenAI models API",
    "endpoints": {
      "chat_completion": {
        "path": "/chat/completions",
        "method": "POST",
        "description": "Generate a chat completion",
        "content_type": "application/json",
        "parameters": {
          "model":    { "type": "string",  "required": true,  "in": "body" },
          "messages": { "type": "array",   "required": true,  "in": "body" },
          "max_tokens": { "type": "integer", "required": false, "in": "body" }
        }
      }
    }
  }
}
```

Then in the chat: *"Generate a chat completion with gpt-4o"* will work automatically.

---

## Troubleshooting

**`GROQ_API_KEY not set`**
→ Add your key to `.env` and restart the server.

**`Missing credentials: STRIPE_SECRET_KEY`**
→ Shown as a warning banner in the UI. Add to `.env`, restart.

**Twilio SMS fails with 401**
→ Verify `TWILIO_ACCOUNT_SID` and `TWILIO_AUTH_TOKEN` are correct.

**GitHub 401 Unauthorized**
→ Ensure `GITHUB_TOKEN` has `repo` and `user` scopes.

**Port 8000 in use**
→ Set `PORT=8001` in `.env` or kill the conflicting process.
