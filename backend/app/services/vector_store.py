"""
Vector Store Service
─────────────────────
Wraps ChromaDB for local development.
Swap the implementation for Pinecone/Weaviate in production.
"""
from __future__ import annotations
import json

import chromadb
from chromadb.config import Settings as ChromaSettings
from openai import AsyncOpenAI

from app.core.config import settings as app_settings


class VectorStore:
    def __init__(self):
        self._client: chromadb.AsyncHttpClient | None = None
        self._openai = AsyncOpenAI(api_key=app_settings.OPENAI_API_KEY)

    async def connect(self):
        try:
            self._client = await chromadb.AsyncHttpClient(
                host=app_settings.CHROMA_HOST,
                port=app_settings.CHROMA_PORT,
                settings=ChromaSettings(allow_reset=True),
            )
        except Exception:
            # Fall back to in-memory for local demo without ChromaDB running
            self._client = chromadb.Client()

    async def close(self):
        pass  # ChromaDB client doesn't need explicit close

    async def upsert_endpoints(
        self,
        api_slug: str,
        endpoints: list[dict],
    ) -> int:
        """
        Embed and store API endpoint metadata in the vector DB.

        Args:
            api_slug: Identifier for this API (e.g. "stripe")
            endpoints: List of endpoint dicts with keys:
                       path, method, summary, description, parameters

        Returns:
            Number of endpoints indexed
        """
        collection = await self._get_or_create_collection(api_slug)

        documents = []
        metadatas = []
        ids = []

        for ep in endpoints:
            # Build a rich text representation for embedding
            text = (
                f"{ep.get('method', 'GET')} {ep.get('path', '/')} "
                f"{ep.get('summary', '')} {ep.get('description', '')} "
                f"{json.dumps(ep.get('parameters', []))}"
            )
            documents.append(text)
            metadatas.append({
                "path": ep.get("path", ""),
                "method": ep.get("method", "GET"),
                "summary": ep.get("summary", ""),
                "api_slug": api_slug,
            })
            ids.append(f"{api_slug}:{ep.get('method','GET')}:{ep.get('path','/')}")

        if documents:
            await collection.upsert(
                documents=documents,
                metadatas=metadatas,
                ids=ids,
            )

        return len(documents)

    async def search(
        self,
        query: str,
        collection: str,
        top_k: int = 3,
    ) -> list[dict]:
        """
        Semantic search for endpoints matching a developer's query.
        """
        try:
            coll = await self._client.get_collection(collection)
            results = await coll.query(
                query_texts=[query],
                n_results=min(top_k, 10),
            )
            items = []
            for i, doc in enumerate(results["documents"][0]):
                items.append({
                    "document": doc,
                    "metadata": results["metadatas"][0][i],
                    "score": 1.0 - (results["distances"][0][i] if results.get("distances") else 0.3),
                })
            return items
        except Exception:
            return []

    async def _get_or_create_collection(self, name: str):
        try:
            return await self._client.get_collection(name)
        except Exception:
            return await self._client.create_collection(
                name=name,
                metadata={"hnsw:space": "cosine"},
            )
