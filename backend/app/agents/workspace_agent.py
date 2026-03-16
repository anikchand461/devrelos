"""
Workspace Generation Agent
──────────────────────────
Converts an ExtractedIntent into a fully-configured Requestly collection:
- Correct endpoint URL
- Authentication headers
- Request body with realistic example values
- Environment variable placeholders
- Pre-request validation script
- Post-response assertion script
"""
from __future__ import annotations
import json
import uuid

from app.models.schemas import (
    ExtractedIntent,
    Requestly Collection,
    Requestly Request,
    RequestHeader,
    EnvironmentVariable,
    RequestAssertion,
)

# Per-API base URLs and auth patterns
API_CONFIGS: dict[str, dict] = {
    "stripe": {
        "base_url": "https://api.stripe.com",
        "auth_type": "basic",
        "auth_header": "Authorization",
        "auth_value": "Basic {{STRIPE_SECRET_KEY}}:",  # Stripe uses basic auth with key as username
        "env_vars": [
            {"key": "STRIPE_SECRET_KEY", "value": "sk_test_...", "is_secret": True},
        ],
    },
    "twilio": {
        "base_url": "https://api.twilio.com",
        "auth_type": "basic",
        "auth_header": "Authorization",
        "auth_value": "Basic {{TWILIO_AUTH_TOKEN}}",
        "env_vars": [
            {"key": "TWILIO_ACCOUNT_SID", "value": "ACxxxxxxxx", "is_secret": False},
            {"key": "TWILIO_AUTH_TOKEN", "value": "your_auth_token", "is_secret": True},
        ],
    },
    "github": {
        "base_url": "https://api.github.com",
        "auth_type": "bearer",
        "auth_header": "Authorization",
        "auth_value": "Bearer {{GITHUB_TOKEN}}",
        "env_vars": [
            {"key": "GITHUB_TOKEN", "value": "ghp_...", "is_secret": True},
        ],
    },
    "openai": {
        "base_url": "https://api.openai.com",
        "auth_type": "bearer",
        "auth_header": "Authorization",
        "auth_value": "Bearer {{OPENAI_API_KEY}}",
        "env_vars": [
            {"key": "OPENAI_API_KEY", "value": "sk-...", "is_secret": True},
        ],
    },
    # Default fallback
    "default": {
        "base_url": "https://api.example.com",
        "auth_type": "bearer",
        "auth_header": "Authorization",
        "auth_value": "Bearer {{API_KEY}}",
        "env_vars": [
            {"key": "API_KEY", "value": "your_api_key", "is_secret": True},
            {"key": "BASE_URL", "value": "https://api.example.com", "is_secret": False},
        ],
    },
}

PRE_REQUEST_SCRIPT = """
// Pre-request: validate required environment variables
const required = {required_vars};
const missing = required.filter(v => !pm.environment.get(v));
if (missing.length > 0) {{
    throw new Error(`Missing required env vars: ${{missing.join(', ')}}`);
}}
console.log('✅ Environment validated');
"""

POST_RESPONSE_SCRIPT = """
// Post-response: validate response
pm.test('Status code is 2xx', () => {{
    pm.expect(pm.response.code).to.be.within(200, 299);
}});

pm.test('Response is valid JSON', () => {{
    pm.response.json();
}});

// Store response ID for chained requests
const body = pm.response.json();
if (body.id) {{
    pm.environment.set('LAST_RESPONSE_ID', body.id);
    console.log('Stored response ID:', body.id);
}}

console.log('Response time:', pm.response.responseTime + 'ms');
"""


class WorkspaceGenerationAgent:

    async def generate(
        self,
        intent: ExtractedIntent,
        include_tests: bool = True,
    ) -> Requestly Collection:
        """
        Generate a complete Requestly collection for the given intent.
        """
        api_config = API_CONFIGS.get(intent.api_name.lower(), API_CONFIGS["default"])
        base_url = api_config["base_url"]
        full_url = f"{base_url}{intent.endpoint_path}"

        # Build headers
        headers = [
            RequestHeader(key="Content-Type", value="application/json"),
            RequestHeader(
                key=api_config["auth_header"],
                value=api_config["auth_value"],
            ),
        ]

        # Build environment variables
        env_vars = [
            EnvironmentVariable(**ev) for ev in api_config["env_vars"]
        ]
        env_vars.append(
            EnvironmentVariable(key="BASE_URL", value=base_url, is_secret=False)
        )

        # Build request body from intent parameters
        body = None
        if intent.http_method in ("POST", "PUT", "PATCH") and intent.parameters:
            body = json.dumps(intent.parameters, indent=2)

        # Build assertions
        assertions = [
            RequestAssertion(
                type="status_code",
                target="status",
                expected="200",
                operator="is_in_range_2xx",
            )
        ]

        # Build pre/post scripts
        required_var_names = [ev.key for ev in env_vars if ev.is_secret]
        pre_script = PRE_REQUEST_SCRIPT.format(
            required_vars=json.dumps(required_var_names)
        ) if include_tests else ""
        post_script = POST_RESPONSE_SCRIPT if include_tests else ""

        request = Requestly Request(
            id=str(uuid.uuid4()),
            name=f"{intent.http_method} {intent.endpoint_path}",
            method=intent.http_method,
            url=full_url,
            headers=headers,
            body=body,
            body_type="json" if body else "raw",
            pre_request_script=pre_script,
            post_response_script=post_script,
            assertions=assertions,
        )

        return Requestly Collection(
            name=f"{intent.api_name.title()} — {intent.goal[:50]}",
            description=intent.description,
            variables=env_vars,
            requests=[request],
            auth={
                "type": api_config["auth_type"],
                "header": api_config["auth_header"],
                "value": api_config["auth_value"],
            },
        )
