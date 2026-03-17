"""
routes/execute.py – API Execution endpoint
POST /execute → runs the generated API request against the real API
"""

import time
import uuid
from fastapi import APIRouter, HTTPException
from models import ExecuteRequest, ExecuteResponse
from services.execution_engine import execute, analyze_failure
from database import log_interaction, track_event, update_session
import agents.docs_agent as docs_agent
import agents.auth_agent as auth_agent

router = APIRouter(prefix="/api", tags=["execute"])


@router.post("/execute")
async def execute_request(req: ExecuteRequest):
    """
    Execute a generated API request against the real external API.
    Handles auth injection, retries, and error analysis automatically.
    """
    session_id = req.session_id or str(uuid.uuid4())

    # Check credentials before attempting
    missing = auth_agent.missing_credentials(req.api_provider)
    if missing:
        return {
            "success":      False,
            "status_code":  401,
            "response_data": {
                "error":   "Missing credentials",
                "missing": missing,
                "hint":    f"Add {', '.join(missing)} to your .env file and restart the server.",
            },
            "explanation":  f"Authentication credentials for {req.api_provider} are not configured.",
            "debug_info":   None,
            "response_time_ms": 0,
        }

    # Execute the API call
    status_code, response_data, elapsed_ms = await execute(
        provider     = req.api_provider,
        endpoint_key = req.endpoint,
        method       = req.method,
        url          = req.url,
        headers      = req.headers or {},
        query_params = req.params or {},
        body         = req.body,
        content_type = req.content_type,
        retry        = True,
    )

    success    = 200 <= status_code < 300
    debug_info = None

    # On failure: run debug agent
    if not success:
        request_snapshot = {
            "provider":     req.api_provider,
            "endpoint":     req.endpoint,
            "method":       req.method,
            "url":          req.url,
            "body":         req.body,
            "params":       req.params,
        }
        debug_info = await analyze_failure(
            request_data  = request_snapshot,
            response_data = response_data,
            status_code   = status_code,
            provider      = req.api_provider,
        )

    # Generate explanation from actual response
    explanation = await docs_agent.generate_from_response(
        provider      = req.api_provider,
        endpoint_key  = req.endpoint,
        request_data  = {"method": req.method, "url": req.url, "body": req.body},
        response_data = response_data,
        success       = success,
    )

    error_code = None
    if not success and isinstance(response_data, dict):
        error_code = (
            response_data.get("error", {}).get("code")
            or response_data.get("code")
            or str(status_code)
        )

    # Persist logs
    await log_interaction(
        session_id       = session_id,
        query            = req.original_query or f"Execute {req.method} {req.endpoint}",
        api_request      = {"method": req.method, "url": req.url, "body": req.body},
        response         = response_data if isinstance(response_data, dict) else {"raw": str(response_data)},
        status           = "success" if success else "error",
        response_time_ms = elapsed_ms,
        api_provider     = req.api_provider,
        endpoint         = req.endpoint,
    )
    await track_event(
        session_id       = session_id,
        event_type       = "execute",
        event_data       = {"endpoint": req.endpoint, "method": req.method},
        api_provider     = req.api_provider,
        endpoint         = req.endpoint,
        success          = success,
        error_code       = error_code,
        response_time_ms = elapsed_ms,
    )
    await update_session(session_id, last_provider=req.api_provider)

    # Build retry suggestion if debug agent recommends it
    retry_request = None
    if debug_info and debug_info.get("retry_recommended") and debug_info.get("retry_changes"):
        changes = debug_info["retry_changes"]
        retry_request = {
            "provider":     req.api_provider,
            "endpoint":     req.endpoint,
            "method":       req.method,
            "url":          req.url,
            "headers":      {**req.headers, **(changes.get("headers") or {})},
            "params":       {**req.params,  **(changes.get("query_params") or {})},
            "body":         {**(req.body or {}), **(changes.get("body") or {})},
            "content_type": req.content_type,
        }

    return {
        "success":         success,
        "status_code":     status_code,
        "response_data":   response_data,
        "explanation":     explanation,
        "debug_info":      debug_info,
        "retry_request":   retry_request,
        "response_time_ms": elapsed_ms,
    }
