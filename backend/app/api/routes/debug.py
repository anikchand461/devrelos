"""
/api/debug — Debugging Agent Route
"""
from fastapi import APIRouter, Request, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.orchestrator import AgentOrchestrator
from app.models.schemas import DebugRequest, DebugResponse
from app.db.session import get_db
from app.telemetry.tracker import track_event
from app.services.vector_store import VectorStore

router = APIRouter()


def get_orchestrator(request: Request) -> AgentOrchestrator:
    vs: VectorStore = request.app.state.vector_store
    return AgentOrchestrator(vs)


@router.post("/", response_model=DebugResponse)
async def debug_error(
    body: DebugRequest,
    db: AsyncSession = Depends(get_db),
    orchestrator: AgentOrchestrator = Depends(get_orchestrator),
):
    """
    Diagnose an API error and return a corrective fix.

    Example request:
        POST /api/debug
        {
            "session_id": "...",
            "error": {
                "status_code": 401,
                "response_body": "{\"error\": \"No such API key\"}",
                "request_url": "https://api.stripe.com/v1/payment_intents",
                "request_method": "POST",
                "request_headers": {}
            }
        }
    """
    result = await orchestrator.debug_error(body)

    await track_event(db, body.session_id, "debug_triggered", {
        "status_code": body.error.status_code,
        "error_type": result.error_type,
        "confidence": result.confidence,
    })

    return result
