"""
agents/tutorial_agent.py – Tutorial Generator Agent
Generates step-by-step integration tutorials.
"""

import json
from typing import Any, Dict, List, Optional
from services.groq_client import structured_completion

SYSTEM_PROMPT = """You are a Tutorial Generator Agent for DevRelOS.

You create practical, step-by-step developer tutorials for integrating APIs.

You MUST respond with ONLY valid JSON – no preamble, no markdown fences.

Output JSON schema:
{
  "title":       "<tutorial title>",
  "description": "<brief description of what the developer will achieve>",
  "prerequisites": ["<prereq 1>", "<prereq 2>"],
  "estimated_time": "<e.g. 10 minutes>",
  "steps": [
    {
      "step": 1,
      "title": "<step title>",
      "description": "<detailed step description>",
      "code": {
        "language": "<python|javascript|curl|bash>",
        "snippet": "<code snippet>"
      },
      "tips": ["<tip 1>"]
    }
  ],
  "code_examples": [
    {
      "title": "<example title>",
      "language": "<language>",
      "code": "<full code example>"
    }
  ],
  "next_steps": ["<next step 1>", "<next step 2>"],
  "common_pitfalls": ["<pitfall 1>"]
}

Write for a developer who wants to get something working quickly. Include real code.
"""


async def run(
    provider: str,
    goal:     str,
    schema:   Dict,
    base_url: str,
) -> Dict:
    """Generate a step-by-step tutorial for a developer goal."""
    endpoints_summary = json.dumps(
        {k: {"path": v["path"], "method": v["method"], "description": v["description"]}
         for k, v in schema.get("endpoints", {}).items()},
        indent=2
    )

    user_message = f"""Create a tutorial for:

Provider: {provider}
Goal:     {goal}
Base URL: {base_url}

Available endpoints:
{endpoints_summary}

Generate a complete step-by-step tutorial with working code examples."""

    result = await structured_completion(
        messages    = [{"role": "user", "content": user_message}],
        system      = SYSTEM_PROMPT,
        temperature = 0.4,
        max_tokens  = 3000,
    )

    result.setdefault("title",          f"How to use {provider}")
    result.setdefault("steps",          [])
    result.setdefault("code_examples",  [])
    result.setdefault("next_steps",     [])
    return result
