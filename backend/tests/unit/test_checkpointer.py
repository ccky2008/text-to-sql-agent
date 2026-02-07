"""Tests for SessionManager (memory mode)."""

import pytest

from text_to_sql.services.checkpointer import SessionManager


@pytest.fixture
def session_manager(monkeypatch):
    """Create a SessionManager in memory mode for testing."""
    monkeypatch.setenv("SESSION_STORAGE_TYPE", "memory")
    # Avoid loading real settings by patching at the instance level
    mgr = SessionManager.__new__(SessionManager)
    mgr._sessions = {}
    mgr._storage_type = "memory"
    mgr._storage_path = ""
    mgr._mongodb_uri = ""
    mgr._mongodb_database = ""
    mgr._checkpointer = None
    mgr._conn = None
    mgr._mongo_client = None
    mgr._motor_client = None
    mgr._sessions_collection = None
    return mgr


class TestSessionManagerMemory:
    """Test SessionManager CRUD in memory mode."""

    async def test_create_session(self, session_manager):
        session = await session_manager.create_session("test-1")
        assert session["session_id"] == "test-1"
        assert session["message_count"] == 0
        assert "created_at" in session
        assert "last_active" in session

    async def test_get_session(self, session_manager):
        await session_manager.create_session("test-1")
        session = await session_manager.get_session("test-1")
        assert session is not None
        assert session["session_id"] == "test-1"

    async def test_get_session_not_found(self, session_manager):
        session = await session_manager.get_session("nonexistent")
        assert session is None

    async def test_update_session(self, session_manager):
        await session_manager.create_session("test-1")
        await session_manager.update_session("test-1")
        session = await session_manager.get_session("test-1")
        assert session["message_count"] == 1

    async def test_update_session_increments(self, session_manager):
        await session_manager.create_session("test-1")
        await session_manager.update_session("test-1")
        await session_manager.update_session("test-1")
        await session_manager.update_session("test-1")
        session = await session_manager.get_session("test-1")
        assert session["message_count"] == 3

    async def test_delete_session(self, session_manager):
        await session_manager.create_session("test-1")
        result = await session_manager.delete_session("test-1")
        assert result is True
        session = await session_manager.get_session("test-1")
        assert session is None

    async def test_delete_session_not_found(self, session_manager):
        result = await session_manager.delete_session("nonexistent")
        assert result is False

    async def test_list_sessions(self, session_manager):
        await session_manager.create_session("test-1")
        await session_manager.create_session("test-2")
        sessions = await session_manager.list_sessions()
        assert len(sessions) == 2
        ids = {s["session_id"] for s in sessions}
        assert ids == {"test-1", "test-2"}

    async def test_list_sessions_empty(self, session_manager):
        sessions = await session_manager.list_sessions()
        assert sessions == []


class TestSessionManagerConfig:
    """Test get_config."""

    def test_get_config_format(self, session_manager):
        config = session_manager.get_config("test-1")
        assert config == {"configurable": {"thread_id": "test-1"}}


class TestSessionManagerClose:
    """Test close() cleanup."""

    async def test_close_memory_mode(self, session_manager):
        """Close in memory mode should not error."""
        await session_manager.close()
        assert session_manager._checkpointer is None
        assert session_manager._sessions_collection is None
