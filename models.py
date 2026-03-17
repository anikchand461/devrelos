"""
models.py – Pydantic v2 request/response models for DevRelOS
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from datetime import datetime


# ── Request Models ────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    query:      str              = Field(..., min_length=1, description="User's natural language query")
    session_id: Optional[str]   = Field(None, description="Session ID for continuity")
    mode:       Optional[str]   = Field("chat", description="chat | support | tutorial | docs")


class ExecuteRequest(BaseModel):
    session_id:   Optional[str]        = Field(None)
    api_provider: str                  = Field(..., description="e.g. stripe, twilio, github")
    endpoint:     str                  = Field(..., description="Endpoint key from schema")
    method:       str                  = Field(..., description="HTTP method")
    url:          str                  = Field(..., description="Full URL to call")
    headers:      Dict[str, str]       = Field(default_factory=dict)
    params:       Dict[str, Any]       = Field(default_factory=dict, description="Query params")
    body:         Optional[Dict[str, Any]] = Field(None, description="Request body")
    content_type: Optional[str]        = Field("application/json")
    original_query: Optional[str]      = Field(None)


class SchemaUpsertRequest(BaseModel):
    provider:     str        = Field(...)
    name:         str        = Field(...)
    base_url:     str        = Field(...)
    schema_json:  Dict       = Field(...)
    auth_type:    str        = Field("bearer")
    env_key_name: str        = Field(...)


class IntegrationRequest(BaseModel):
    channel:    str        = Field(..., description="slack | discord | email")
    message:    str        = Field(...)
    subject:    Optional[str] = Field(None, description="Email subject")
    to_email:   Optional[str] = Field(None, description="Recipient email")
    session_id: Optional[str] = Field(None)


# ── Intent / Agent Output Models ─────────────────────────────────────────────

class Intent(BaseModel):
    action:       str                    = Field(..., description="verb: create, list, retrieve, delete, send, charge …")
    resource:     str                    = Field(..., description="e.g. payment, customer, message, repo")
    parameters:   Dict[str, Any]         = Field(default_factory=dict)
    api_provider: str                    = Field(..., description="stripe | twilio | github | unknown")
    endpoint_key: Optional[str]          = Field(None)
    confidence:   float                  = Field(0.0, ge=0.0, le=1.0)
    raw_query:    Optional[str]          = Field(None)


class APIRequest(BaseModel):
    provider:     str                    = Field(...)
    endpoint_key: str                    = Field(...)
    method:       str                    = Field(...)
    url:          str                    = Field(...)
    headers:      Dict[str, str]         = Field(default_factory=dict)
    params:       Dict[str, Any]         = Field(default_factory=dict)
    body:         Optional[Dict[str, Any]] = Field(None)
    content_type: Optional[str]          = Field(None)
    description:  Optional[str]          = Field(None)


class WorkflowStep(BaseModel):
    step:        int
    description: str
    api_request: Optional[APIRequest] = None


# ── Response Models ───────────────────────────────────────────────────────────

class ChatResponse(BaseModel):
    session_id:     str
    query:          str
    intent:         Optional[Dict]     = None
    api_request:    Optional[Dict]     = None
    explanation:    Optional[str]      = None
    documentation:  Optional[str]      = None
    suggestions:    List[str]          = Field(default_factory=list)
    mode:           str                = "chat"
    timestamp:      str                = Field(default_factory=lambda: datetime.utcnow().isoformat())


class ExecuteResponse(BaseModel):
    success:         bool
    status_code:     int
    response_data:   Any
    explanation:     Optional[str]     = None
    debug_info:      Optional[Dict]    = None
    retry_request:   Optional[Dict]    = None
    response_time_ms: int              = 0
    timestamp:       str               = Field(default_factory=lambda: datetime.utcnow().isoformat())


class TutorialResponse(BaseModel):
    provider:   str
    goal:       str
    steps:      List[Dict]
    code_examples: List[Dict]          = Field(default_factory=list)
    timestamp:  str                    = Field(default_factory=lambda: datetime.utcnow().isoformat())


class DocsResponse(BaseModel):
    provider:    str
    endpoint:    Optional[str]         = None
    content:     str
    examples:    List[Dict]            = Field(default_factory=list)
    timestamp:   str                   = Field(default_factory=lambda: datetime.utcnow().isoformat())


class AnalyticsResponse(BaseModel):
    total_interactions:     int
    total_sessions:         int
    successful_executions:  int
    failed_executions:      int
    conversion_rate:        float
    avg_response_time_ms:   float
    avg_first_call_time_ms: float
    endpoint_usage:         List[Dict]
    error_frequency:        List[Dict]
    daily_activity:         List[Dict]
    provider_breakdown:     List[Dict]
