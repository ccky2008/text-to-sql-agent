"""Tests for the exploration tools module."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from text_to_sql.agents.tools.exploration_tools import (
    _validate_identifier,
    _normalize_table_name,
    _get_known_tables,
    _get_known_columns,
    explore_column_values,
    get_exploration_tools,
)


class TestValidateIdentifier:
    """Test the _validate_identifier function for SQL injection prevention."""

    def test_valid_simple_identifier(self):
        """Test valid simple identifiers."""
        assert _validate_identifier("users") is True
        assert _validate_identifier("aws_rds") is True
        assert _validate_identifier("table1") is True

    def test_valid_identifier_with_underscore(self):
        """Test identifiers starting with underscore."""
        assert _validate_identifier("_private") is True
        assert _validate_identifier("_table_name") is True

    def test_valid_mixed_case(self):
        """Test mixed case identifiers."""
        assert _validate_identifier("UserTable") is True
        assert _validate_identifier("AWS_RDS") is True
        assert _validate_identifier("camelCase") is True

    def test_invalid_starts_with_number(self):
        """Test that identifiers starting with numbers are rejected."""
        assert _validate_identifier("1table") is False
        assert _validate_identifier("123") is False

    def test_invalid_sql_injection_attempts(self):
        """Test that SQL injection attempts are rejected."""
        # Basic injection attempts
        assert _validate_identifier("users; DROP TABLE") is False
        assert _validate_identifier("users--") is False
        assert _validate_identifier("users/**/") is False

        # Quotes and special characters
        assert _validate_identifier("users'") is False
        assert _validate_identifier('users"') is False
        assert _validate_identifier("users`") is False

        # Schema-qualified (handled by normalize, but should fail validation)
        assert _validate_identifier("public.users") is False
        assert _validate_identifier("schema.table") is False

    def test_invalid_special_characters(self):
        """Test that special characters are rejected."""
        assert _validate_identifier("table-name") is False
        assert _validate_identifier("table name") is False
        assert _validate_identifier("table@name") is False
        assert _validate_identifier("table$name") is False
        assert _validate_identifier("table#name") is False

    def test_empty_string(self):
        """Test that empty strings are rejected."""
        assert _validate_identifier("") is False

    def test_unicode_characters(self):
        """Test that unicode characters are rejected."""
        assert _validate_identifier("tëst") is False
        assert _validate_identifier("表") is False


class TestNormalizeTableName:
    """Test the _normalize_table_name function."""

    def test_simple_table_name(self):
        """Test that simple table names are unchanged."""
        assert _normalize_table_name("users") == "users"
        assert _normalize_table_name("aws_rds") == "aws_rds"

    def test_schema_qualified_name(self):
        """Test stripping schema prefix."""
        assert _normalize_table_name("public.users") == "users"
        assert _normalize_table_name("public.aws_rds") == "aws_rds"
        assert _normalize_table_name("schema.table") == "table"

    def test_multiple_dots(self):
        """Test handling of multiple dots (takes last part)."""
        assert _normalize_table_name("catalog.schema.table") == "table"
        assert _normalize_table_name("a.b.c.d") == "d"

    def test_empty_after_dot(self):
        """Test edge case with trailing dot."""
        assert _normalize_table_name("schema.") == ""

    def test_dot_at_start(self):
        """Test edge case with leading dot."""
        assert _normalize_table_name(".table") == "table"


class TestGetKnownTables:
    """Test the _get_known_tables function."""

    def test_returns_lowercase_table_names(self):
        """Test that table names are returned in lowercase."""
        mock_tables = [
            {"metadata": {"table_name": "AWS_RDS"}},
            {"metadata": {"table_name": "users"}},
            {"metadata": {"table_name": "EC2_Instances"}},
        ]

        with patch(
            "text_to_sql.agents.tools.exploration_tools.get_vector_store_service"
        ) as mock_get_vs:
            mock_vs = MagicMock()
            mock_vs.list_database_info.return_value = mock_tables
            mock_get_vs.return_value = mock_vs

            result = _get_known_tables()

        assert result == {"aws_rds", "users", "ec2_instances"}

    def test_handles_missing_table_name(self):
        """Test handling entries without table_name."""
        mock_tables = [
            {"metadata": {"table_name": "valid_table"}},
            {"metadata": {}},  # Missing table_name
            {"metadata": {"table_name": ""}},  # Empty table_name
            {},  # Missing metadata
        ]

        with patch(
            "text_to_sql.agents.tools.exploration_tools.get_vector_store_service"
        ) as mock_get_vs:
            mock_vs = MagicMock()
            mock_vs.list_database_info.return_value = mock_tables
            mock_get_vs.return_value = mock_vs

            result = _get_known_tables()

        assert result == {"valid_table"}

    def test_empty_database(self):
        """Test handling of empty database info."""
        with patch(
            "text_to_sql.agents.tools.exploration_tools.get_vector_store_service"
        ) as mock_get_vs:
            mock_vs = MagicMock()
            mock_vs.list_database_info.return_value = []
            mock_get_vs.return_value = mock_vs

            result = _get_known_tables()

        assert result == set()


class TestGetKnownColumns:
    """Test the _get_known_columns function."""

    def test_returns_columns_for_table(self):
        """Test getting columns for a specific table."""
        mock_tables = [
            {
                "metadata": {
                    "table_name": "aws_rds",
                    "columns": [
                        {"name": "id"},
                        {"name": "engine"},
                        {"name": "instance_type"},
                    ],
                }
            },
            {
                "metadata": {
                    "table_name": "aws_ec2",
                    "columns": [{"name": "id"}, {"name": "status"}],
                }
            },
        ]

        with patch(
            "text_to_sql.agents.tools.exploration_tools.get_vector_store_service"
        ) as mock_get_vs:
            mock_vs = MagicMock()
            mock_vs.list_database_info.return_value = mock_tables
            mock_get_vs.return_value = mock_vs

            result = _get_known_columns("aws_rds")

        assert result == {"id", "engine", "instance_type"}

    def test_case_insensitive_table_match(self):
        """Test case-insensitive table name matching."""
        mock_tables = [
            {
                "metadata": {
                    "table_name": "AWS_RDS",
                    "columns": [{"name": "engine"}],
                }
            },
        ]

        with patch(
            "text_to_sql.agents.tools.exploration_tools.get_vector_store_service"
        ) as mock_get_vs:
            mock_vs = MagicMock()
            mock_vs.list_database_info.return_value = mock_tables
            mock_get_vs.return_value = mock_vs

            result = _get_known_columns("aws_rds")

        assert result == {"engine"}

    def test_returns_lowercase_columns(self):
        """Test that column names are returned in lowercase."""
        mock_tables = [
            {
                "metadata": {
                    "table_name": "users",
                    "columns": [{"name": "ID"}, {"name": "UserName"}],
                }
            },
        ]

        with patch(
            "text_to_sql.agents.tools.exploration_tools.get_vector_store_service"
        ) as mock_get_vs:
            mock_vs = MagicMock()
            mock_vs.list_database_info.return_value = mock_tables
            mock_get_vs.return_value = mock_vs

            result = _get_known_columns("users")

        assert result == {"id", "username"}

    def test_handles_string_columns(self):
        """Test handling columns as plain strings instead of dicts."""
        mock_tables = [
            {
                "metadata": {
                    "table_name": "users",
                    "columns": ["id", "name", "email"],
                }
            },
        ]

        with patch(
            "text_to_sql.agents.tools.exploration_tools.get_vector_store_service"
        ) as mock_get_vs:
            mock_vs = MagicMock()
            mock_vs.list_database_info.return_value = mock_tables
            mock_get_vs.return_value = mock_vs

            result = _get_known_columns("users")

        assert result == {"id", "name", "email"}

    def test_table_not_found(self):
        """Test behavior when table is not found."""
        mock_tables = [
            {"metadata": {"table_name": "other_table", "columns": [{"name": "id"}]}},
        ]

        with patch(
            "text_to_sql.agents.tools.exploration_tools.get_vector_store_service"
        ) as mock_get_vs:
            mock_vs = MagicMock()
            mock_vs.list_database_info.return_value = mock_tables
            mock_get_vs.return_value = mock_vs

            result = _get_known_columns("nonexistent")

        assert result == set()

    def test_handles_empty_column_names(self):
        """Test filtering out empty column names."""
        mock_tables = [
            {
                "metadata": {
                    "table_name": "users",
                    "columns": [{"name": "id"}, {"name": ""}, {"name": None}],
                }
            },
        ]

        with patch(
            "text_to_sql.agents.tools.exploration_tools.get_vector_store_service"
        ) as mock_get_vs:
            mock_vs = MagicMock()
            mock_vs.list_database_info.return_value = mock_tables
            mock_get_vs.return_value = mock_vs

            result = _get_known_columns("users")

        assert result == {"id"}


class TestExploreColumnValues:
    """Test the explore_column_values tool function."""

    @pytest.fixture
    def mock_known_tables(self):
        """Mock known tables for testing."""
        return {"aws_rds", "aws_ec2", "users"}

    @pytest.fixture
    def mock_known_columns(self):
        """Mock known columns for aws_rds."""
        return {"id", "engine", "instance_type", "status"}

    @pytest.mark.asyncio
    async def test_invalid_table_name_rejected(self):
        """Test that invalid table names are rejected."""
        result = await explore_column_values.ainvoke(
            {"table_name": "users; DROP TABLE", "column_name": "id"}
        )

        assert result["success"] is False
        assert "Invalid table name" in result["error"]

    @pytest.mark.asyncio
    async def test_invalid_column_name_rejected(self):
        """Test that invalid column names are rejected."""
        with patch(
            "text_to_sql.agents.tools.exploration_tools._get_known_tables"
        ) as mock_tables:
            mock_tables.return_value = {"users"}

            result = await explore_column_values.ainvoke(
                {"table_name": "users", "column_name": "id; DROP TABLE"}
            )

        assert result["success"] is False
        assert "Invalid column name" in result["error"]

    @pytest.mark.asyncio
    async def test_schema_prefix_normalized(self):
        """Test that schema prefix is stripped before validation."""
        mock_rows = [{"value": "postgres", "count": 100}]
        mock_count = {"total": 5}

        with patch(
            "text_to_sql.agents.tools.exploration_tools._get_known_tables"
        ) as mock_tables, patch(
            "text_to_sql.agents.tools.exploration_tools._get_known_columns"
        ) as mock_cols, patch(
            "text_to_sql.agents.tools.exploration_tools.get_database_service"
        ) as mock_db:
            mock_tables.return_value = {"aws_rds"}
            mock_cols.return_value = {"engine"}

            mock_conn = AsyncMock()
            mock_conn.fetch = AsyncMock(return_value=mock_rows)
            mock_conn.fetchrow = AsyncMock(return_value=mock_count)

            mock_db_service = MagicMock()
            mock_db_service.get_connection = MagicMock(
                return_value=AsyncMock(
                    __aenter__=AsyncMock(return_value=mock_conn),
                    __aexit__=AsyncMock(),
                )
            )
            mock_db.return_value = mock_db_service

            result = await explore_column_values.ainvoke(
                {"table_name": "public.aws_rds", "column_name": "engine"}
            )

        assert result["success"] is True
        assert result["table"] == "aws_rds"  # Schema stripped

    @pytest.mark.asyncio
    async def test_unknown_table_rejected(self):
        """Test that unknown tables are rejected with helpful message."""
        with patch(
            "text_to_sql.agents.tools.exploration_tools._get_known_tables"
        ) as mock_tables:
            mock_tables.return_value = {"aws_rds", "aws_ec2"}

            result = await explore_column_values.ainvoke(
                {"table_name": "nonexistent", "column_name": "id"}
            )

        assert result["success"] is False
        assert "not found" in result["error"]
        assert "Available tables" in result["error"]

    @pytest.mark.asyncio
    async def test_unknown_column_rejected(self):
        """Test that unknown columns are rejected with helpful message."""
        with patch(
            "text_to_sql.agents.tools.exploration_tools._get_known_tables"
        ) as mock_tables, patch(
            "text_to_sql.agents.tools.exploration_tools._get_known_columns"
        ) as mock_cols:
            mock_tables.return_value = {"aws_rds"}
            mock_cols.return_value = {"id", "engine", "status"}

            result = await explore_column_values.ainvoke(
                {"table_name": "aws_rds", "column_name": "nonexistent_column"}
            )

        assert result["success"] is False
        assert "Column 'nonexistent_column' not found" in result["error"]
        assert "Available columns" in result["error"]

    @pytest.mark.asyncio
    async def test_successful_exploration(self):
        """Test successful column value exploration."""
        mock_rows = [
            {"value": "postgres", "count": 150},
            {"value": "mysql", "count": 100},
            {"value": "mariadb", "count": 50},
        ]
        mock_count = {"total": 3}

        with patch(
            "text_to_sql.agents.tools.exploration_tools._get_known_tables"
        ) as mock_tables, patch(
            "text_to_sql.agents.tools.exploration_tools._get_known_columns"
        ) as mock_cols, patch(
            "text_to_sql.agents.tools.exploration_tools.get_database_service"
        ) as mock_db:
            mock_tables.return_value = {"aws_rds"}
            mock_cols.return_value = {"engine"}

            mock_conn = AsyncMock()
            mock_conn.fetch = AsyncMock(return_value=mock_rows)
            mock_conn.fetchrow = AsyncMock(return_value=mock_count)

            mock_db_service = MagicMock()
            mock_db_service.get_connection = MagicMock(
                return_value=AsyncMock(
                    __aenter__=AsyncMock(return_value=mock_conn),
                    __aexit__=AsyncMock(),
                )
            )
            mock_db.return_value = mock_db_service

            result = await explore_column_values.ainvoke(
                {"table_name": "aws_rds", "column_name": "engine"}
            )

        assert result["success"] is True
        assert result["table"] == "aws_rds"
        assert result["column"] == "engine"
        assert result["total_distinct"] == 3
        assert len(result["values"]) == 3
        assert result["values"][0]["value"] == "postgres"
        assert result["values"][0]["count"] == 150

    @pytest.mark.asyncio
    async def test_exploration_with_search_term(self):
        """Test exploration with search term filter."""
        mock_rows = [{"value": "postgres", "count": 150}]
        mock_count = {"total": 1}

        with patch(
            "text_to_sql.agents.tools.exploration_tools._get_known_tables"
        ) as mock_tables, patch(
            "text_to_sql.agents.tools.exploration_tools._get_known_columns"
        ) as mock_cols, patch(
            "text_to_sql.agents.tools.exploration_tools.get_database_service"
        ) as mock_db:
            mock_tables.return_value = {"aws_rds"}
            mock_cols.return_value = {"engine"}

            mock_conn = AsyncMock()
            mock_conn.fetch = AsyncMock(return_value=mock_rows)
            mock_conn.fetchrow = AsyncMock(return_value=mock_count)

            mock_db_service = MagicMock()
            mock_db_service.get_connection = MagicMock(
                return_value=AsyncMock(
                    __aenter__=AsyncMock(return_value=mock_conn),
                    __aexit__=AsyncMock(),
                )
            )
            mock_db.return_value = mock_db_service

            result = await explore_column_values.ainvoke(
                {
                    "table_name": "aws_rds",
                    "column_name": "engine",
                    "search_term": "postgres",
                }
            )

        assert result["success"] is True
        assert result["search_term"] == "postgres"
        # Verify search_term was passed to the query
        mock_conn.fetch.assert_called_once()
        call_args = mock_conn.fetch.call_args
        assert "postgres" in call_args[0]  # search_term passed as parameter

    @pytest.mark.asyncio
    async def test_limit_enforcement(self):
        """Test that limit is enforced within bounds."""
        mock_rows = []
        mock_count = {"total": 0}

        with patch(
            "text_to_sql.agents.tools.exploration_tools._get_known_tables"
        ) as mock_tables, patch(
            "text_to_sql.agents.tools.exploration_tools._get_known_columns"
        ) as mock_cols, patch(
            "text_to_sql.agents.tools.exploration_tools.get_database_service"
        ) as mock_db:
            mock_tables.return_value = {"aws_rds"}
            mock_cols.return_value = {"engine"}

            mock_conn = AsyncMock()
            mock_conn.fetch = AsyncMock(return_value=mock_rows)
            mock_conn.fetchrow = AsyncMock(return_value=mock_count)

            mock_db_service = MagicMock()
            mock_db_service.get_connection = MagicMock(
                return_value=AsyncMock(
                    __aenter__=AsyncMock(return_value=mock_conn),
                    __aexit__=AsyncMock(),
                )
            )
            mock_db.return_value = mock_db_service

            # Test with limit above max (should be capped to 50)
            result = await explore_column_values.ainvoke(
                {"table_name": "aws_rds", "column_name": "engine", "limit": 1000}
            )

        assert result["success"] is True
        # Verify LIMIT 50 was used in the query
        call_sql = mock_conn.fetch.call_args[0][0]
        assert "LIMIT 50" in call_sql

    @pytest.mark.asyncio
    async def test_limit_minimum_enforcement(self):
        """Test that limit is enforced to minimum of 1."""
        mock_rows = []
        mock_count = {"total": 0}

        with patch(
            "text_to_sql.agents.tools.exploration_tools._get_known_tables"
        ) as mock_tables, patch(
            "text_to_sql.agents.tools.exploration_tools._get_known_columns"
        ) as mock_cols, patch(
            "text_to_sql.agents.tools.exploration_tools.get_database_service"
        ) as mock_db:
            mock_tables.return_value = {"aws_rds"}
            mock_cols.return_value = {"engine"}

            mock_conn = AsyncMock()
            mock_conn.fetch = AsyncMock(return_value=mock_rows)
            mock_conn.fetchrow = AsyncMock(return_value=mock_count)

            mock_db_service = MagicMock()
            mock_db_service.get_connection = MagicMock(
                return_value=AsyncMock(
                    __aenter__=AsyncMock(return_value=mock_conn),
                    __aexit__=AsyncMock(),
                )
            )
            mock_db.return_value = mock_db_service

            # Test with negative limit (should be set to 1)
            result = await explore_column_values.ainvoke(
                {"table_name": "aws_rds", "column_name": "engine", "limit": -5}
            )

        assert result["success"] is True
        call_sql = mock_conn.fetch.call_args[0][0]
        assert "LIMIT 1" in call_sql

    @pytest.mark.asyncio
    async def test_database_error_handling(self):
        """Test handling of database errors."""
        with patch(
            "text_to_sql.agents.tools.exploration_tools._get_known_tables"
        ) as mock_tables, patch(
            "text_to_sql.agents.tools.exploration_tools._get_known_columns"
        ) as mock_cols, patch(
            "text_to_sql.agents.tools.exploration_tools.get_database_service"
        ) as mock_db:
            mock_tables.return_value = {"aws_rds"}
            mock_cols.return_value = {"engine"}

            mock_conn = AsyncMock()
            mock_conn.fetch = AsyncMock(side_effect=Exception("Connection failed"))

            mock_db_service = MagicMock()
            mock_db_service.get_connection = MagicMock(
                return_value=AsyncMock(
                    __aenter__=AsyncMock(return_value=mock_conn),
                    __aexit__=AsyncMock(),
                )
            )
            mock_db.return_value = mock_db_service

            result = await explore_column_values.ainvoke(
                {"table_name": "aws_rds", "column_name": "engine"}
            )

        assert result["success"] is False
        assert "Exploration failed" in result["error"]

    @pytest.mark.asyncio
    async def test_column_validation_skipped_when_no_columns_known(self):
        """Test that column validation is skipped when schema has no columns."""
        mock_rows = [{"value": "test", "count": 1}]
        mock_count = {"total": 1}

        with patch(
            "text_to_sql.agents.tools.exploration_tools._get_known_tables"
        ) as mock_tables, patch(
            "text_to_sql.agents.tools.exploration_tools._get_known_columns"
        ) as mock_cols, patch(
            "text_to_sql.agents.tools.exploration_tools.get_database_service"
        ) as mock_db:
            mock_tables.return_value = {"aws_rds"}
            mock_cols.return_value = set()  # Empty columns - validation skipped

            mock_conn = AsyncMock()
            mock_conn.fetch = AsyncMock(return_value=mock_rows)
            mock_conn.fetchrow = AsyncMock(return_value=mock_count)

            mock_db_service = MagicMock()
            mock_db_service.get_connection = MagicMock(
                return_value=AsyncMock(
                    __aenter__=AsyncMock(return_value=mock_conn),
                    __aexit__=AsyncMock(),
                )
            )
            mock_db.return_value = mock_db_service

            # Should succeed even with unknown column when schema is empty
            result = await explore_column_values.ainvoke(
                {"table_name": "aws_rds", "column_name": "any_column"}
            )

        assert result["success"] is True


class TestGetExplorationTools:
    """Test the get_exploration_tools function."""

    def test_returns_explore_column_values(self):
        """Test that explore_column_values is included."""
        tools = get_exploration_tools()
        assert len(tools) == 1
        assert tools[0] == explore_column_values

    def test_tools_have_ainvoke(self):
        """Test that all tools have ainvoke method."""
        tools = get_exploration_tools()
        for tool in tools:
            assert hasattr(tool, "ainvoke"), f"Tool should have ainvoke method"
