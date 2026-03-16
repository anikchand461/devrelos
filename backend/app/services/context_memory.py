"""
Context Memory
──────────────
Per-session key-value store for agent state.
Uses Redis in production, in-memory dict for local dev.
"""
from __future__ import annotations
import json
from uuid import UUID

_memory: dict[str, dict] = {}   # In-process fallback


class ContextMemory:
    def __init__(self, session_id: UUID | None):
        self.key = str(session_id) if session_id else "anonymous"

    async def set(self, field: str, value):
        if self.key not in _memory:
            _memory[self.key] = {}
        _memory[self.key][field] = value

    async def get(self, field: str, default=None):
        return _memory.get(self.key, {}).get(field, default)

    async def get_intent(self):
        from app.models.schemas import ExtractedIntent
        raw = await self.get("intent")
        if raw:
            return ExtractedIntent(**raw)
        return None

    async def clear(self):
        _memory.pop(self.key, None)
