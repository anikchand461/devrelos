"""
orchestrator.py – AI Orchestration Layer
Coordinates all agents in sequence: intent → mapping → workflow → auth → execute
"""

import asyncio
import time
import uuid
from typing import Any, Dict, List, Optional, Tuple

import agents.intent_agent         as intent_agent
import agents.api_mapping_agent    as mapping_agent
import agents.workflow_agent       as workflow_agent
import agents.auth_agent           as auth_agent
import agents.docs_agent           as docs_agent
import agents.support_agent        as support_agent
import agents.tutorial_agent       as tutorial_agent
import agents.personalization_agent as persona_agent

from cache import (
    get_cached_intent, set_cached_intent,
    get_cached_schema, set_cached_schema,
    get_cached_session, set_cached_session,
)
from database import (
    get_schema_by_provider, get_all_schemas,
    get_or_create_session, update_session,
    get_interaction_history, log_interaction, track_event,
)


# ── Main Chat Pipeline ────────────────────────────────────────────────────────

async def process_chat(
    query:      str,
    session_id: str,
    mode:       str = "chat",
) -> Dict:
    """
    Full pipeline:
    query → session → personalization → intent → mapping → workflow → response
    """
    start = time.monotonic()

    # 1. Ensure session exists
    session  = await get_or_create_session(session_id)
    history  = await get_interaction_history(session_id, limit=10)

    # 2. Personalization profile
    profile  = await persona_agent.run(history, query)

    # 3. Parse intent
    intent   = await intent_agent.run(query, history)
    provider = intent.get("api_provider", "unknown")

    # 4. Route by mode
    if mode == "support":
        answer = await support_agent.run(query, history, {"last_provider": provider})
        result = _support_response(query, answer, profile)
        await _log_and_track(session_id, query, intent, None, result, "support", None, provider, None)
        return result

    if mode == "tutorial":
        schema   = await _get_schema(provider)
        tutorial = await tutorial_agent.run(
            provider = provider,
            goal     = query,
            schema   = schema.get("schema_json", {}) if schema else {},
            base_url = schema.get("base_url", "") if schema else "",
        )
        result = _tutorial_response(query, tutorial, profile)
        await _log_and_track(session_id, query, intent, None, result, "tutorial", None, provider, None)
        return result

    if mode == "docs":
        schema       = await _get_schema(provider)
        endpoint_key = intent.get("endpoint_key", "")
        docs = await docs_agent.run(
            provider     = provider,
            endpoint_key = endpoint_key or "",
            schema       = schema.get("schema_json", {}) if schema else {},
            base_url     = schema.get("base_url", "") if schema else "",
        )
        result = _docs_response(query, docs, provider, endpoint_key, profile)
        await _log_and_track(session_id, query, intent, None, result, "docs", None, provider, endpoint_key)
        return result

    # --- Default: chat / API workflow generation ---

    if provider == "unknown":
        # Fallback to support agent
        answer = await support_agent.run(query, history, {})
        result = _support_response(query, answer, profile)
        await _log_and_track(session_id, query, intent, None, result, "support", None, "unknown", None)
        return result

    # 5. Load API schema
    schema = await _get_schema(provider)
    if not schema:
        result = _no_schema_response(query, provider, profile)
        await _log_and_track(session_id, query, intent, None, result, "error", None, provider, None)
        return result

    # 6. Map intent → endpoint
    mapping = await mapping_agent.run(intent, schema)

    # 7. Build workflow
    workflow = await workflow_agent.run(mapping, intent)

    # 8. Extract primary request
    primary = workflow.get("primary_request", {})
    if not primary.get("url"):
        # Fallback: build from mapping directly
        primary = {
            "method":       mapping.get("method", "GET"),
            "url":          mapping.get("full_url", ""),
            "headers":      {},
            "query_params": mapping.get("query_params", {}),
            "body":         mapping.get("body_params") or None,
        }

    endpoint_key = mapping.get("endpoint_key", intent.get("endpoint_key", ""))
    content_type = mapping.get("content_type")

    # 9. Check credentials
    missing = auth_agent.missing_credentials(provider)
    cred_warning = None
    if missing:
        cred_warning = f"⚠️ Missing credentials: {', '.join(missing)}. Add them to your .env file."

    # 10. Generate documentation
    elapsed_so_far = int((time.monotonic() - start) * 1000)
    docs = await docs_agent.generate_from_response(
        provider      = provider,
        endpoint_key  = endpoint_key,
        request_data  = primary,
        response_data = None,
        success       = True,
    )

    # 11. Assemble response
    api_request_payload = {
        "provider":     provider,
        "endpoint_key": endpoint_key,
        "method":       primary.get("method", "GET"),
        "url":          primary.get("url", ""),
        "headers":      primary.get("headers", {}),
        "params":       primary.get("query_params", {}),
        "body":         primary.get("body"),
        "content_type": content_type,
        "description":  mapping.get("description", ""),
        "curl_example": workflow.get("curl_example", ""),
    }

    result = {
        "session_id":    session_id,
        "query":         query,
        "intent":        intent,
        "api_request":   api_request_payload,
        "workflow":      workflow,
        "explanation":   docs,
        "documentation": docs,
        "suggestions":   profile.get("suggestions", []),
        "profile":       profile,
        "mode":          "chat",
        "cred_warning":  cred_warning,
    }

    # 12. Update session + log
    await update_session(session_id, last_provider=provider)
    await _log_and_track(session_id, query, intent, api_request_payload, result, "chat",
                         elapsed_so_far, provider, endpoint_key)

    return result


# ── Helper: schema with cache ─────────────────────────────────────────────────

async def _get_schema(provider: str) -> Optional[Dict]:
    cached = await get_cached_schema(provider)
    if cached:
        return cached
    schema = await get_schema_by_provider(provider)
    if schema:
        await set_cached_schema(provider, schema)
    return schema


# ── Response builders ─────────────────────────────────────────────────────────

def _support_response(query: str, answer: str, profile: Dict) -> Dict:
    return {
        "session_id":   "",
        "query":        query,
        "intent":       None,
        "api_request":  None,
        "explanation":  answer,
        "suggestions":  profile.get("suggestions", []),
        "mode":         "support",
    }


def _tutorial_response(query: str, tutorial: Dict, profile: Dict) -> Dict:
    return {
        "session_id":   "",
        "query":        query,
        "intent":       None,
        "api_request":  None,
        "explanation":  None,
        "tutorial":     tutorial,
        "suggestions":  profile.get("suggestions", []),
        "mode":         "tutorial",
    }


def _docs_response(query: str, docs: str, provider: str,
                   endpoint_key: str, profile: Dict) -> Dict:
    return {
        "session_id":   "",
        "query":        query,
        "intent":       None,
        "api_request":  None,
        "documentation": docs,
        "explanation":  docs,
        "suggestions":  profile.get("suggestions", []),
        "mode":         "docs",
    }


def _no_schema_response(query: str, provider: str, profile: Dict) -> Dict:
    return {
        "session_id":   "",
        "query":        query,
        "intent":       None,
        "api_request":  None,
        "explanation":  f"No API schema found for provider '{provider}'. "
                        f"Please add it via POST /api/schemas.",
        "suggestions":  profile.get("suggestions", []),
        "mode":         "error",
    }


# ── Logging helper ────────────────────────────────────────────────────────────

async def _log_and_track(
    session_id:   str,
    query:        str,
    intent:       Dict,
    api_request:  Optional[Dict],
    result:       Dict,
    event_type:   str,
    elapsed_ms:   Optional[int],
    provider:     str,
    endpoint:     Optional[str],
) -> None:
    try:
        await log_interaction(
            session_id       = session_id,
            query            = query,
            intent           = intent,
            api_request      = api_request,
            response         = result,
            status           = event_type,
            response_time_ms = elapsed_ms,
            api_provider     = provider,
            endpoint         = endpoint,
        )
        await track_event(
            session_id       = session_id,
            event_type       = event_type,
            event_data       = {"query": query, "mode": event_type},
            api_provider     = provider,
            endpoint         = endpoint,
            success          = event_type not in ("error",),
            response_time_ms = elapsed_ms,
        )
    except Exception as exc:
        print(f"[Orchestrator] Logging error: {exc}")
