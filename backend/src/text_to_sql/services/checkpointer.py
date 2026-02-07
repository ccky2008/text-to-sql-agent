"""LangGraph checkpointer for session persistence."""

from datetime import UTC, datetime
from typing import Any

from langgraph.checkpoint.memory import MemorySaver

from text_to_sql.config import get_settings


class SessionManager:
    """Manages session state and checkpointing for LangGraph."""

    def __init__(self) -> None:
        settings = get_settings()
        self._sessions: dict[str, dict[str, Any]] = {}
        self._storage_type = settings.session_storage_type
        self._storage_path = settings.session_storage_path
        self._mongodb_uri = settings.mongodb_uri
        self._mongodb_database = settings.mongodb_database
        self._checkpointer: Any = None
        self._conn: Any = None
        self._mongo_client: Any = None
        self._motor_client: Any = None
        self._sessions_collection: Any = None

    async def initialize(self) -> Any:
        """Initialize the checkpointer and session storage.

        Must be called once during application startup before using the
        checkpointer or session CRUD methods.
        """
        if self._checkpointer is not None:
            return self._checkpointer

        if self._storage_type == "mongodb":
            from pymongo import MongoClient
            from motor.motor_asyncio import AsyncIOMotorClient
            from langgraph.checkpoint.mongodb import MongoDBSaver

            self._mongo_client = MongoClient(self._mongodb_uri)
            self._checkpointer = MongoDBSaver(
                self._mongo_client, db_name=self._mongodb_database
            )

            self._motor_client = AsyncIOMotorClient(self._mongodb_uri)
            db = self._motor_client[self._mongodb_database]
            self._sessions_collection = db["sessions"]
            await self._sessions_collection.create_index("session_id", unique=True)
        elif self._storage_type == "sqlite":
            import aiosqlite
            from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

            self._conn = await aiosqlite.connect(self._storage_path)
            self._checkpointer = AsyncSqliteSaver(self._conn)
        else:
            self._checkpointer = MemorySaver()

        return self._checkpointer

    @property
    def checkpointer(self) -> Any:
        """Get the LangGraph checkpointer instance."""
        return self._checkpointer

    async def create_session(self, session_id: str) -> dict[str, Any]:
        """Create a new session."""
        session = {
            "session_id": session_id,
            "created_at": datetime.now(UTC),
            "last_active": datetime.now(UTC),
            "message_count": 0,
        }

        if self._sessions_collection is not None:
            await self._sessions_collection.insert_one(session.copy())
        else:
            self._sessions[session_id] = session

        return session

    async def get_session(self, session_id: str) -> dict[str, Any] | None:
        """Get session info."""
        if self._sessions_collection is not None:
            doc = await self._sessions_collection.find_one({"session_id": session_id})
            if doc:
                doc.pop("_id", None)
                return doc
            return None
        return self._sessions.get(session_id)

    async def update_session(self, session_id: str) -> None:
        """Update session last active time and message count."""
        if self._sessions_collection is not None:
            await self._sessions_collection.update_one(
                {"session_id": session_id},
                {"$set": {"last_active": datetime.now(UTC)}, "$inc": {"message_count": 1}},
            )
        elif session_id in self._sessions:
            self._sessions[session_id]["last_active"] = datetime.now(UTC)
            self._sessions[session_id]["message_count"] += 1

    async def delete_session(self, session_id: str) -> bool:
        """Delete a session."""
        if self._sessions_collection is not None:
            result = await self._sessions_collection.delete_one({"session_id": session_id})
            return result.deleted_count > 0
        if session_id in self._sessions:
            del self._sessions[session_id]
            return True
        return False

    async def list_sessions(self) -> list[dict[str, Any]]:
        """List all sessions."""
        if self._sessions_collection is not None:
            sessions = []
            async for doc in self._sessions_collection.find():
                doc.pop("_id", None)
                sessions.append(doc)
            return sessions
        return list(self._sessions.values())

    def get_config(self, session_id: str) -> dict[str, Any]:
        """Get LangGraph config for a session."""
        return {"configurable": {"thread_id": session_id}}

    async def close(self) -> None:
        """Clean up resources."""
        if self._mongo_client is not None:
            self._mongo_client.close()
            self._mongo_client = None
        if self._motor_client is not None:
            self._motor_client.close()
            self._motor_client = None
        if self._conn is not None:
            await self._conn.close()
            self._conn = None
        self._checkpointer = None
        self._sessions_collection = None


_session_manager: SessionManager | None = None


def get_session_manager() -> SessionManager:
    """Get singleton session manager instance."""
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager()
    return _session_manager
