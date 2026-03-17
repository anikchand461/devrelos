"""
database.py – SQLite database layer for DevRelOS
Tables: api_schemas, user_sessions, interaction_logs, analytics_events
"""

import aiosqlite
import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./devrelos.db")
DB_PATH = DATABASE_URL.replace("sqlite:///", "").replace("sqlite://", "")


# ── Schema Definitions ────────────────────────────────────────────────────────

CREATE_API_SCHEMAS = """
CREATE TABLE IF NOT EXISTS api_schemas (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    provider     TEXT    NOT NULL,
    name         TEXT    NOT NULL,
    base_url     TEXT    NOT NULL,
    schema_json  TEXT    NOT NULL,
    auth_type    TEXT    DEFAULT 'bearer',
    env_key_name TEXT,
    created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
"""

CREATE_USER_SESSIONS = """
CREATE TABLE IF NOT EXISTS user_sessions (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id        TEXT    UNIQUE NOT NULL,
    user_data         TEXT    DEFAULT '{}',
    preferences       TEXT    DEFAULT '{}',
    interaction_count INTEGER DEFAULT 0,
    last_provider     TEXT,
    created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
"""

CREATE_INTERACTION_LOGS = """
CREATE TABLE IF NOT EXISTS interaction_logs (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id       TEXT    NOT NULL,
    query            TEXT    NOT NULL,
    intent_json      TEXT,
    api_request_json TEXT,
    response_json    TEXT,
    execution_status TEXT,
    response_time_ms INTEGER,
    api_provider     TEXT,
    endpoint         TEXT,
    timestamp        TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
"""

CREATE_ANALYTICS_EVENTS = """
CREATE TABLE IF NOT EXISTS analytics_events (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id       TEXT,
    event_type       TEXT    NOT NULL,
    event_data       TEXT    DEFAULT '{}',
    api_provider     TEXT,
    endpoint         TEXT,
    success          INTEGER DEFAULT 0,
    error_code       TEXT,
    response_time_ms INTEGER,
    timestamp        TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
"""


# ── Default API Schemas ───────────────────────────────────────────────────────

DEFAULT_SCHEMAS: List[Dict] = [
    {
        "provider": "stripe",
        "name": "Stripe Payments API",
        "base_url": "https://api.stripe.com/v1",
        "auth_type": "basic",
        "env_key_name": "STRIPE_SECRET_KEY",
        "schema": {
            "description": "Accept payments, manage customers, and handle billing with Stripe.",
            "endpoints": {
                "create_payment_intent": {
                    "path": "/payment_intents",
                    "method": "POST",
                    "description": "Create a PaymentIntent to start a payment flow",
                    "content_type": "application/x-www-form-urlencoded",
                    "parameters": {
                        "amount":               {"type": "integer",  "required": True,  "in": "body", "description": "Amount in smallest currency unit (cents)"},
                        "currency":             {"type": "string",   "required": True,  "in": "body", "description": "Three-letter ISO currency code e.g. usd"},
                        "payment_method_types": {"type": "array",    "required": False, "in": "body", "description": "Payment method types e.g. ['card']"},
                        "description":          {"type": "string",   "required": False, "in": "body"},
                        "customer":             {"type": "string",   "required": False, "in": "body"}
                    }
                },
                "create_charge": {
                    "path": "/charges",
                    "method": "POST",
                    "description": "Directly charge a credit or debit card",
                    "content_type": "application/x-www-form-urlencoded",
                    "parameters": {
                        "amount":      {"type": "integer", "required": True,  "in": "body"},
                        "currency":    {"type": "string",  "required": True,  "in": "body"},
                        "source":      {"type": "string",  "required": False, "in": "body", "description": "Token or source ID"},
                        "description": {"type": "string",  "required": False, "in": "body"},
                        "customer":    {"type": "string",  "required": False, "in": "body"}
                    }
                },
                "list_charges": {
                    "path": "/charges",
                    "method": "GET",
                    "description": "List all charges",
                    "content_type": None,
                    "parameters": {
                        "limit":    {"type": "integer", "required": False, "in": "query"},
                        "customer": {"type": "string",  "required": False, "in": "query"}
                    }
                },
                "retrieve_charge": {
                    "path": "/charges/{charge_id}",
                    "method": "GET",
                    "description": "Retrieve a specific charge",
                    "content_type": None,
                    "parameters": {
                        "charge_id": {"type": "string", "required": True, "in": "path"}
                    }
                },
                "create_customer": {
                    "path": "/customers",
                    "method": "POST",
                    "description": "Create a new Stripe customer",
                    "content_type": "application/x-www-form-urlencoded",
                    "parameters": {
                        "email":       {"type": "string", "required": False, "in": "body"},
                        "name":        {"type": "string", "required": False, "in": "body"},
                        "description": {"type": "string", "required": False, "in": "body"},
                        "phone":       {"type": "string", "required": False, "in": "body"}
                    }
                },
                "list_customers": {
                    "path": "/customers",
                    "method": "GET",
                    "description": "List all customers",
                    "content_type": None,
                    "parameters": {
                        "limit": {"type": "integer", "required": False, "in": "query"},
                        "email": {"type": "string",  "required": False, "in": "query"}
                    }
                },
                "create_refund": {
                    "path": "/refunds",
                    "method": "POST",
                    "description": "Refund a charge",
                    "content_type": "application/x-www-form-urlencoded",
                    "parameters": {
                        "charge":         {"type": "string",  "required": False, "in": "body"},
                        "payment_intent": {"type": "string",  "required": False, "in": "body"},
                        "amount":         {"type": "integer", "required": False, "in": "body"}
                    }
                },
                "list_payment_intents": {
                    "path": "/payment_intents",
                    "method": "GET",
                    "description": "List all payment intents",
                    "content_type": None,
                    "parameters": {
                        "limit":    {"type": "integer", "required": False, "in": "query"},
                        "customer": {"type": "string",  "required": False, "in": "query"}
                    }
                }
            }
        }
    },
    {
        "provider": "twilio",
        "name": "Twilio Communications API",
        "base_url": "https://api.twilio.com/2010-04-01",
        "auth_type": "twilio_basic",
        "env_key_name": "TWILIO_AUTH_TOKEN",
        "schema": {
            "description": "Send SMS, make calls, and manage phone numbers with Twilio.",
            "endpoints": {
                "send_sms": {
                    "path": "/Accounts/{AccountSid}/Messages.json",
                    "method": "POST",
                    "description": "Send an SMS message",
                    "content_type": "application/x-www-form-urlencoded",
                    "parameters": {
                        "To":   {"type": "string", "required": True,  "in": "body", "description": "Recipient phone number in E.164 format"},
                        "From": {"type": "string", "required": True,  "in": "body", "description": "Sender Twilio phone number"},
                        "Body": {"type": "string", "required": True,  "in": "body", "description": "Message text content"}
                    }
                },
                "list_messages": {
                    "path": "/Accounts/{AccountSid}/Messages.json",
                    "method": "GET",
                    "description": "List all messages",
                    "content_type": None,
                    "parameters": {
                        "To":       {"type": "string",  "required": False, "in": "query"},
                        "From":     {"type": "string",  "required": False, "in": "query"},
                        "PageSize": {"type": "integer", "required": False, "in": "query"}
                    }
                },
                "make_call": {
                    "path": "/Accounts/{AccountSid}/Calls.json",
                    "method": "POST",
                    "description": "Initiate an outbound phone call",
                    "content_type": "application/x-www-form-urlencoded",
                    "parameters": {
                        "To":   {"type": "string", "required": True,  "in": "body"},
                        "From": {"type": "string", "required": True,  "in": "body"},
                        "Url":  {"type": "string", "required": True,  "in": "body", "description": "TwiML URL to handle the call"}
                    }
                },
                "list_calls": {
                    "path": "/Accounts/{AccountSid}/Calls.json",
                    "method": "GET",
                    "description": "List all calls",
                    "content_type": None,
                    "parameters": {
                        "To":       {"type": "string",  "required": False, "in": "query"},
                        "From":     {"type": "string",  "required": False, "in": "query"},
                        "PageSize": {"type": "integer", "required": False, "in": "query"}
                    }
                }
            }
        }
    },
    {
        "provider": "github",
        "name": "GitHub REST API",
        "base_url": "https://api.github.com",
        "auth_type": "bearer",
        "env_key_name": "GITHUB_TOKEN",
        "schema": {
            "description": "Manage repositories, issues, pull requests, and more with the GitHub API.",
            "endpoints": {
                "get_authenticated_user": {
                    "path": "/user",
                    "method": "GET",
                    "description": "Get the currently authenticated user",
                    "content_type": None,
                    "parameters": {}
                },
                "list_repos": {
                    "path": "/user/repos",
                    "method": "GET",
                    "description": "List repositories for the authenticated user",
                    "content_type": None,
                    "parameters": {
                        "type":     {"type": "string",  "required": False, "in": "query", "description": "all, owner, public, private, member"},
                        "sort":     {"type": "string",  "required": False, "in": "query"},
                        "per_page": {"type": "integer", "required": False, "in": "query"}
                    }
                },
                "create_repo": {
                    "path": "/user/repos",
                    "method": "POST",
                    "description": "Create a new repository",
                    "content_type": "application/json",
                    "parameters": {
                        "name":        {"type": "string",  "required": True,  "in": "body"},
                        "description": {"type": "string",  "required": False, "in": "body"},
                        "private":     {"type": "boolean", "required": False, "in": "body"},
                        "auto_init":   {"type": "boolean", "required": False, "in": "body"}
                    }
                },
                "create_issue": {
                    "path": "/repos/{owner}/{repo}/issues",
                    "method": "POST",
                    "description": "Create an issue in a repository",
                    "content_type": "application/json",
                    "parameters": {
                        "owner":  {"type": "string", "required": True, "in": "path"},
                        "repo":   {"type": "string", "required": True, "in": "path"},
                        "title":  {"type": "string", "required": True,  "in": "body"},
                        "body":   {"type": "string", "required": False, "in": "body"},
                        "labels": {"type": "array",  "required": False, "in": "body"}
                    }
                },
                "list_issues": {
                    "path": "/repos/{owner}/{repo}/issues",
                    "method": "GET",
                    "description": "List issues in a repository",
                    "content_type": None,
                    "parameters": {
                        "owner": {"type": "string",  "required": True,  "in": "path"},
                        "repo":  {"type": "string",  "required": True,  "in": "path"},
                        "state": {"type": "string",  "required": False, "in": "query"},
                        "per_page": {"type": "integer", "required": False, "in": "query"}
                    }
                },
                "get_repo": {
                    "path": "/repos/{owner}/{repo}",
                    "method": "GET",
                    "description": "Get a specific repository",
                    "content_type": None,
                    "parameters": {
                        "owner": {"type": "string", "required": True, "in": "path"},
                        "repo":  {"type": "string", "required": True, "in": "path"}
                    }
                }
            }
        }
    }
]


# ── Initialization ────────────────────────────────────────────────────────────

async def init_db() -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        await db.execute(CREATE_API_SCHEMAS)
        await db.execute(CREATE_USER_SESSIONS)
        await db.execute(CREATE_INTERACTION_LOGS)
        await db.execute(CREATE_ANALYTICS_EVENTS)
        await db.commit()
        await _seed_if_empty(db)
        print(f"[DB] Initialized at {DB_PATH}")


async def _seed_if_empty(db: aiosqlite.Connection) -> None:
    cur = await db.execute("SELECT COUNT(*) FROM api_schemas")
    row = await cur.fetchone()
    if row[0] > 0:
        return
    for s in DEFAULT_SCHEMAS:
        await db.execute(
            "INSERT INTO api_schemas (provider, name, base_url, schema_json, auth_type, env_key_name) VALUES (?,?,?,?,?,?)",
            (s["provider"], s["name"], s["base_url"],
             json.dumps(s["schema"]), s["auth_type"], s.get("env_key_name"))
        )
    await db.commit()
    print("[DB] Seeded default API schemas")


# ── Generic Helpers ───────────────────────────────────────────────────────────

async def fetchone(query: str, params: tuple = ()) -> Optional[Dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(query, params)
        row = await cur.fetchone()
        return dict(row) if row else None


async def fetchall(query: str, params: tuple = ()) -> List[Dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(query, params)
        rows = await cur.fetchall()
        return [dict(r) for r in rows]


async def execute_write(query: str, params: tuple = ()) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(query, params)
        await db.commit()
        return cur.lastrowid


# ── API Schemas ───────────────────────────────────────────────────────────────

async def get_all_schemas() -> List[Dict]:
    rows = await fetchall("SELECT * FROM api_schemas ORDER BY provider")
    for r in rows:
        r["schema_json"] = json.loads(r["schema_json"])
    return rows


async def get_schema_by_provider(provider: str) -> Optional[Dict]:
    row = await fetchone("SELECT * FROM api_schemas WHERE provider=? LIMIT 1", (provider,))
    if row:
        row["schema_json"] = json.loads(row["schema_json"])
    return row


async def upsert_schema(provider: str, name: str, base_url: str,
                        schema: Dict, auth_type: str, env_key_name: str) -> int:
    existing = await fetchone("SELECT id FROM api_schemas WHERE provider=?", (provider,))
    if existing:
        await execute_write(
            "UPDATE api_schemas SET name=?,base_url=?,schema_json=?,auth_type=?,env_key_name=?,updated_at=CURRENT_TIMESTAMP WHERE provider=?",
            (name, base_url, json.dumps(schema), auth_type, env_key_name, provider)
        )
        return existing["id"]
    return await execute_write(
        "INSERT INTO api_schemas (provider,name,base_url,schema_json,auth_type,env_key_name) VALUES (?,?,?,?,?,?)",
        (provider, name, base_url, json.dumps(schema), auth_type, env_key_name)
    )


# ── Sessions ──────────────────────────────────────────────────────────────────

async def get_or_create_session(session_id: str) -> Dict:
    row = await fetchone("SELECT * FROM user_sessions WHERE session_id=?", (session_id,))
    if row:
        row["user_data"]   = json.loads(row["user_data"])
        row["preferences"] = json.loads(row["preferences"])
        return row
    await execute_write(
        "INSERT INTO user_sessions (session_id) VALUES (?)", (session_id,)
    )
    return {"session_id": session_id, "user_data": {}, "preferences": {}, "interaction_count": 0}


async def update_session(session_id: str, user_data: Dict = None,
                         preferences: Dict = None, last_provider: str = None) -> None:
    session = await get_or_create_session(session_id)
    ud   = user_data   or session.get("user_data",   {})
    pref = preferences or session.get("preferences", {})
    lp   = last_provider or session.get("last_provider")
    await execute_write(
        """UPDATE user_sessions
           SET user_data=?, preferences=?, last_provider=?,
               interaction_count=interaction_count+1, updated_at=CURRENT_TIMESTAMP
           WHERE session_id=?""",
        (json.dumps(ud), json.dumps(pref), lp, session_id)
    )


# ── Interaction Logs ──────────────────────────────────────────────────────────

async def log_interaction(session_id: str, query: str, intent: Dict = None,
                          api_request: Dict = None, response: Dict = None,
                          status: str = None, response_time_ms: int = None,
                          api_provider: str = None, endpoint: str = None) -> int:
    return await execute_write(
        """INSERT INTO interaction_logs
           (session_id, query, intent_json, api_request_json, response_json,
            execution_status, response_time_ms, api_provider, endpoint)
           VALUES (?,?,?,?,?,?,?,?,?)""",
        (session_id, query,
         json.dumps(intent)      if intent      else None,
         json.dumps(api_request) if api_request else None,
         json.dumps(response)    if response    else None,
         status, response_time_ms, api_provider, endpoint)
    )


async def get_interaction_history(session_id: str, limit: int = 20) -> List[Dict]:
    rows = await fetchall(
        "SELECT * FROM interaction_logs WHERE session_id=? ORDER BY timestamp DESC LIMIT ?",
        (session_id, limit)
    )
    for r in rows:
        for field in ("intent_json", "api_request_json", "response_json"):
            if r.get(field):
                try:
                    r[field] = json.loads(r[field])
                except Exception:
                    pass
    return rows


# ── Analytics Events ──────────────────────────────────────────────────────────

async def track_event(session_id: str, event_type: str, event_data: Dict = None,
                      api_provider: str = None, endpoint: str = None,
                      success: bool = False, error_code: str = None,
                      response_time_ms: int = None) -> int:
    return await execute_write(
        """INSERT INTO analytics_events
           (session_id, event_type, event_data, api_provider, endpoint,
            success, error_code, response_time_ms)
           VALUES (?,?,?,?,?,?,?,?)""",
        (session_id, event_type,
         json.dumps(event_data or {}),
         api_provider, endpoint,
         1 if success else 0,
         error_code, response_time_ms)
    )


async def get_analytics_summary() -> Dict:
    """Aggregate all analytics metrics for the dashboard."""
    # Total interactions
    total = await fetchone("SELECT COUNT(*) AS cnt FROM interaction_logs")

    # Successful executions
    success = await fetchone(
        "SELECT COUNT(*) AS cnt FROM analytics_events WHERE event_type='execute' AND success=1"
    )
    failed = await fetchone(
        "SELECT COUNT(*) AS cnt FROM analytics_events WHERE event_type='execute' AND success=0"
    )

    # Avg response time
    avg_rt = await fetchone(
        "SELECT AVG(response_time_ms) AS avg FROM analytics_events WHERE response_time_ms IS NOT NULL"
    )

    # Endpoint usage
    endpoint_usage = await fetchall(
        """SELECT endpoint, api_provider, COUNT(*) AS cnt
           FROM analytics_events WHERE endpoint IS NOT NULL
           GROUP BY endpoint, api_provider ORDER BY cnt DESC LIMIT 20"""
    )

    # Error frequency
    errors = await fetchall(
        """SELECT error_code, COUNT(*) AS cnt
           FROM analytics_events WHERE error_code IS NOT NULL AND error_code != ''
           GROUP BY error_code ORDER BY cnt DESC LIMIT 10"""
    )

    # Daily activity (last 14 days)
    daily = await fetchall(
        """SELECT date(timestamp) AS day, COUNT(*) AS cnt
           FROM analytics_events
           WHERE timestamp >= datetime('now','-14 days')
           GROUP BY day ORDER BY day"""
    )

    # Provider breakdown
    providers = await fetchall(
        """SELECT api_provider, COUNT(*) AS cnt
           FROM analytics_events WHERE api_provider IS NOT NULL
           GROUP BY api_provider ORDER BY cnt DESC"""
    )

    # Sessions
    sessions = await fetchone("SELECT COUNT(DISTINCT session_id) AS cnt FROM user_sessions")

    # First successful call time (median approx via avg for SQLite)
    first_call = await fetchone(
        """SELECT AVG(response_time_ms) AS avg FROM analytics_events
           WHERE event_type='execute' AND success=1 AND response_time_ms IS NOT NULL"""
    )

    total_exec   = (success["cnt"] or 0) + (failed["cnt"] or 0)
    conversion   = round((success["cnt"] / total_exec * 100), 1) if total_exec > 0 else 0

    return {
        "total_interactions":       total["cnt"],
        "total_sessions":           sessions["cnt"],
        "successful_executions":    success["cnt"],
        "failed_executions":        failed["cnt"],
        "conversion_rate":          conversion,
        "avg_response_time_ms":     round(avg_rt["avg"] or 0, 1),
        "avg_first_call_time_ms":   round(first_call["avg"] or 0, 1),
        "endpoint_usage":           endpoint_usage,
        "error_frequency":          errors,
        "daily_activity":           daily,
        "provider_breakdown":       providers,
    }
