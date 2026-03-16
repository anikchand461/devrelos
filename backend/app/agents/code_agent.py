"""
Code Generation Agent
─────────────────────
Produces idiomatic, production-quality API integration code
in Node.js, Python, and Go from an ExtractedIntent.
"""
from __future__ import annotations
import json

from openai import AsyncOpenAI
from app.core.config import settings
from app.models.schemas import ExtractedIntent

CODE_GEN_SYSTEM_PROMPT = """You are a senior software engineer writing idiomatic API integration code.
Given an API intent, produce clean, production-ready code snippets.

Rules:
- Use the official SDK if one exists (e.g. stripe for Stripe, openai for OpenAI)
- Fall back to fetch/requests/net/http if no SDK exists
- Include proper error handling
- Use environment variables for secrets (process.env.API_KEY, os.environ["API_KEY"])
- Include a comment at the top explaining what the code does
- Keep it concise — no unnecessary boilerplate

Respond ONLY with valid JSON:
{
  "javascript": "<complete Node.js/JavaScript code>",
  "python": "<complete Python code>",
  "go": "<complete Go code>"
}
"""

# Fallback templates for when LLM is unavailable (demo mode)
TEMPLATES = {
    "javascript": """\
// {description}
const response = await fetch('{url}', {{
  method: '{method}',
  headers: {{
    'Authorization': `Bearer ${{process.env.API_KEY}}`,
    'Content-Type': 'application/json',
  }},
  {body_line}
}});

if (!response.ok) {{
  const error = await response.json();
  throw new Error(`API error ${{response.status}}: ${{JSON.stringify(error)}}`);
}}

const data = await response.json();
console.log(data);
""",
    "python": """\
# {description}
import os
import httpx

response = httpx.{method_lower}(
    "{url}",
    headers={{
        "Authorization": f"Bearer {{os.environ['API_KEY']}}",
        "Content-Type": "application/json",
    }},
    {py_body_line}
)
response.raise_for_status()
data = response.json()
print(data)
""",
    "go": """\
// {description}
package main

import (
    "encoding/json"
    "fmt"
    "net/http"
    "os"
    "strings"
)

func main() {{
    body := strings.NewReader(`{body_json}`)
    req, _ := http.NewRequest("{method}", "{url}", body)
    req.Header.Set("Authorization", "Bearer " + os.Getenv("API_KEY"))
    req.Header.Set("Content-Type", "application/json")

    client := &http.Client{{}}
    resp, err := client.Do(req)
    if err != nil {{ panic(err) }}
    defer resp.Body.Close()

    var result map[string]interface{{}}
    json.NewDecoder(resp.Body).Decode(&result)
    fmt.Println(result)
}}
""",
}


class CodeGenerationAgent:
    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = settings.OPENAI_MODEL

    async def generate_snippets(
        self,
        intent: ExtractedIntent,
        languages: list[str] | None = None,
    ) -> dict[str, str]:
        """
        Generate code snippets for the given intent.

        Falls back to templates if LLM is unavailable.
        """
        languages = languages or ["javascript", "python", "go"]

        try:
            return await self._llm_generate(intent, languages)
        except Exception:
            return self._template_generate(intent, languages)

    async def _llm_generate(
        self,
        intent: ExtractedIntent,
        languages: list[str],
    ) -> dict[str, str]:
        context = {
            "api": intent.api_name,
            "endpoint": intent.endpoint_path,
            "method": intent.http_method,
            "parameters": intent.parameters,
            "auth_type": intent.auth_type,
            "description": intent.description,
            "goal": intent.goal,
        }

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": CODE_GEN_SYSTEM_PROMPT},
                {"role": "user", "content": json.dumps(context)},
            ],
            response_format={"type": "json_object"},
            temperature=0.2,
        )

        raw = json.loads(response.choices[0].message.content)
        return {lang: raw.get(lang, "") for lang in languages}

    def _template_generate(
        self,
        intent: ExtractedIntent,
        languages: list[str],
    ) -> dict[str, str]:
        """Deterministic fallback using string templates."""
        body_json = json.dumps(intent.parameters, indent=2) if intent.parameters else ""
        base_url = f"https://api.{intent.api_name}.com"
        url = f"{base_url}{intent.endpoint_path}"

        result = {}
        for lang in languages:
            tmpl = TEMPLATES.get(lang, "")
            result[lang] = tmpl.format(
                description=intent.description or intent.goal,
                url=url,
                method=intent.http_method,
                method_lower=intent.http_method.lower(),
                body_line=f"body: JSON.stringify({body_json})," if body_json else "",
                py_body_line=f"json={body_json}," if body_json else "",
                body_json=body_json,
            )
        return result
