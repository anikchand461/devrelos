"""
Pydantic schemas — all request/response shapes for DevRel-in-a-Box.
"""
from __future__ import annotations
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


# ─── Shared ──────────────────────────────────────────────

class SuccessResponse(BaseModel):
    ok: bool = True
    message: str = ""


# ─── Developer Session ───────────────────────────────────

class DeveloperSession(BaseModel):
    session_id: UUID = Field(default_factory=uuid4)
    developer_id: str | None = None
    framework: str | None = None          # "node", "python", "go", etc.
    experience_level: str = "intermediate" # "beginner" | "intermediate" | "advanced"
    api_slug: str | None = None            # which API they're working with


# ─── Intent ──────────────────────────────────────────────

class IntentRequest(BaseModel):
    goal: str = Field(..., description="Natural language goal, e.g. 'charge a card $50'")
    session_id: UUID | None = None
    api_slug: str | None = None
    context: dict[str, Any] = {}


class ExtractedIntent(BaseModel):
    goal: str
    api_name: str
    endpoint_path: str
    http_method: str
    parameters: dict[str, Any]
    auth_type: str                  # "bearer" | "api_key" | "basic" | "oauth2"
    description: str
    confidence: float


class IntentResponse(BaseModel):
    session_id: UUID
    intent: ExtractedIntent
    matched_endpoints: list[EndpointMatch]
    suggested_goal: str | None = None


class EndpointMatch(BaseModel):
    path: str
    method: str
    summary: str
    score: float


# ─── Workspace ───────────────────────────────────────────

class WorkspaceRequest(BaseModel):
    session_id: UUID
    intent: ExtractedIntent
    include_tests: bool = True
    target_language: str = "javascript"  # for code snippets


class RequestHeader(BaseModel):
    key: str
    value: str


class EnvironmentVariable(BaseModel):
    key: str
    value: str
    is_secret: bool = False


class RequestAssertion(BaseModel):
    type: str       # "status_code" | "json_path" | "header"
    target: str
    expected: str
    operator: str = "equals"


class Requestly Request(BaseModel):
    """Represents one request inside a Requestly collection."""
    id: str
    name: str
    method: str
    url: str
    headers: list[RequestHeader]
    body: str | None = None
    body_type: str = "json"         # "json" | "form" | "raw"
    pre_request_script: str = ""
    post_response_script: str = ""
    assertions: list[RequestAssertion] = []


class Requestly Collection(BaseModel):
    """Full Requestly collection — importable JSON."""
    version: str = "1.0"
    name: str
    description: str = ""
    variables: list[EnvironmentVariable]
    requests: list[Requestly Request]
    auth: dict[str, Any] = {}


class WorkspaceResponse(BaseModel):
    session_id: UUID
    collection: Requestly Collection
    collection_json: str           # serialized for direct import
    import_url: str | None = None  # deep-link to open in Requestly
    code_snippets: dict[str, str]  # language → code string


# ─── Debugging ───────────────────────────────────────────

class ErrorSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class APIError(BaseModel):
    status_code: int
    response_body: str
    request_url: str
    request_method: str
    request_headers: dict[str, str] = {}
    request_body: str | None = None


class DebugRequest(BaseModel):
    session_id: UUID
    error: APIError
    original_intent: ExtractedIntent | None = None


class DebugFix(BaseModel):
    description: str
    corrected_headers: dict[str, str] = {}
    corrected_body: str | None = None
    corrected_url: str | None = None
    explanation: str
    code_example: str | None = None


class DebugResponse(BaseModel):
    session_id: UUID
    error_type: str
    severity: ErrorSeverity
    root_cause: str
    fix: DebugFix
    confidence: float
    related_docs_url: str | None = None


# ─── Analytics ───────────────────────────────────────────

class TelemetryEvent(BaseModel):
    session_id: UUID
    event_type: str          # "intent_captured" | "workspace_generated" | "api_success" | "api_error"
    metadata: dict[str, Any] = {}
    timestamp: str | None = None


class FunnelStage(BaseModel):
    stage: str
    count: int
    conversion_rate: float


class ActivationMetrics(BaseModel):
    total_sessions: int
    funnel: list[FunnelStage]
    top_errors: list[dict[str, Any]]
    avg_time_to_first_success_seconds: float
    at_risk_sessions: list[UUID]


# ─── Ingest ──────────────────────────────────────────────

class IngestRequest(BaseModel):
    api_slug: str
    spec_url: str | None = None
    spec_content: str | None = None   # raw YAML/JSON string
    spec_format: str = "openapi"      # "openapi" | "postman" | "graphql"


class IngestResponse(BaseModel):
    api_slug: str
    endpoints_indexed: int
    schemas_indexed: int
    embedding_count: int
    status: str
