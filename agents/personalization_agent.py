"""
agents/personalization_agent.py – Personalization Engine
Adjusts responses based on session history, skill level, and preferences.
"""

import json
from typing import Any, Dict, List, Optional
from services.groq_client import structured_completion

SYSTEM_PROMPT = """You are a Personalization Engine for DevRelOS.

Analyze a developer's session history and produce a personalization profile
that other agents can use to tailor their responses.

You MUST respond with ONLY valid JSON – no preamble, no markdown fences.

Output JSON schema:
{
  "skill_level":       "<beginner|intermediate|advanced>",
  "preferred_provider": "<most used provider or null>",
  "frequent_actions":  ["<action1>", "<action2>"],
  "preferred_language": "<python|javascript|curl|null>",
  "tone":              "<formal|casual|technical>",
  "context_hints":     ["<hint for next response>"],
  "suggestions":       ["<proactive suggestion 1>", "<proactive suggestion 2>"]
}
"""


async def run(session_history: List[Dict], current_query: str = "") -> Dict:
    """Build a personalization profile from session history."""
    if not session_history:
        return _default_profile()

    history_summary = []
    for interaction in session_history[-10:]:
        history_summary.append({
            "query":    interaction.get("query", ""),
            "provider": interaction.get("api_provider", ""),
            "endpoint": interaction.get("endpoint", ""),
            "status":   interaction.get("execution_status", ""),
        })

    user_message = f"""Analyze this developer's session history and produce a personalization profile:

Session History:
{json.dumps(history_summary, indent=2)}

Current Query: "{current_query}"

Infer skill level, preferences, and provide suggestions."""

    result = await structured_completion(
        messages    = [{"role": "user", "content": user_message}],
        system      = SYSTEM_PROMPT,
        temperature = 0.2,
        max_tokens  = 512,
    )

    result.setdefault("skill_level",        "intermediate")
    result.setdefault("preferred_provider", None)
    result.setdefault("frequent_actions",   [])
    result.setdefault("preferred_language", "curl")
    result.setdefault("tone",               "technical")
    result.setdefault("context_hints",      [])
    result.setdefault("suggestions",        [])
    return result


def _default_profile() -> Dict:
    return {
        "skill_level":        "intermediate",
        "preferred_provider": None,
        "frequent_actions":   [],
        "preferred_language": "curl",
        "tone":               "technical",
        "context_hints":      [],
        "suggestions": [
            "Try: 'Charge $50 to a customer'",
            "Try: 'Send an SMS to +1234567890'",
            "Try: 'Create a GitHub repository called my-project'",
        ]
    }
