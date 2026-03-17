"""
agents/workflow_agent.py – Workflow Generator Agent
Builds a complete, ready-to-execute API request from an API mapping
"""

import json
from typing import Any, Dict, List
from services.groq_client import structured_completion

SYSTEM_PROMPT = """You are a Workflow Generator Agent for DevRelOS.

Given an API mapping, produce a complete, executable API request workflow.

You MUST respond with ONLY valid JSON – no preamble, no markdown fences.

Output JSON schema:
{
  "workflow_id":    "<uuid-style short id>",
  "title":          "<human-readable title>",
  "description":    "<what this workflow does>",
  "steps": [
    {
      "step":        1,
      "title":       "<step title>",
      "description": "<what this step does>",
      "request": {
        "method":       "<HTTP method>",
        "url":          "<full URL>",
        "headers":      {"<key>": "<value>"},
        "query_params": {"<key>": "<value>"},
        "body":         {"<key>": "<value>"}
      }
    }
  ],
  "primary_request": {
    "method":       "<HTTP method>",
    "url":          "<full URL>",
    "headers":      {"Content-Type": "<content_type>"},
    "query_params": {},
    "body":         {}
  },
  "curl_example":   "<curl command>",
  "notes":          "<any important notes>"
}

Rules:
- headers must include Content-Type if body is present
- Do NOT include Authorization headers (filled by auth agent)
- query_params for GET, body for POST/PUT/PATCH
- curl_example must be a complete, valid curl command with placeholder for API key
- For Stripe form-encoded requests: body should use key=value& format shown in curl, but JSON in body field
"""


async def run(api_mapping: Dict, intent: Dict) -> Dict:
    """Build complete workflow from API mapping."""
    user_message = f"""Generate a complete API request workflow:

API Mapping:
{json.dumps(api_mapping, indent=2)}

Original Intent:
{json.dumps(intent, indent=2)}

Produce the workflow JSON with a curl example."""

    result = await structured_completion(
        messages    = [{"role": "user", "content": user_message}],
        system      = SYSTEM_PROMPT,
        temperature = 0.15,
        max_tokens  = 1500,
    )

    # Ensure structure
    result.setdefault("steps",           [])
    result.setdefault("primary_request", {})
    result.setdefault("description",     "")
    return result
