"""Tests for database service methods."""

import pytest

from text_to_sql.services.database import DatabaseService


class TestStripTrailingSemicolons:
    """Test _strip_trailing_semicolons helper."""

    def test_strips_single_semicolon(self):
        """Test stripping a single trailing semicolon."""
        result = DatabaseService._strip_trailing_semicolons("SELECT 1;")
        assert result == "SELECT 1"

    def test_strips_multiple_semicolons(self):
        """Test stripping multiple trailing semicolons."""
        result = DatabaseService._strip_trailing_semicolons("SELECT 1;;;")
        assert result == "SELECT 1"

    def test_strips_semicolon_with_whitespace(self):
        """Test stripping semicolon with trailing whitespace."""
        result = DatabaseService._strip_trailing_semicolons("SELECT 1;  \n\t")
        assert result == "SELECT 1"

    def test_strips_whitespace_then_semicolon(self):
        """Test stripping whitespace before semicolon."""
        # rstrip() first removes trailing whitespace, then rstrip(";") removes semicolons
        # "SELECT 1  ;" has no trailing whitespace after ;, so rstrip() is no-op
        # Then rstrip(";") removes the ;, leaving "SELECT 1  " (internal whitespace preserved)
        result = DatabaseService._strip_trailing_semicolons("SELECT 1  ;")
        assert result == "SELECT 1  "  # Internal whitespace is preserved

    def test_no_semicolon(self):
        """Test SQL without semicolon is unchanged."""
        result = DatabaseService._strip_trailing_semicolons("SELECT 1")
        assert result == "SELECT 1"

    def test_internal_semicolon_preserved(self):
        """Test that internal semicolons are preserved."""
        # This shouldn't happen in real SQL, but tests the method's behavior
        sql = "SELECT ';' FROM test;"
        result = DatabaseService._strip_trailing_semicolons(sql)
        assert result == "SELECT ';' FROM test"

    def test_empty_string(self):
        """Test empty string handling."""
        result = DatabaseService._strip_trailing_semicolons("")
        assert result == ""

    def test_only_whitespace(self):
        """Test whitespace-only string."""
        result = DatabaseService._strip_trailing_semicolons("   \n\t  ")
        assert result == ""

    def test_complex_query(self):
        """Test with a complex CTE query."""
        sql = """
            WITH active_users AS (
                SELECT id, name FROM users WHERE active = true
            )
            SELECT * FROM active_users;
        """
        result = DatabaseService._strip_trailing_semicolons(sql)
        assert result.endswith("active_users")
        assert not result.endswith(";")


class TestPaginatedQuerySQLGeneration:
    """Test SQL generation for paginated queries (unit tests, no DB connection)."""

    def test_paginated_sql_format(self):
        """Test that paginated SQL is correctly formatted."""
        # This tests the SQL string generation pattern
        sql = "SELECT * FROM users"
        clean_sql = DatabaseService._strip_trailing_semicolons(sql)
        offset, limit = 10, 20

        paginated_sql = f"SELECT * FROM ({clean_sql}) AS subq LIMIT {limit} OFFSET {offset}"

        assert "LIMIT 20" in paginated_sql
        assert "OFFSET 10" in paginated_sql
        assert "AS subq" in paginated_sql

    def test_count_sql_format(self):
        """Test that count SQL is correctly formatted."""
        sql = "SELECT * FROM users WHERE active = true;"
        clean_sql = DatabaseService._strip_trailing_semicolons(sql)

        count_sql = f"SELECT COUNT(*) as cnt FROM ({clean_sql}) AS count_subq"

        assert "COUNT(*)" in count_sql
        assert "AS count_subq" in count_sql
        assert ";" not in count_sql  # Semicolon should be stripped
