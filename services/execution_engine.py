"""
services/execution_engine.py – API Execution Engine
Makes real HTTP calls to APIs with proper auth, form encoding, and error handling.
Includes retry logic for transient failures.
"""

import time
import json
import asyncio
import httpx
from typing import Any, Dict, Optional, Tuple
from urllib.parse import urlencode

import agents.auth_agent  as auth_agent
import agents.debug_agent as debug_agent
from database import get_schema_by_provider

# Retry config
MAX_RETRIES   = 3
RETRY_BACKOFF = [1.0, 2.0, 4.0]  # seconds between retries
RETRY_CODES   = {429, 500, 502, 503, 504}

TIMEOUT = httpx.Timeout(30.0, connect=10.0)


async def execute(
    provider:      str,
    endpoint_key:  str,
    method:        str,
    url:           str,
    headers:       Dict[str, str],
    query_params:  Dict[str, Any],
    body:          Optional[Dict[str, Any]],
    content_type:  Optional[str],
    retry:         bool = True,
) -> Tuple[int, Any, int]:
    """
    Execute an API request.
    Returns: (status_code, response_data, response_time_ms)
    """
    # Get schema for auth_type / env_key_name
    schema = await get_schema_by_provider(provider)
    auth_type    = schema.get("auth_type",    "bearer") if schema else "bearer"
    env_key_name = schema.get("env_key_name", None)     if schema else None

    # Inject authentication + resolve dynamic placeholders
    injected = auth_agent.inject(
        provider     = provider,
        url          = url,
        headers      = dict(headers),
        body         = body,
        auth_type    = auth_type,
        env_key_name = env_key_name,
    )
    final_url     = injected["url"]
    final_headers = injected["headers"]
    final_body    = injected["body"]

    # Set content-type if body present and not yet set
    if final_body and "Content-Type" not in final_headers:
        ct = content_type or "application/json"
        final_headers["Content-Type"] = ct

    # Remove empty query params
    clean_params = {k: v for k, v in (query_params or {}).items() if v is not None and v != ""}

    attempt   = 0
    last_exc  = None

    while attempt < (MAX_RETRIES if retry else 1):
        start = time.monotonic()
        try:
            async with httpx.AsyncClient(timeout=TIMEOUT, follow_redirects=True) as client:
                resp = await _send(
                    client       = client,
                    method       = method.upper(),
                    url          = final_url,
                    headers      = final_headers,
                    params       = clean_params,
                    body         = final_body,
                    content_type = final_headers.get("Content-Type", ""),
                )
            elapsed_ms = int((time.monotonic() - start) * 1000)

            # Parse response
            try:
                data = resp.json()
            except Exception:
                data = resp.text

            if resp.status_code in RETRY_CODES and attempt < MAX_RETRIES - 1:
                wait = RETRY_BACKOFF[attempt]
                attempt += 1
                await asyncio.sleep(wait)
                continue

            return resp.status_code, data, elapsed_ms

        except httpx.TimeoutException as exc:
            last_exc   = str(exc)
            elapsed_ms = int((time.monotonic() - start) * 1000)
            if attempt < MAX_RETRIES - 1:
                await asyncio.sleep(RETRY_BACKOFF[attempt])
                attempt += 1
                continue
            return 408, {"error": "Request timeout", "detail": last_exc}, elapsed_ms

        except httpx.RequestError as exc:
            last_exc   = str(exc)
            elapsed_ms = int((time.monotonic() - start) * 1000)
            return 0, {"error": "Network error", "detail": last_exc}, elapsed_ms

    return 0, {"error": "Max retries exceeded", "last_error": last_exc}, 0


async def _send(
    client:       httpx.AsyncClient,
    method:       str,
    url:          str,
    headers:      Dict,
    params:       Dict,
    body:         Optional[Dict],
    content_type: str,
) -> httpx.Response:
    """Build and send the HTTP request."""
    kwargs: Dict[str, Any] = {"headers": headers, "params": params}

    if body:
        ct = content_type.lower()
        if "form" in ct or "x-www-form-urlencoded" in ct:
            # Flatten nested lists for form encoding (e.g. Stripe)
            flat = _flatten_for_form(body)
            kwargs["data"] = flat
        else:
            kwargs["json"] = body

    return await client.request(method, url, **kwargs)


def _flatten_for_form(data: Dict, prefix: str = "") -> Dict:
    """
    Flatten a dict for application/x-www-form-urlencoded.
    Handles arrays: payment_method_types[] = ["card"] → payment_method_types[]=card
    """
    result = {}
    for key, value in data.items():
        full_key = f"{prefix}[{key}]" if prefix else key
        if isinstance(value, dict):
            result.update(_flatten_for_form(value, full_key))
        elif isinstance(value, list):
            for item in value:
                result[f"{full_key}[]"] = item
        elif value is not None:
            result[full_key] = str(value)
    return result


async def analyze_failure(
    request_data:  Dict,
    response_data: Any,
    status_code:   int,
    provider:      str,
) -> Dict:
    """Delegate to debug agent for failure analysis."""
    return await debug_agent.run(
        request       = request_data,
        response_data = response_data,
        status_code   = status_code,
        provider      = provider,
    )
