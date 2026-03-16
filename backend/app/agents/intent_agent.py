"""
Developer Intent Agent
──────────────────────
Converts a developer's natural language goal into a structured
ExtractedIntent containing the correct API, endpoint, method,
parameters, and authentication type.
"""
from __future__ import annotations
import json

from openai import AsyncOpenAI
from app.core.config import settings
from app.models.schemas import ExtractedIntent

INTENT_SYSTEM_PROMPT = """You are a senior DevRel engineer and API expert.
Your job is to convert a developer's natural language goal into a precise
API call specification.

Given a goal like "charge a credit card $50", you extract:
- The API being used (stripe, twilio, github, etc.)
- The exact endpoint path and HTTP method
- All required parameters with example values
- The authentication type required

Respond ONLY with valid JSON matching this schema:
{
  "goal": "<original goal>",
  "api_name": "<api slug>",
  "endpoint_path": "<path like /v1/payment_intents>",
  "http_method": "<GET|POST|PUT|DELETE|PATCH>",
  "parameters": {
    "body": {"field": "example_value"},
    "query": {},
    "path": {}
  },
  "auth_type": "<bearer|api_key|basic|oauth2>",
  "description": "<one sentence explaining what this call does>",
  "confidence": 0.0 to 1.0
}

Use realistic, correct example values. For amounts use the API's expected
format (e.g. Stripe uses cents: 5000 for $50).
"""

class DeveloperIntentAgent:
    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = settings.OPENAI_MODEL

    async def extract(
        self,
        goal: str,
        api_slug: str | None = None,
        context: dict | None = None,
    ) -> ExtractedIntent:
        """
        Extract structured intent from natural language.

        Args:
            goal: Developer's NL goal, e.g. "charge a card $50"
            api_slug: Optional hint about which API to use
            context: Additional context (framework, prior messages, etc.)

        Returns:
            ExtractedIntent with all fields populated
        """
        user_message = f"Goal: {goal}"
        if api_slug:
            user_message += f"\nAPI: {api_slug}"
        if context:
            user_message += f"\nContext: {json.dumps(context)}"

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": INTENT_SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            response_format={"type": "json_object"},
            temperature=0.1,
        )

        raw = json.loads(response.choices[0].message.content)

        # Flatten parameters for the schema
        params = raw.get("parameters", {})
        flat_params = {
            **params.get("body", {}),
            **params.get("query", {}),
            **params.get("path", {}),
        }

        return ExtractedIntent(
            goal=raw["goal"],
            api_name=raw.get("api_name", api_slug or "unknown"),
            endpoint_path=raw.get("endpoint_path", "/"),
            http_method=raw.get("http_method", "POST").upper(),
            parameters=flat_params,
            auth_type=raw.get("auth_type", "bearer"),
            description=raw.get("description", ""),
            confidence=float(raw.get("confidence", 0.8)),
        )
