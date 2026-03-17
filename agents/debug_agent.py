"""
agents/debug_agent.py – Debugging Agent
Analyzes failed API responses, explains errors, and suggests fixes.
"""

import json
from typing import Any, Dict, Optional
from services.groq_client import structured_completion

SYSTEM_PROMPT = """You are a Debugging Agent for DevRelOS, an AI Developer Relations platform.

When an API call fails, you analyze the error and provide a clear explanation and actionable fix.

You MUST respond with ONLY valid JSON – no preamble, no markdown fences.

Output JSON schema:
{
  "error_type":        "<authentication|validation|rate_limit|not_found|server_error|network|unknown>",
  "error_summary":     "<one sentence explanation of the error>",
  "root_cause":        "<detailed root cause analysis>",
  "user_friendly_msg": "<plain English message for the developer>",
  "suggested_fixes": [
    "<fix 1>",
    "<fix 2>"
  ],
  "retry_recommended": <true|false>,
  "retry_changes": {
    "body":         {},
    "query_params": {},
    "headers":      {}
  },
  "docs_link": "<relevant documentation URL if applicable>"
}
"""


async def run(
    request:       Dict,
    response_data: Any,
    status_code:   int,
    provider:      str,
) -> Dict:
    """Analyze a failed API response and produce debugging guidance."""
    user_message = f"""Analyze this failed API call:

Provider: {provider}
HTTP Status: {status_code}

Original Request:
{json.dumps(request, indent=2)}

Error Response:
{json.dumps(response_data, indent=2) if isinstance(response_data, dict) else str(response_data)}

Provide a complete debugging analysis with suggested fixes."""

    result = await structured_completion(
        messages    = [{"role": "user", "content": user_message}],
        system      = SYSTEM_PROMPT,
        temperature = 0.2,
        max_tokens  = 1024,
    )

    result.setdefault("error_type",        "unknown")
    result.setdefault("error_summary",     f"HTTP {status_code} error")
    result.setdefault("root_cause",        "Unknown error")
    result.setdefault("user_friendly_msg", f"The API returned status {status_code}")
    result.setdefault("suggested_fixes",   [])
    result.setdefault("retry_recommended", False)
    result.setdefault("retry_changes",     {})
    return result
