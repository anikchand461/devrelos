"""
Debugging Agent
───────────────
Analyzes failed API requests, identifies root cause,
and generates a corrected request the developer can run immediately.
"""
from __future__ import annotations
import json

from openai import AsyncOpenAI
from app.core.config import settings
from app.models.schemas import (
    APIError, ExtractedIntent,
    DebugResponse, DebugFix, ErrorSeverity
)

# Known error patterns for fast-path diagnosis (no LLM needed)
ERROR_PATTERNS = {
    401: {
        "type": "authentication_error",
        "severity": ErrorSeverity.HIGH,
        "cause": "Missing or invalid authentication credentials",
        "fix_hint": "Check that your API key or bearer token is set correctly in the Authorization header",
    },
    403: {
        "type": "authorization_error",
        "severity": ErrorSeverity.HIGH,
        "cause": "Your credentials are valid but you don't have permission for this resource",
        "fix_hint": "Verify your API key has the required scopes/permissions for this endpoint",
    },
    404: {
        "type": "not_found_error",
        "severity": ErrorSeverity.MEDIUM,
        "cause": "The requested endpoint or resource does not exist",
        "fix_hint": "Check the endpoint path for typos and verify the resource ID exists",
    },
    422: {
        "type": "validation_error",
        "severity": ErrorSeverity.MEDIUM,
        "cause": "Request body failed server-side validation",
        "fix_hint": "Review the required fields in the request body — a field may be missing or the wrong type",
    },
    429: {
        "type": "rate_limit_error",
        "severity": ErrorSeverity.LOW,
        "cause": "You have exceeded the API rate limit",
        "fix_hint": "Wait before retrying, or implement exponential backoff in your integration",
    },
    500: {
        "type": "server_error",
        "severity": ErrorSeverity.CRITICAL,
        "cause": "The API server encountered an internal error",
        "fix_hint": "This is likely transient — retry with exponential backoff. If persistent, check the API status page",
    },
}

DEBUG_SYSTEM_PROMPT = """You are a senior API integration engineer and debugger.
A developer received an API error. Diagnose it precisely and provide a concrete fix.

Respond ONLY with valid JSON:
{
  "error_type": "<authentication_error|validation_error|not_found_error|rate_limit_error|server_error|other>",
  "severity": "<low|medium|high|critical>",
  "root_cause": "<1-2 sentence precise explanation>",
  "fix": {
    "description": "<what to change>",
    "corrected_headers": {"key": "value"},
    "corrected_body": "<corrected JSON string or null>",
    "corrected_url": "<corrected URL or null>",
    "explanation": "<step-by-step fix explanation>",
    "code_example": "<corrected code snippet>"
  },
  "confidence": 0.0 to 1.0
}
"""


class DebuggingAgent:
    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = settings.OPENAI_MODEL

    async def diagnose(
        self,
        error: APIError,
        original_intent: ExtractedIntent | None = None,
    ) -> DebugResponse:
        """
        Diagnose an API error and return a corrective fix.

        Uses a fast-path for well-known HTTP error codes,
        falling back to LLM analysis for complex cases.
        """
        from uuid import uuid4

        # Fast-path: known error pattern
        pattern = ERROR_PATTERNS.get(error.status_code)

        if pattern and error.status_code in (401, 429):
            # Simple errors we can fix without LLM
            return self._build_simple_fix(error, pattern)

        # LLM-powered diagnosis for complex errors
        return await self._llm_diagnose(error, original_intent, pattern)

    def _build_simple_fix(self, error: APIError, pattern: dict) -> DebugResponse:
        from uuid import uuid4

        if error.status_code == 401:
            fix = DebugFix(
                description="Add or correct the Authorization header",
                corrected_headers={
                    "Authorization": "Bearer {{API_KEY}}",
                    **{k: v for k, v in error.request_headers.items()
                       if k.lower() != "authorization"}
                },
                explanation=(
                    "Your request was rejected because the Authorization header is "
                    "missing or contains an invalid token. "
                    "Make sure {{API_KEY}} is set in your environment variables "
                    "and the header is formatted as: `Authorization: Bearer <your_key>`"
                ),
                code_example=(
                    "// Node.js fix:\n"
                    "const response = await fetch('" + error.request_url + "', {\n"
                    "  method: '" + error.request_method + "',\n"
                    "  headers: {\n"
                    "    'Authorization': `Bearer ${process.env.API_KEY}`,\n"
                    "    'Content-Type': 'application/json',\n"
                    "  },\n"
                    "});"
                ),
            )
        else:
            fix = DebugFix(
                description=pattern["fix_hint"],
                explanation=pattern["fix_hint"],
            )

        return DebugResponse(
            session_id=uuid4(),
            error_type=pattern["type"],
            severity=pattern["severity"],
            root_cause=pattern["cause"],
            fix=fix,
            confidence=0.95,
        )

    async def _llm_diagnose(
        self,
        error: APIError,
        original_intent: ExtractedIntent | None,
        pattern: dict | None,
    ) -> DebugResponse:
        from uuid import uuid4

        context = {
            "status_code": error.status_code,
            "request_url": error.request_url,
            "request_method": error.request_method,
            "request_headers": error.request_headers,
            "request_body": error.request_body,
            "response_body": error.response_body[:2000],  # Truncate large responses
        }
        if original_intent:
            context["original_intent"] = {
                "goal": original_intent.goal,
                "endpoint": original_intent.endpoint_path,
                "expected_params": original_intent.parameters,
            }

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": DEBUG_SYSTEM_PROMPT},
                {"role": "user", "content": json.dumps(context)},
            ],
            response_format={"type": "json_object"},
            temperature=0.1,
        )

        raw = json.loads(response.choices[0].message.content)
        fix_data = raw.get("fix", {})

        return DebugResponse(
            session_id=uuid4(),
            error_type=raw.get("error_type", "unknown"),
            severity=ErrorSeverity(raw.get("severity", "medium")),
            root_cause=raw.get("root_cause", "Unknown error"),
            fix=DebugFix(
                description=fix_data.get("description", ""),
                corrected_headers=fix_data.get("corrected_headers", {}),
                corrected_body=fix_data.get("corrected_body"),
                corrected_url=fix_data.get("corrected_url"),
                explanation=fix_data.get("explanation", ""),
                code_example=fix_data.get("code_example"),
            ),
            confidence=float(raw.get("confidence", 0.75)),
        )
