"""
agents/auth_agent.py – Auth Injection Agent
Injects the correct authentication from environment variables into API requests.
No hardcoding: all keys are read from .env via os.getenv.
"""

import os
import base64
from typing import Dict, Optional
from dotenv import load_dotenv

load_dotenv()

# ── Auth strategy per provider ────────────────────────────────────────────────

def _stripe_auth() -> Dict[str, str]:
    """Stripe: HTTP Basic Auth – secret key as username, empty password."""
    key = os.getenv("STRIPE_SECRET_KEY", "")
    if not key:
        return {}
    token = base64.b64encode(f"{key}:".encode()).decode()
    return {"Authorization": f"Basic {token}"}


def _twilio_auth() -> Dict[str, str]:
    """Twilio: HTTP Basic Auth – AccountSid:AuthToken."""
    sid   = os.getenv("TWILIO_ACCOUNT_SID", "")
    token = os.getenv("TWILIO_AUTH_TOKEN",  "")
    if not sid or not token:
        return {}
    encoded = base64.b64encode(f"{sid}:{token}".encode()).decode()
    return {"Authorization": f"Basic {encoded}"}


def _github_auth() -> Dict[str, str]:
    """GitHub: Bearer token."""
    token = os.getenv("GITHUB_TOKEN", "")
    if not token:
        return {}
    return {
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def _bearer_auth(env_var: str) -> Dict[str, str]:
    """Generic Bearer token from env var."""
    token = os.getenv(env_var, "")
    if not token:
        return {}
    return {"Authorization": f"Bearer {token}"}


_AUTH_STRATEGIES = {
    "stripe":        _stripe_auth,
    "twilio":        _twilio_auth,
    "twilio_basic":  _twilio_auth,
    "github":        _github_auth,
}


def _resolve_twilio_url(url: str) -> str:
    """Replace {AccountSid} placeholder in Twilio URLs."""
    sid = os.getenv("TWILIO_ACCOUNT_SID", "")
    return url.replace("{AccountSid}", sid) if sid else url


def _resolve_twilio_body(body: Dict) -> Dict:
    """Twilio From number default if not set."""
    if body and "From" not in body:
        default_from = os.getenv("TWILIO_FROM_NUMBER", "")
        if default_from:
            body = {**body, "From": default_from}
    return body


def inject(
    provider:     str,
    url:          str,
    headers:      Dict[str, str],
    body:         Optional[Dict],
    auth_type:    str = "bearer",
    env_key_name: Optional[str] = None,
) -> Dict:
    """
    Inject authentication and resolve dynamic placeholders.
    Returns updated {url, headers, body}.
    """
    headers = dict(headers or {})

    # Resolve provider-specific auth
    strategy = _AUTH_STRATEGIES.get(provider) or _AUTH_STRATEGIES.get(auth_type)
    if strategy:
        auth_headers = strategy()
        headers.update(auth_headers)
    elif env_key_name:
        # Fallback: generic bearer from env_key_name
        token = os.getenv(env_key_name, "")
        if token:
            headers["Authorization"] = f"Bearer {token}"

    # GitHub: always include Accept header
    if provider == "github":
        headers.setdefault("Accept", "application/vnd.github+json")

    # Twilio: resolve {AccountSid} in URL
    if provider in ("twilio", "twilio_basic"):
        url = _resolve_twilio_url(url)
        if body:
            body = _resolve_twilio_body(body)

    return {"url": url, "headers": headers, "body": body}


def has_credentials(provider: str) -> bool:
    """Check whether the required credentials are configured."""
    checks = {
        "stripe":  ["STRIPE_SECRET_KEY"],
        "twilio":  ["TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN"],
        "github":  ["GITHUB_TOKEN"],
    }
    required = checks.get(provider, [])
    return all(bool(os.getenv(k)) for k in required)


def missing_credentials(provider: str) -> list:
    """Return list of missing env var names for a provider."""
    checks = {
        "stripe":  ["STRIPE_SECRET_KEY"],
        "twilio":  ["TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN"],
        "github":  ["GITHUB_TOKEN"],
    }
    required = checks.get(provider, [])
    return [k for k in required if not os.getenv(k)]
