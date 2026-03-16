"""
SQLAlchemy ORM models for DevRel-in-a-Box.
"""
from datetime import datetime
from uuid import uuid4

from sqlalchemy import (
    Column, String, Integer, Float, Boolean,
    DateTime, Text, JSON, ForeignKey
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


class DeveloperSession(Base):
    __tablename__ = "developer_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    developer_id = Column(String, nullable=True, index=True)
    api_slug = Column(String, nullable=True, index=True)
    framework = Column(String, nullable=True)
    experience_level = Column(String, default="intermediate")
    stage = Column(String, default="discovery")  # discovery|intent|workspace|first_call|debug|production
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    workspaces = relationship("Workspace", back_populates="session")
    events = relationship("TelemetryEvent", back_populates="session")


class Workspace(Base):
    __tablename__ = "workspaces"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("developer_sessions.id"))
    api_slug = Column(String, nullable=True)
    goal = Column(Text)                    # original NL goal
    collection_json = Column(JSON)         # full Requestly collection
    endpoint_path = Column(String)
    http_method = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

    session = relationship("DeveloperSession", back_populates="workspaces")


class DebugLog(Base):
    __tablename__ = "debug_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("developer_sessions.id"))
    status_code = Column(Integer)
    error_type = Column(String)
    root_cause = Column(Text)
    fix_applied = Column(Boolean, default=False)
    resolution_time_seconds = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class APIEndpoint(Base):
    """Persisted metadata for every indexed API endpoint."""
    __tablename__ = "api_endpoints"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    api_slug = Column(String, nullable=False, index=True)
    path = Column(String, nullable=False)
    method = Column(String, nullable=False)
    summary = Column(Text)
    description = Column(Text)
    parameters = Column(JSON, default=list)
    request_body_schema = Column(JSON, nullable=True)
    response_schema = Column(JSON, nullable=True)
    auth_required = Column(Boolean, default=True)
    tags = Column(JSON, default=list)
    embedding_id = Column(String, nullable=True)   # ID in vector DB
    created_at = Column(DateTime, default=datetime.utcnow)


class TelemetryEvent(Base):
    __tablename__ = "telemetry_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("developer_sessions.id"))
    event_type = Column(String, nullable=False, index=True)
    metadata = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    session = relationship("DeveloperSession", back_populates="events")
