"""
/api/workspace — Workspace Generation Route
"""
from fastapi import APIRouter, Request, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.orchestrator import AgentOrchestrator
from app.models.schemas import WorkspaceRequest, WorkspaceResponse
from app.db.session import get_db
from app.telemetry.tracker import track_event
from app.services.vector_store import VectorStore

router = APIRouter()


def get_orchestrator(request: Request) -> AgentOrchestrator:
    vs: VectorStore = request.app.state.vector_store
    return AgentOrchestrator(vs)


@router.post("/", response_model=WorkspaceResponse)
async def generate_workspace(
    body: WorkspaceRequest,
    db: AsyncSession = Depends(get_db),
    orchestrator: AgentOrchestrator = Depends(get_orchestrator),
):
    """
    Generate a Requestly collection + code snippets from a structured intent.
    """
    result = await orchestrator.generate_workspace(body)

    await track_event(db, body.session_id, "workspace_generated", {
        "endpoint": body.intent.endpoint_path,
        "api": body.intent.api_name,
    })

    return result
