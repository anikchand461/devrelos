"""
agents/support_agent.py – Support Agent
Handles conversational developer support Q&A.
"""

from typing import Dict, List, Optional
from services.groq_client import chat_completion

SYSTEM_PROMPT = """You are a senior Developer Relations Engineer and support specialist for DevRelOS.

You help developers integrate APIs (Stripe, Twilio, GitHub, and others) by answering their questions clearly and practically.

Your style:
- Conversational, friendly, and direct
- Always include code examples when relevant
- Reference official documentation when appropriate
- Ask clarifying questions if the problem is ambiguous
- Point out common pitfalls proactively

Available integrations: Stripe (payments), Twilio (SMS/calls), GitHub (repos/issues).

Format your response in Markdown for readability.
"""


async def run(
    query:          str,
    session_history: List[Dict] = None,
    context:        Dict = None,
) -> str:
    """Handle a developer support question."""
    messages = []

    # Inject session history for continuity
    if session_history:
        for interaction in session_history[-5:]:
            q = interaction.get("query", "")
            r = interaction.get("response_json", {})
            if isinstance(r, dict):
                answer = r.get("explanation", r.get("content", ""))
            else:
                answer = str(r)[:200]
            if q:
                messages.append({"role": "user",      "content": q})
            if answer:
                messages.append({"role": "assistant", "content": answer})

    # Add context if available
    context_text = ""
    if context:
        provider = context.get("last_provider", "")
        if provider:
            context_text = f"\n\n[Context: User is working with the {provider} API]"

    messages.append({"role": "user", "content": query + context_text})

    return await chat_completion(
        messages    = messages,
        system      = SYSTEM_PROMPT,
        temperature = 0.5,
        max_tokens  = 1500,
    )
