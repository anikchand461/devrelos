"""
routes/chat.py – Chat endpoint
POST /chat → orchestrates full AI pipeline
"""

import uuid
from fastapi import APIRouter, HTTPException
from models import ChatRequest, ChatResponse
from orchestrator import process_chat

router = APIRouter(prefix="/api", tags=["chat"])


@router.post("/chat")
async def chat(req: ChatRequest):
    """
    Accept a developer's natural language query and return:
    - Parsed intent
    - Generated API request
    - Explanation / documentation
    - Proactive suggestions
    """
    session_id = req.session_id or str(uuid.uuid4())

    try:
        result = await process_chat(
            query      = req.query,
            session_id = session_id,
            mode       = req.mode or "chat",
        )
        result["session_id"] = session_id
        return result

    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
