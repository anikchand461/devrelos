"""
agents/intent_agent.py – Intent Understanding Agent
Extracts: action, resource, parameters, api_provider, endpoint_key, confidence
"""

import json
from typing import Any, Dict, List, Optional
from services.groq_client import structured_completion
from cache import get_cached_intent, set_cached_intent

SYSTEM_PROMPT = """You are an Intent Understanding Agent for DevRelOS, an AI Developer Relations platform.

Your task is to analyze a developer's natural language query and extract structured intent.

You MUST respond with ONLY valid JSON – no preamble, no markdown fences.

Available API providers and their common actions:
- stripe: create_payment_intent, create_charge, list_charges, retrieve_charge, create_customer, list_customers, create_refund, list_payment_intents
- twilio: send_sms, list_messages, make_call, list_calls
- github: get_authenticated_user, list_repos, create_repo, create_issue, list_issues, get_repo

Currency conversions: always convert dollar amounts to cents (e.g. "$50" → 5000).

Output JSON schema:
{
  "action": "<verb: create|list|retrieve|delete|send|charge|refund|call|get>",
  "resource": "<noun: payment|charge|customer|message|sms|call|repo|issue|user>",
  "parameters": {
    "<key>": "<value>"
  },
  "api_provider": "<stripe|twilio|github|unknown>",
  "endpoint_key": "<exact endpoint key from the list above or null>",
  "confidence": <0.0-1.0>,
  "intent_summary": "<one sentence summary of what the user wants to do>"
}
"""


async def run(query: str, session_history: List[Dict] = None, schema_context: str = "") -> Dict:
    """
    Parse a natural language query into structured intent.
    Uses cache to avoid redundant LLM calls for identical queries.
    """
    # Check cache first
    cached = await get_cached_intent(query)
    if cached:
        return cached

    history_text = ""
    if session_history:
        recent = session_history[-3:]  # last 3 interactions
        history_text = "\n\nRecent session context:\n" + "\n".join(
            f"- Q: {h.get('query','')} → provider: {h.get('api_provider','')}"
            for h in recent
        )

    user_message = f"""Parse this developer query into structured intent:

Query: "{query}"
{history_text}
{f"Additional API context:{schema_context}" if schema_context else ""}

Return ONLY the JSON object."""

    result = await structured_completion(
        messages    = [{"role": "user", "content": user_message}],
        system      = SYSTEM_PROMPT,
        temperature = 0.1,
        max_tokens  = 512,
    )

    # Ensure required fields
    result.setdefault("action",        "unknown")
    result.setdefault("resource",      "unknown")
    result.setdefault("parameters",    {})
    result.setdefault("api_provider",  "unknown")
    result.setdefault("endpoint_key",  None)
    result.setdefault("confidence",    0.5)
    result.setdefault("intent_summary", query)
    result["raw_query"] = query

    await set_cached_intent(query, result)
    return result
