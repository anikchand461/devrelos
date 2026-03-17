"""
agents/api_mapping_agent.py – API Mapping Agent
Maps structured intent to a specific API endpoint + parameters
"""

import json
from typing import Any, Dict, List, Optional
from services.groq_client import structured_completion

SYSTEM_PROMPT = """You are an API Mapping Agent for DevRelOS.

Given a structured intent and the full API schema for a provider, produce a precise API mapping.

You MUST respond with ONLY valid JSON – no preamble, no markdown.

Output JSON schema:
{
  "provider":       "<api provider>",
  "endpoint_key":   "<key from schema endpoints>",
  "method":         "<HTTP method>",
  "path":           "<resolved path with path params substituted>",
  "path_params":    {"<key>": "<value>"},
  "query_params":   {"<key>": "<value>"},
  "body_params":    {"<key>": "<value>"},
  "content_type":   "<application/json|application/x-www-form-urlencoded|null>",
  "description":    "<what this call will do>",
  "notes":          "<any important notes about this mapping>"
}

Rules:
- Use ONLY endpoint keys that exist in the schema
- Substitute path parameters into the path (e.g. /charges/{charge_id} → /charges/ch_abc)
- For Stripe, amounts must be integers in cents
- For Twilio paths, {AccountSid} will be filled by the auth injection agent
- Never invent endpoints not in the schema
- If no matching endpoint exists, use the closest one and note it
"""


async def run(intent: Dict, schema: Dict) -> Dict:
    """Map a parsed intent to a specific API endpoint."""
    provider     = intent.get("api_provider", "unknown")
    endpoints    = schema.get("schema_json", {}).get("endpoints", {})
    base_url     = schema.get("base_url", "")

    # Serialize endpoints summary for LLM context
    endpoints_summary = json.dumps(
        {k: {"path": v["path"], "method": v["method"], "description": v["description"],
             "parameters": {pk: {"type": pv["type"], "required": pv.get("required", False), "in": pv.get("in", "body")}
                            for pk, pv in v.get("parameters", {}).items()}}
         for k, v in endpoints.items()},
        indent=2
    )

    user_message = f"""Map this intent to the correct API endpoint:

Intent:
{json.dumps(intent, indent=2)}

Provider: {provider}
Base URL: {base_url}

Available Endpoints:
{endpoints_summary}

Produce the exact API mapping JSON."""

    result = await structured_completion(
        messages    = [{"role": "user", "content": user_message}],
        system      = SYSTEM_PROMPT,
        temperature = 0.1,
        max_tokens  = 1024,
    )

    # Inject base_url into path to form full URL
    if "path" in result and "full_url" not in result:
        path = result["path"]
        result["full_url"] = base_url.rstrip("/") + "/" + path.lstrip("/")

    result.setdefault("provider",     provider)
    result.setdefault("method",       "GET")
    result.setdefault("path_params",  {})
    result.setdefault("query_params", {})
    result.setdefault("body_params",  {})
    result.setdefault("content_type", None)
    return result
