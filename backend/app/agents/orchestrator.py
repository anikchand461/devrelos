"""
Agent Orchestrator
──────────────────
Routes developer requests to the appropriate specialized agents,
manages shared context, and synthesizes multi-agent responses.
"""
from __future__ import annotations
import asyncio
from uuid import UUID

from app.agents.doc_agent import DocUnderstandingAgent
from app.agents.intent_agent import DeveloperIntentAgent
from app.agents.workspace_agent import WorkspaceGenerationAgent
from app.agents.debug_agent import DebuggingAgent
from app.agents.code_agent import CodeGenerationAgent
from app.models.schemas import (
    IntentRequest, IntentResponse,
    WorkspaceRequest, WorkspaceResponse,
    DebugRequest, DebugResponse,
    ExtractedIntent,
)
from app.services.vector_store import VectorStore
from app.services.context_memory import ContextMemory


class AgentOrchestrator:
    """
    Central coordinator for all AI agents.

    Flow:
        1. Developer submits NL goal
        2. IntentAgent extracts structured intent
        3. DocAgent enriches intent with endpoint metadata
        4. WorkspaceAgent generates Requestly collection
        5. CodeAgent produces language-specific snippets
        6. (On error) DebugAgent diagnoses and fixes

    All agents share a ContextMemory instance keyed by session_id.
    """

    def __init__(self, vector_store: VectorStore):
        self.vector_store = vector_store
        self.intent_agent = DeveloperIntentAgent()
        self.doc_agent = DocUnderstandingAgent(vector_store)
        self.workspace_agent = WorkspaceGenerationAgent()
        self.debug_agent = DebuggingAgent()
        self.code_agent = CodeGenerationAgent()

    async def process_intent(self, request: IntentRequest) -> IntentResponse:
        """
        Step 1-2: Extract developer intent and match to API endpoints.
        """
        session_id = request.session_id
        memory = ContextMemory(session_id)

        # 1. Extract structured intent from natural language
        intent = await self.intent_agent.extract(
            goal=request.goal,
            api_slug=request.api_slug,
            context=request.context,
        )

        # 2. Semantically search for matching endpoints in vector DB
        matched_endpoints = await self.doc_agent.find_endpoints(
            intent=intent,
            api_slug=request.api_slug,
            top_k=3,
        )

        # Refine intent with best-matched endpoint metadata
        if matched_endpoints:
            best = matched_endpoints[0]
            intent.endpoint_path = best.path
            intent.http_method = best.method

        # Store in session memory for downstream agents
        await memory.set("intent", intent.model_dump())
        await memory.set("matched_endpoints", [e.model_dump() for e in matched_endpoints])

        return IntentResponse(
            session_id=session_id,
            intent=intent,
            matched_endpoints=matched_endpoints,
        )

    async def generate_workspace(self, request: WorkspaceRequest) -> WorkspaceResponse:
        """
        Step 3-5: Generate Requestly workspace + code snippets in parallel.
        """
        memory = ContextMemory(request.session_id)

        # Run workspace generation and code generation in parallel
        collection_task = self.workspace_agent.generate(
            intent=request.intent,
            include_tests=request.include_tests,
        )
        snippets_task = self.code_agent.generate_snippets(
            intent=request.intent,
            languages=["javascript", "python", "go"],
        )

        collection, code_snippets = await asyncio.gather(
            collection_task, snippets_task
        )

        import json
        collection_json = json.dumps(collection.model_dump(), indent=2)

        # Build Requestly deep-link URL for one-click import
        import urllib.parse
        import_url = (
            f"https://app.requestly.io/import?data="
            f"{urllib.parse.quote(collection_json)}"
        )

        await memory.set("workspace_generated", True)
        await memory.set("collection_id", collection.name)

        return WorkspaceResponse(
            session_id=request.session_id,
            collection=collection,
            collection_json=collection_json,
            import_url=import_url,
            code_snippets=code_snippets,
        )

    async def debug_error(self, request: DebugRequest) -> DebugResponse:
        """
        Diagnose an API error and generate a corrective fix.
        """
        memory = ContextMemory(request.session_id)
        original_intent = request.original_intent or await memory.get_intent()

        result = await self.debug_agent.diagnose(
            error=request.error,
            original_intent=original_intent,
        )

        # Track resolution in memory
        await memory.set("last_debug", result.model_dump())

        return result
