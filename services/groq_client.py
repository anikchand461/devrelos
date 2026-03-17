"""
services/groq_client.py – Async Groq API client singleton
"""

import os
import json
import re
from typing import Any, Dict, List, Optional
from groq import AsyncGroq
from dotenv import load_dotenv

load_dotenv()

_client: Optional[AsyncGroq] = None
_MODEL  = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")


def get_client() -> AsyncGroq:
    global _client
    if _client is None:
        api_key = os.getenv("GROQ_API_KEY", "")
        if not api_key:
            raise RuntimeError("GROQ_API_KEY not set in environment")
        _client = AsyncGroq(api_key=api_key)
    return _client


async def chat_completion(
    messages:    List[Dict],
    system:      Optional[str] = None,
    temperature: float = 0.2,
    max_tokens:  int   = 2048,
    model:       Optional[str] = None,
) -> str:
    """Single call returning the assistant message text."""
    client = get_client()
    full_messages = []
    if system:
        full_messages.append({"role": "system", "content": system})
    full_messages.extend(messages)

    response = await client.chat.completions.create(
        model       = model or _MODEL,
        messages    = full_messages,
        temperature = temperature,
        max_tokens  = max_tokens,
    )
    return response.choices[0].message.content.strip()


async def structured_completion(
    messages:    List[Dict],
    system:      Optional[str] = None,
    temperature: float = 0.1,
    max_tokens:  int   = 2048,
    model:       Optional[str] = None,
) -> Dict:
    """Call Groq and parse the response as JSON. Returns dict."""
    text = await chat_completion(messages, system, temperature, max_tokens, model)
    return _parse_json(text)


def _parse_json(text: str) -> Dict:
    """Robustly extract JSON from LLM response."""
    # Try direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try stripping markdown fences
    cleaned = re.sub(r"```(?:json)?\s*", "", text).strip().rstrip("`").strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # Find first JSON object or array
    match = re.search(r"(\{[\s\S]*\}|\[[\s\S]*\])", text)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass

    # Return raw as error
    return {"error": "Failed to parse JSON", "raw": text}
