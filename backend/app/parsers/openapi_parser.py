"""
OpenAPI Spec Parsing Engine
────────────────────────────
Ingests OpenAPI 3.x / Swagger 2.x specifications and converts
them into a normalized list of endpoint dicts ready for vector indexing.
"""
from __future__ import annotations
import json
import re
from typing import Any

import yaml
import httpx


class OpenAPIParser:
    """
    Parse an OpenAPI spec (URL or raw string) into normalized endpoint records.
    """

    async def from_url(self, url: str) -> list[dict]:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            content = response.text
        return self.from_string(content)

    def from_string(self, content: str) -> list[dict]:
        """Parse raw YAML or JSON spec string."""
        try:
            spec = json.loads(content)
        except json.JSONDecodeError:
            spec = yaml.safe_load(content)
        return self._parse(spec)

    def _parse(self, spec: dict) -> list[dict]:
        version = spec.get("openapi") or spec.get("swagger", "")
        if version.startswith("3"):
            return self._parse_v3(spec)
        elif version.startswith("2"):
            return self._parse_v2(spec)
        raise ValueError(f"Unsupported OpenAPI version: {version}")

    def _parse_v3(self, spec: dict) -> list[dict]:
        endpoints = []
        paths = spec.get("paths", {})
        components = spec.get("components", {})

        for path, path_item in paths.items():
            for method in ("get", "post", "put", "patch", "delete", "options"):
                op = path_item.get(method)
                if not op:
                    continue

                # Resolve request body schema
                request_schema = None
                rb = op.get("requestBody", {})
                content = rb.get("content", {})
                if "application/json" in content:
                    schema_ref = content["application/json"].get("schema", {})
                    request_schema = self._resolve_ref(schema_ref, components)

                # Resolve response schemas
                responses = {}
                for status, resp in op.get("responses", {}).items():
                    resp_content = resp.get("content", {})
                    if "application/json" in resp_content:
                        resp_schema = resp_content["application/json"].get("schema", {})
                        responses[status] = self._resolve_ref(resp_schema, components)

                endpoints.append({
                    "path": path,
                    "method": method.upper(),
                    "summary": op.get("summary", ""),
                    "description": op.get("description", ""),
                    "tags": op.get("tags", []),
                    "parameters": self._parse_params(op.get("parameters", []), components),
                    "request_body_schema": request_schema,
                    "response_schema": responses,
                    "auth_required": self._requires_auth(op),
                    "operation_id": op.get("operationId", ""),
                })

        return endpoints

    def _parse_v2(self, spec: dict) -> list[dict]:
        """Swagger 2.x support — converts to same normalized format."""
        endpoints = []
        paths = spec.get("paths", {})
        definitions = spec.get("definitions", {})

        for path, path_item in paths.items():
            for method in ("get", "post", "put", "patch", "delete"):
                op = path_item.get(method)
                if not op:
                    continue

                endpoints.append({
                    "path": path,
                    "method": method.upper(),
                    "summary": op.get("summary", ""),
                    "description": op.get("description", ""),
                    "tags": op.get("tags", []),
                    "parameters": self._parse_params_v2(op.get("parameters", []), definitions),
                    "request_body_schema": None,
                    "response_schema": {},
                    "auth_required": bool(op.get("security")),
                    "operation_id": op.get("operationId", ""),
                })

        return endpoints

    def _parse_params(self, params: list, components: dict) -> list[dict]:
        result = []
        for p in params:
            p = self._resolve_ref(p, components)
            result.append({
                "name": p.get("name", ""),
                "in": p.get("in", "query"),     # query | path | header | cookie
                "required": p.get("required", False),
                "description": p.get("description", ""),
                "schema": p.get("schema", {}),
            })
        return result

    def _parse_params_v2(self, params: list, definitions: dict) -> list[dict]:
        result = []
        for p in params:
            result.append({
                "name": p.get("name", ""),
                "in": p.get("in", "query"),
                "required": p.get("required", False),
                "description": p.get("description", ""),
                "schema": {"type": p.get("type", "string")},
            })
        return result

    def _resolve_ref(self, schema: dict, components: dict) -> dict:
        """Resolve $ref pointers within the spec."""
        if not isinstance(schema, dict):
            return schema
        ref = schema.get("$ref")
        if not ref:
            return schema

        # Extract the ref name: "#/components/schemas/PaymentIntent" → PaymentIntent
        parts = ref.lstrip("#/").split("/")
        node = {"components": components}
        try:
            for part in parts[1:]:   # Skip "components"
                node = node[part]
            return node
        except (KeyError, TypeError):
            return schema

    def _requires_auth(self, op: dict) -> bool:
        """Check if operation requires authentication."""
        # If security is explicitly empty list [], auth is not required
        security = op.get("security")
        if security is not None:
            return len(security) > 0
        return True  # Default: assume auth required


def generate_example_value(schema: dict) -> Any:
    """
    Generate a realistic example value from a JSON Schema definition.
    Used for pre-populating request bodies.
    """
    if not schema:
        return None

    schema_type = schema.get("type", "string")
    example = schema.get("example")
    if example is not None:
        return example

    enum = schema.get("enum")
    if enum:
        return enum[0]

    if schema_type == "string":
        fmt = schema.get("format", "")
        if fmt == "uuid":
            return "550e8400-e29b-41d4-a716-446655440000"
        if fmt == "email":
            return "developer@example.com"
        if fmt == "date-time":
            return "2024-01-15T10:30:00Z"
        return schema.get("description", "string_value")[:20].replace(" ", "_").lower()

    if schema_type == "integer":
        return schema.get("minimum", 1)

    if schema_type == "number":
        return schema.get("minimum", 1.0)

    if schema_type == "boolean":
        return True

    if schema_type == "array":
        items = schema.get("items", {})
        return [generate_example_value(items)]

    if schema_type == "object":
        props = schema.get("properties", {})
        return {k: generate_example_value(v) for k, v in list(props.items())[:5]}

    return None
