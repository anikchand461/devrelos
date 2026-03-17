"""
routes/api_routes.py – Docs, Tutorial, Analytics, Schemas, Integrations endpoints
"""

import uuid
from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from models import SchemaUpsertRequest, IntegrationRequest
from database import (
    get_all_schemas, get_schema_by_provider, upsert_schema,
    get_analytics_summary, get_interaction_history,
)
from services.integration_service import send as send_integration, broadcast
import agents.docs_agent     as docs_agent
import agents.tutorial_agent as tutorial_agent
from cache import get_cache_stats

router = APIRouter(prefix="/api", tags=["api"])


# ── Documentation ─────────────────────────────────────────────────────────────

@router.get("/docs/{provider}")
async def get_docs(
    provider:     str,
    endpoint_key: Optional[str] = Query(None),
):
    """Generate documentation for a provider (and optionally a specific endpoint)."""
    schema = await get_schema_by_provider(provider)
    if not schema:
        raise HTTPException(status_code=404, detail=f"No schema for provider: {provider}")

    content = await docs_agent.run(
        provider     = provider,
        endpoint_key = endpoint_key or "",
        schema       = schema.get("schema_json", {}),
        base_url     = schema.get("base_url", ""),
    )
    return {
        "provider":    provider,
        "endpoint":    endpoint_key,
        "content":     content,
        "base_url":    schema.get("base_url"),
        "description": schema.get("schema_json", {}).get("description", ""),
    }


# ── Tutorial ──────────────────────────────────────────────────────────────────

@router.get("/tutorial/{provider}")
async def get_tutorial(
    provider: str,
    goal:     str = Query("get started with the API"),
):
    """Generate a step-by-step tutorial for a provider and specific goal."""
    schema = await get_schema_by_provider(provider)
    if not schema:
        raise HTTPException(status_code=404, detail=f"No schema for provider: {provider}")

    tutorial = await tutorial_agent.run(
        provider = provider,
        goal     = goal,
        schema   = schema.get("schema_json", {}),
        base_url = schema.get("base_url", ""),
    )
    return {
        "provider":  provider,
        "goal":      goal,
        "tutorial":  tutorial,
        "base_url":  schema.get("base_url"),
    }


# ── Analytics ─────────────────────────────────────────────────────────────────

@router.get("/analytics")
async def get_analytics():
    """Return enterprise analytics dashboard data."""
    summary = await get_analytics_summary()
    return summary


@router.get("/analytics/session/{session_id}")
async def get_session_analytics(session_id: str):
    """Return interaction history for a specific session."""
    history = await get_interaction_history(session_id, limit=50)
    return {"session_id": session_id, "interactions": history, "count": len(history)}


# ── API Schemas ───────────────────────────────────────────────────────────────

@router.get("/schemas")
async def list_schemas():
    """List all registered API schemas."""
    schemas = await get_all_schemas()
    return {
        "schemas": [
            {
                "id":          s["id"],
                "provider":    s["provider"],
                "name":        s["name"],
                "base_url":    s["base_url"],
                "auth_type":   s["auth_type"],
                "env_key_name": s.get("env_key_name"),
                "endpoints":   list(s["schema_json"].get("endpoints", {}).keys()),
                "description": s["schema_json"].get("description", ""),
            }
            for s in schemas
        ]
    }


@router.get("/schemas/{provider}")
async def get_schema(provider: str):
    """Get full schema for a provider."""
    schema = await get_schema_by_provider(provider)
    if not schema:
        raise HTTPException(status_code=404, detail=f"Schema not found: {provider}")
    return schema


@router.post("/schemas")
async def create_or_update_schema(req: SchemaUpsertRequest):
    """Create or update an API schema."""
    schema_id = await upsert_schema(
        provider     = req.provider,
        name         = req.name,
        base_url     = req.base_url,
        schema       = req.schema_json,
        auth_type    = req.auth_type,
        env_key_name = req.env_key_name,
    )
    return {"success": True, "provider": req.provider, "id": schema_id}


# ── Integrations ──────────────────────────────────────────────────────────────

@router.post("/integrations/send")
async def send_notification(req: IntegrationRequest):
    """Send a notification to Slack, Discord, or Email."""
    result = await send_integration(
        channel  = req.channel,
        message  = req.message,
        subject  = req.subject,
        to_email = req.to_email,
        details  = None,
    )
    return result


@router.post("/integrations/broadcast")
async def broadcast_notification(req: IntegrationRequest):
    """Broadcast a notification to all configured channels."""
    result = await broadcast(message=req.message)
    return result


# ── System Health ─────────────────────────────────────────────────────────────

@router.get("/health")
async def health():
    """System health check."""
    cache_stats = await get_cache_stats()
    schemas     = await get_all_schemas()
    return {
        "status":          "ok",
        "schemas_loaded":  len(schemas),
        "providers":       [s["provider"] for s in schemas],
        "cache_stats":     cache_stats,
    }
