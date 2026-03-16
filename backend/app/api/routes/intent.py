"""
/api/intent  — Developer Intent Route
"""
from uuid import uuid4

from fastapi import APIRouter, Request, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.orchestrator import AgentOrchestrator
from app.models.schemas import IntentRequest, IntentResponse, WorkspaceResponse
from app.db.session import get_db
from app.telemetry.tracker import track_event
from app.services.vector_store import VectorStore

router = APIRouter()


def get_orchestrator(request: Request) -> AgentOrchestrator:
    vs: VectorStore = request.app.state.vector_store
    return AgentOrchestrator(vs)


@router.post("/", response_model=IntentResponse)
async def capture_intent(
    body: IntentRequest,
    db: AsyncSession = Depends(get_db),
    orchestrator: AgentOrchestrator = Depends(get_orchestrator),
):
    """
    Core endpoint: take a developer's natural language goal and extract
    a structured API intent + matching endpoints.

    Example request:
        POST /api/intent
        {
            "goal": "charge a credit card $50",
            "api_slug": "stripe"
        }
    """
    # Assign session if not provided
    if not body.session_id:
        body.session_id = uuid4()

    result = await orchestrator.process_intent(body)

    await track_event(db, body.session_id, "intent_captured", {
        "goal": body.goal,
        "api": body.api_slug,
        "confidence": result.intent.confidence,
    })

    return result


@router.post("/full", response_model=WorkspaceResponse)
async def intent_to_workspace(
    body: IntentRequest,
    db: AsyncSession = Depends(get_db),
    orchestrator: AgentOrchestrator = Depends(get_orchestrator),
):
    """
    Convenience endpoint: extract intent AND generate workspace in one call.
    This is what the embeddable widget uses.
    """
    if not body.session_id:
        body.session_id = uuid4()

    # Step 1: Extract intent
    intent_result = await orchestrator.process_intent(body)

    # Step 2: Generate workspace immediately
    from app.models.schemas import WorkspaceRequest
    workspace_request = WorkspaceRequest(
        session_id=body.session_id,
        intent=intent_result.intent,
        include_tests=True,
        target_language=body.context.get("language", "javascript"),
    )
    workspace = await orchestrator.generate_workspace(workspace_request)

    await track_event(db, body.session_id, "workspace_generated", {
        "goal": body.goal,
        "endpoint": intent_result.intent.endpoint_path,
    })

    return workspace
