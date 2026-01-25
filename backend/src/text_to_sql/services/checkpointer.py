"""LangGraph checkpointer for session persistence."""

import aiosqlite
from datetime import UTC, datetime
from typing import Any

from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from text_to_sql.config import get_settings


class SessionManager:
    """Manages session state and checkpointing for LangGraph."""

    def __init__(self) -> None:
        settings = get_settings()
        self._sessions: dict[str, dict[str, Any]] = {}
        self._storage_type = settings.session_storage_type
        self._storage_path = settings.session_storage_path
        self._checkpointer: MemorySaver | AsyncSqliteSaver | None = None
        self._conn: aiosqlite.Connection | None = None

    async def _init_checkpointer(self) -> MemorySaver | AsyncSqliteSaver:
        """Initialize the checkpointer (async for SQLite)."""
        if self._checkpointer is not None:
            return self._checkpointer

        if self._storage_type == "sqlite":
            self._conn = await aiosqlite.connect(self._storage_path)
            self._checkpointer = AsyncSqliteSaver(self._conn)
        else:
            self._checkpointer = MemorySaver()

        return self._checkpointer

    @property
    def checkpointer(self) -> MemorySaver | AsyncSqliteSaver | None:
        """Get the LangGraph checkpointer instance."""
        return self._checkpointer

    def create_session(self, session_id: str) -> dict[str, Any]:
        """Create a new session."""
        session = {
            "session_id": session_id,
            "created_at": datetime.now(UTC),
            "last_active": datetime.now(UTC),
            "message_count": 0,
        }
        self._sessions[session_id] = session
        return session

    def get_session(self, session_id: str) -> dict[str, Any] | None:
        """Get session info."""
        return self._sessions.get(session_id)

    def update_session(self, session_id: str) -> None:
        """Update session last active time and message count."""
        if session_id in self._sessions:
            self._sessions[session_id]["last_active"] = datetime.now(UTC)
            self._sessions[session_id]["message_count"] += 1

    def delete_session(self, session_id: str) -> bool:
        """Delete a session."""
        if session_id in self._sessions:
            del self._sessions[session_id]
            return True
        return False

    def list_sessions(self) -> list[dict[str, Any]]:
        """List all sessions."""
        return list(self._sessions.values())

    def get_config(self, session_id: str) -> dict[str, Any]:
        """Get LangGraph config for a session."""
        return {"configurable": {"thread_id": session_id}}


_session_manager: SessionManager | None = None


def get_session_manager() -> SessionManager:
    """Get singleton session manager instance."""
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager()
    return _session_manager
