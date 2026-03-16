"""
/api/analytics — Analytics & Activation Metrics Route
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, text

from app.models.db_models import TelemetryEvent, DeveloperSession
from app.models.schemas import ActivationMetrics, FunnelStage
from app.db.session import get_db

router = APIRouter()

FUNNEL_STAGES = [
    "intent_captured",
    "workspace_generated",
    "api_success",
    "debug_triggered",
]


@router.get("/activation", response_model=ActivationMetrics)
async def get_activation_metrics(db: AsyncSession = Depends(get_db)):
    """
    Return developer activation funnel and top error patterns.
    """
    # Total sessions
    total = await db.scalar(select(func.count()).select_from(DeveloperSession))

    # Funnel: count sessions that reached each stage
    funnel = []
    prev_count = total or 1
    for stage in FUNNEL_STAGES:
        count = await db.scalar(
            select(func.count(TelemetryEvent.session_id.distinct()))
            .where(TelemetryEvent.event_type == stage)
        ) or 0
        funnel.append(FunnelStage(
            stage=stage,
            count=count,
            conversion_rate=round(count / prev_count, 3) if prev_count else 0,
        ))
        prev_count = max(count, 1)

    # Top errors
    error_rows = await db.execute(
        select(
            TelemetryEvent.metadata["status_code"].label("status_code"),
            func.count().label("count"),
        )
        .where(TelemetryEvent.event_type == "debug_triggered")
        .group_by(text("1"))
        .order_by(text("2 DESC"))
        .limit(5)
    )
    top_errors = [{"status_code": r[0], "count": r[1]} for r in error_rows]

    return ActivationMetrics(
        total_sessions=total or 0,
        funnel=funnel,
        top_errors=top_errors,
        avg_time_to_first_success_seconds=45.2,  # TODO: compute from event timestamps
        at_risk_sessions=[],
    )


@router.post("/event")
async def record_event(
    session_id: str,
    event_type: str,
    metadata: dict = {},
    db: AsyncSession = Depends(get_db),
):
    """Record a telemetry event from the frontend widget."""
    from uuid import UUID
    from app.telemetry.tracker import track_event
    await track_event(db, UUID(session_id), event_type, metadata)
    return {"ok": True}
