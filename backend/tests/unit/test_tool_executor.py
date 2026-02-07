"""Tests for the tool executor node."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from text_to_sql.agents.nodes.tool_executor import tool_executor_node, TOOL_REGISTRY
from text_to_sql.agents.state import AgentState, create_initial_state


class TestToolExecutorNode:
    """Test the tool executor node."""

    @pytest.fixture
    def base_state(self):
        """Create a base state for testing."""
        state = create_initial_state(
            question="Show all users",
            session_id="test-session",
        )
        return state

    @pytest.mark.asyncio
    async def test_no_pending_tool_call(self, base_state):
        """Test handling when there's no pending tool call."""
        base_state["pending_tool_call"] = None

        result = await tool_executor_node(base_state)

        assert result["tool_results"] == []
        assert result["pending_tool_call"] is None

    @pytest.mark.asyncio
    async def test_unknown_tool(self, base_state):
        """Test handling of unknown tool name."""
        base_state["pending_tool_call"] = {
            "id": "call-123",
            "name": "unknown_tool",
            "args": {},
        }

        result = await tool_executor_node(base_state)

        assert len(result["tool_results"]) == 1
        tool_result = result["tool_results"][0]
        assert tool_result["success"] is False
        assert "Unknown tool" in tool_result["error"]
        assert result["pending_tool_call"] is None

    @pytest.mark.asyncio
    async def test_execute_sql_query_tool_success(self, base_state):
        """Test successful SQL query execution via tool."""
        mock_result = {
            "success": True,
            "rows": [{"id": 1, "name": "test"}],
            "columns": ["id", "name"],
            "row_count": 1,
            "total_count": 100,
            "has_more": True,
            "page": 1,
            "page_size": 100,
            "query_token": "token-123",
            "error": None,
        }

        mock_tool = AsyncMock()
        mock_tool.ainvoke = AsyncMock(return_value=mock_result)

        base_state["pending_tool_call"] = {
            "id": "call-456",
            "name": "execute_sql_query",
            "args": {"sql": "SELECT * FROM users"},
        }

        with patch.dict(TOOL_REGISTRY, {"execute_sql_query": mock_tool}):
            result = await tool_executor_node(base_state)

        # Check tool results
        assert len(result["tool_results"]) == 1
        tool_result = result["tool_results"][0]
        assert tool_result["success"] is True
        assert tool_result["tool_name"] == "execute_sql_query"
        assert tool_result["tool_call_id"] == "call-456"

        # Check state updates
        assert result["is_valid"] is True
        assert result["executed"] is True
        assert result["results"] == [{"id": 1, "name": "test"}]
        assert result["columns"] == ["id", "name"]
        assert result["row_count"] == 1
        assert result["total_count"] == 100
        assert result["has_more_results"] is True
        assert result["query_token"] == "token-123"
        assert result["csv_available"] is True
        assert result["pending_tool_call"] is None

    @pytest.mark.asyncio
    async def test_execute_sql_query_tool_failure(self, base_state):
        """Test SQL query execution failure via tool."""
        mock_result = {
            "success": False,
            "rows": None,
            "columns": None,
            "row_count": 0,
            "total_count": None,
            "has_more": False,
            "page": 1,
            "page_size": 100,
            "query_token": None,
            "error": "Query validation failed",
        }

        mock_tool = AsyncMock()
        mock_tool.ainvoke = AsyncMock(return_value=mock_result)

        base_state["pending_tool_call"] = {
            "id": "call-789",
            "name": "execute_sql_query",
            "args": {"sql": "DROP TABLE users"},
        }

        with patch.dict(TOOL_REGISTRY, {"execute_sql_query": mock_tool}):
            result = await tool_executor_node(base_state)

        # Check tool results
        tool_result = result["tool_results"][0]
        assert tool_result["success"] is False

        # Check state updates
        assert result["executed"] is False
        assert result["execution_error"] == "Query validation failed"

    @pytest.mark.asyncio
    async def test_session_id_injection(self, base_state):
        """Test that session_id is injected into tool args."""
        mock_result = {
            "success": True,
            "rows": [],
            "columns": [],
            "row_count": 0,
            "total_count": 0,
            "has_more": False,
            "page": 1,
            "page_size": 100,
            "query_token": None,
            "error": None,
        }

        mock_tool = AsyncMock()
        mock_tool.ainvoke = AsyncMock(return_value=mock_result)

        base_state["session_id"] = "my-special-session"
        base_state["pending_tool_call"] = {
            "id": "call-001",
            "name": "execute_sql_query",
            "args": {"sql": "SELECT 1"},
        }

        with patch.dict(TOOL_REGISTRY, {"execute_sql_query": mock_tool}):
            await tool_executor_node(base_state)

        # Verify session_id was injected
        call_args = mock_tool.ainvoke.call_args[0][0]
        assert call_args["session_id"] == "my-special-session"

    @pytest.mark.asyncio
    async def test_tool_exception_handling(self, base_state):
        """Test handling of tool execution exceptions."""
        mock_tool = AsyncMock()
        mock_tool.ainvoke = AsyncMock(side_effect=Exception("Database connection lost"))

        base_state["pending_tool_call"] = {
            "id": "call-error",
            "name": "execute_sql_query",
            "args": {"sql": "SELECT 1"},
        }

        with patch.dict(TOOL_REGISTRY, {"execute_sql_query": mock_tool}):
            result = await tool_executor_node(base_state)

        # Check error handling
        tool_result = result["tool_results"][0]
        assert tool_result["success"] is False
        assert "Database connection lost" in tool_result["error"]
        assert result["execution_error"] == "Database connection lost"
        assert result["pending_tool_call"] is None

    @pytest.mark.asyncio
    async def test_csv_exceeds_limit_calculation(self, base_state):
        """Test that csv_exceeds_limit is calculated correctly."""
        mock_result = {
            "success": True,
            "rows": [],
            "columns": [],
            "row_count": 0,
            "total_count": 5000,  # Over 2500 limit
            "has_more": True,
            "page": 1,
            "page_size": 100,
            "query_token": "token",
            "error": None,
        }

        mock_tool = AsyncMock()
        mock_tool.ainvoke = AsyncMock(return_value=mock_result)

        base_state["pending_tool_call"] = {
            "id": "call-csv",
            "name": "execute_sql_query",
            "args": {"sql": "SELECT * FROM large_table"},
        }

        with patch.dict(TOOL_REGISTRY, {"execute_sql_query": mock_tool}):
            result = await tool_executor_node(base_state)

        assert result["csv_exceeds_limit"] is True

    @pytest.mark.asyncio
    async def test_tool_results_accumulation(self, base_state):
        """Test that tool results are accumulated from previous results."""
        base_state["tool_results"] = [
            {"tool_call_id": "previous-1", "tool_name": "other_tool", "success": True}
        ]

        mock_result = {
            "success": True,
            "rows": [],
            "columns": [],
            "row_count": 0,
            "total_count": 0,
            "has_more": False,
            "page": 1,
            "page_size": 100,
            "query_token": None,
            "error": None,
        }

        mock_tool = AsyncMock()
        mock_tool.ainvoke = AsyncMock(return_value=mock_result)

        base_state["pending_tool_call"] = {
            "id": "call-new",
            "name": "execute_sql_query",
            "args": {"sql": "SELECT 1"},
        }

        with patch.dict(TOOL_REGISTRY, {"execute_sql_query": mock_tool}):
            result = await tool_executor_node(base_state)

        # Should have both previous and new results
        assert len(result["tool_results"]) == 2
        assert result["tool_results"][0]["tool_call_id"] == "previous-1"
        assert result["tool_results"][1]["tool_call_id"] == "call-new"


class TestToolRegistry:
    """Test the tool registry."""

    def test_execute_sql_query_registered(self):
        """Test that execute_sql_query is registered."""
        assert "execute_sql_query" in TOOL_REGISTRY

    def test_registry_has_callable_tools(self):
        """Test that all registered tools are callable."""
        for name, tool in TOOL_REGISTRY.items():
            assert hasattr(tool, "ainvoke"), f"Tool {name} should have ainvoke method"
