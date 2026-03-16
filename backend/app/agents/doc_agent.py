"""
Documentation Understanding Agent
───────────────────────────────────
Parses API specifications, builds semantic embeddings, and retrieves
the most relevant endpoints for a given developer intent.
"""
from __future__ import annotations

from app.models.schemas import ExtractedIntent, EndpointMatch
from app.services.vector_store import VectorStore


class DocUnderstandingAgent:
    def __init__(self, vector_store: VectorStore):
        self.vector_store = vector_store

    async def find_endpoints(
        self,
        intent: ExtractedIntent,
        api_slug: str | None = None,
        top_k: int = 3,
    ) -> list[EndpointMatch]:
        """
        Semantically search the vector DB for endpoints matching the intent.
        """
        query = f"{intent.goal} {intent.description} {intent.http_method} {intent.endpoint_path}"

        results = await self.vector_store.search(
            query=query,
            collection=api_slug or intent.api_name,
            top_k=top_k,
        )

        matches = []
        for r in results:
            matches.append(EndpointMatch(
                path=r["metadata"].get("path", intent.endpoint_path),
                method=r["metadata"].get("method", intent.http_method),
                summary=r["metadata"].get("summary", ""),
                score=r["score"],
            ))

        # If vector search found nothing, return the intent's own values as a fallback
        if not matches:
            matches.append(EndpointMatch(
                path=intent.endpoint_path,
                method=intent.http_method,
                summary=intent.description,
                score=0.5,
            ))

        return matches
