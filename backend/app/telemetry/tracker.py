"""Lightweight telemetry event writer."""
from uuid import UUID
from app.models.db_models import TelemetryEvent
from app.core.config import settings


async def track_event(db, session_id: UUID, event_type: str, metadata: dict = {}):
    if not settings.ENABLE_TELEMETRY:
        return
    event = TelemetryEvent(
        session_id=session_id,
        event_type=event_type,
        metadata=metadata,
    )
    db.add(event)
    # Flush without commit — caller commits the transaction
    await db.flush()
