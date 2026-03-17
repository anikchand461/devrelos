"""
agents/docs_agent.py – Documentation Generator Agent
Generates human-readable documentation for API endpoints.
"""

import json
from typing import Any, Dict, List, Optional
from services.groq_client import chat_completion

SYSTEM_PROMPT = """You are a Documentation Generator Agent for DevRelOS.

You write clear, developer-friendly API documentation in Markdown.

Your docs must include:
1. Overview / description
2. Authentication requirements
3. Request parameters (with types, required status, descriptions)
4. Request example (curl + JSON body)
5. Response example
6. Common errors and how to handle them
7. Related endpoints

Write for a junior developer who is integrating this API for the first time.
Be specific, practical, and concise.
"""


async def run(
    provider:     str,
    endpoint_key: str,
    schema:       Dict,
    base_url:     str,
) -> str:
    """Generate Markdown documentation for a specific API endpoint."""
    endpoints = schema.get("endpoints", {})
    endpoint  = endpoints.get(endpoint_key, {})

    if not endpoint:
        # Generate general provider docs
        return await _generate_provider_docs(provider, schema, base_url)

    user_message = f"""Generate complete documentation for this API endpoint:

Provider:     {provider}
Endpoint Key: {endpoint_key}
Base URL:     {base_url}

Endpoint Definition:
{json.dumps(endpoint, indent=2)}

Full Schema Context:
{json.dumps(schema, indent=2)}

Write detailed Markdown documentation."""

    return await chat_completion(
        messages    = [{"role": "user", "content": user_message}],
        system      = SYSTEM_PROMPT,
        temperature = 0.3,
        max_tokens  = 2048,
    )


async def _generate_provider_docs(provider: str, schema: Dict, base_url: str) -> str:
    """Generate overview documentation for an entire provider."""
    user_message = f"""Generate a comprehensive overview of this API provider:

Provider:  {provider}
Base URL:  {base_url}
Schema:    {json.dumps(schema, indent=2)}

Write a complete Markdown overview covering all endpoints."""

    return await chat_completion(
        messages    = [{"role": "user", "content": user_message}],
        system      = SYSTEM_PROMPT,
        temperature = 0.3,
        max_tokens  = 3000,
    )


async def generate_from_response(
    provider:      str,
    endpoint_key:  str,
    request_data:  Dict,
    response_data: Any,
    success:       bool,
) -> str:
    """Generate documentation based on actual request/response."""
    user_message = f"""Generate inline documentation for this API interaction:

Provider:  {provider}
Endpoint:  {endpoint_key}
Success:   {success}

Request:
{json.dumps(request_data, indent=2)}

Response:
{json.dumps(response_data, indent=2) if isinstance(response_data, dict) else str(response_data)}

Write a concise explanation of what happened and what the response fields mean."""

    return await chat_completion(
        messages    = [{"role": "user", "content": user_message}],
        system      = SYSTEM_PROMPT,
        temperature = 0.3,
        max_tokens  = 1024,
    )
