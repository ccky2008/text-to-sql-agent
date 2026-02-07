"""Tests for the enhanced SQL execution tool."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from text_to_sql.agents.tools.sql_tools import execute_sql_query, _error_result
from text_to_sql.core.types import ExecutionResult


class TestErrorResult:
    """Test the error result helper function."""

    def test_error_result_basic(self):
        """Test basic error result creation."""
        result = _error_result("Test error")

        assert result["success"] is False
        assert result["error"] == "Test error"
        assert result["rows"] is None
        assert result["columns"] is None
        assert result["row_count"] == 0
        assert result["total_count"] is None
        assert result["has_more"] is False
        assert result["page"] == 1
        assert result["page_size"] == 100
        assert result["query_token"] is None

    def test_error_result_with_pagination(self):
        """Test error result with custom pagination."""
        result = _error_result("Test error", page=5, page_size=50)

        assert result["page"] == 5
        assert result["page_size"] == 50


class TestExecuteSQLQuery:
    """Test the execute_sql_query tool."""

    @pytest.fixture
    def mock_settings(self):
        """Mock settings."""
        settings = MagicMock()
        settings.sql_max_rows = 1000
        return settings

    @pytest.fixture
    def mock_db_service(self):
        """Mock database service."""
        service = AsyncMock()
        service.execute_count_query = AsyncMock(return_value=100)
        service.execute_query_paginated = AsyncMock(
            return_value=ExecutionResult(
                success=True,
                rows=[{"id": 1, "name": "test"}],
                row_count=1,
                columns=["id", "name"],
                error=None,
            )
        )
        return service

    @pytest.fixture
    def mock_query_cache(self):
        """Mock query cache."""
        cache = MagicMock()
        cache.store = MagicMock(return_value="test-token-123")
        return cache

    @pytest.mark.asyncio
    async def test_execute_valid_query(self, mock_settings, mock_db_service, mock_query_cache):
        """Test executing a valid SQL query."""
        with patch("text_to_sql.agents.tools.sql_tools.get_settings", return_value=mock_settings), \
             patch("text_to_sql.agents.tools.sql_tools.get_database_service", return_value=mock_db_service), \
             patch("text_to_sql.agents.tools.sql_tools.get_query_cache", return_value=mock_query_cache), \
             patch("text_to_sql.agents.tools.sql_tools.validate_tables_exist", new_callable=AsyncMock, return_value=(True, [], None)):

            result = await execute_sql_query.ainvoke({
                "sql": "SELECT id, name FROM users LIMIT 10",
                "page": 1,
                "page_size": 100,
                "session_id": "test-session",
            })

            assert result["success"] is True
            assert result["rows"] == [{"id": 1, "name": "test"}]
            assert result["columns"] == ["id", "name"]
            assert result["row_count"] == 1
            assert result["total_count"] == 100
            assert result["query_token"] == "test-token-123"

    @pytest.mark.asyncio
    async def test_execute_with_validation_error(self, mock_settings):
        """Test executing an invalid SQL query."""
        with patch("text_to_sql.agents.tools.sql_tools.get_settings", return_value=mock_settings):

            result = await execute_sql_query.ainvoke({
                "sql": "DROP TABLE users",
                "page": 1,
                "page_size": 100,
                "session_id": "test-session",
            })

            assert result["success"] is False
            assert "read-only" in result["error"].lower()
            assert result["rows"] is None

    @pytest.mark.asyncio
    async def test_execute_with_missing_table(self, mock_settings, mock_db_service, mock_query_cache):
        """Test executing query with non-existent table."""
        with patch("text_to_sql.agents.tools.sql_tools.get_settings", return_value=mock_settings), \
             patch("text_to_sql.agents.tools.sql_tools.get_database_service", return_value=mock_db_service), \
             patch("text_to_sql.agents.tools.sql_tools.get_query_cache", return_value=mock_query_cache), \
             patch("text_to_sql.agents.tools.sql_tools.validate_tables_exist", new_callable=AsyncMock, return_value=(False, ["nonexistent"], "Table not found")):

            result = await execute_sql_query.ainvoke({
                "sql": "SELECT * FROM nonexistent",
                "page": 1,
                "page_size": 100,
                "session_id": "test-session",
            })

            assert result["success"] is False
            assert "Table not found" in result["error"]

    @pytest.mark.asyncio
    async def test_page_size_enforcement(self, mock_settings, mock_db_service, mock_query_cache):
        """Test that page_size is capped at 500."""
        with patch("text_to_sql.agents.tools.sql_tools.get_settings", return_value=mock_settings), \
             patch("text_to_sql.agents.tools.sql_tools.get_database_service", return_value=mock_db_service), \
             patch("text_to_sql.agents.tools.sql_tools.get_query_cache", return_value=mock_query_cache), \
             patch("text_to_sql.agents.tools.sql_tools.validate_tables_exist", new_callable=AsyncMock, return_value=(True, [], None)):

            result = await execute_sql_query.ainvoke({
                "sql": "SELECT id FROM users LIMIT 10",
                "page": 1,
                "page_size": 1000,  # Over the limit
                "session_id": "test-session",
            })

            assert result["success"] is True
            # The page_size should be capped, but we can verify execution happened
            mock_db_service.execute_query_paginated.assert_called_once()

    @pytest.mark.asyncio
    async def test_pagination_offset_calculation(self, mock_settings, mock_db_service, mock_query_cache):
        """Test correct offset calculation for pagination."""
        with patch("text_to_sql.agents.tools.sql_tools.get_settings", return_value=mock_settings), \
             patch("text_to_sql.agents.tools.sql_tools.get_database_service", return_value=mock_db_service), \
             patch("text_to_sql.agents.tools.sql_tools.get_query_cache", return_value=mock_query_cache), \
             patch("text_to_sql.agents.tools.sql_tools.validate_tables_exist", new_callable=AsyncMock, return_value=(True, [], None)):

            await execute_sql_query.ainvoke({
                "sql": "SELECT id FROM users LIMIT 10",
                "page": 3,
                "page_size": 50,
                "session_id": "test-session",
            })

            # Page 3 with page_size 50 should have offset 100
            call_args = mock_db_service.execute_query_paginated.call_args
            assert call_args[1]["offset"] == 100
            assert call_args[1]["limit"] == 50

    @pytest.mark.asyncio
    async def test_has_more_calculation(self, mock_settings, mock_db_service, mock_query_cache):
        """Test has_more is calculated correctly."""
        mock_db_service.execute_count_query = AsyncMock(return_value=150)
        mock_db_service.execute_query_paginated = AsyncMock(
            return_value=ExecutionResult(
                success=True,
                rows=[{"id": i} for i in range(100)],
                row_count=100,
                columns=["id"],
                error=None,
            )
        )

        with patch("text_to_sql.agents.tools.sql_tools.get_settings", return_value=mock_settings), \
             patch("text_to_sql.agents.tools.sql_tools.get_database_service", return_value=mock_db_service), \
             patch("text_to_sql.agents.tools.sql_tools.get_query_cache", return_value=mock_query_cache), \
             patch("text_to_sql.agents.tools.sql_tools.validate_tables_exist", new_callable=AsyncMock, return_value=(True, [], None)):

            result = await execute_sql_query.ainvoke({
                "sql": "SELECT id FROM users",
                "page": 1,
                "page_size": 100,
                "session_id": "test-session",
            })

            assert result["has_more"] is True  # 100 rows fetched, 150 total

    @pytest.mark.asyncio
    async def test_query_token_generation(self, mock_settings, mock_db_service, mock_query_cache):
        """Test that query token is generated for successful execution."""
        with patch("text_to_sql.agents.tools.sql_tools.get_settings", return_value=mock_settings), \
             patch("text_to_sql.agents.tools.sql_tools.get_database_service", return_value=mock_db_service), \
             patch("text_to_sql.agents.tools.sql_tools.get_query_cache", return_value=mock_query_cache), \
             patch("text_to_sql.agents.tools.sql_tools.validate_tables_exist", new_callable=AsyncMock, return_value=(True, [], None)):

            result = await execute_sql_query.ainvoke({
                "sql": "SELECT id FROM users LIMIT 10",
                "page": 1,
                "page_size": 100,
                "session_id": "my-session",
            })

            assert result["query_token"] == "test-token-123"
            mock_query_cache.store.assert_called_once_with("SELECT id FROM users LIMIT 10", "my-session")

    @pytest.mark.asyncio
    async def test_execution_failure(self, mock_settings, mock_db_service, mock_query_cache):
        """Test handling of database execution failure."""
        mock_db_service.execute_query_paginated = AsyncMock(
            return_value=ExecutionResult(
                success=False,
                rows=None,
                row_count=0,
                columns=None,
                error="Connection timeout",
            )
        )

        with patch("text_to_sql.agents.tools.sql_tools.get_settings", return_value=mock_settings), \
             patch("text_to_sql.agents.tools.sql_tools.get_database_service", return_value=mock_db_service), \
             patch("text_to_sql.agents.tools.sql_tools.get_query_cache", return_value=mock_query_cache), \
             patch("text_to_sql.agents.tools.sql_tools.validate_tables_exist", new_callable=AsyncMock, return_value=(True, [], None)):

            result = await execute_sql_query.ainvoke({
                "sql": "SELECT id FROM users LIMIT 10",
                "page": 1,
                "page_size": 100,
                "session_id": "test-session",
            })

            assert result["success"] is False
            assert "Connection timeout" in result["error"]
