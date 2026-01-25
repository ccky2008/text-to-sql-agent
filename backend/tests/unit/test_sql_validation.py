"""Tests for SQL validation."""

import pytest

from text_to_sql.agents.tools.sql_tools import validate_sql
from text_to_sql.core.types import SQLCategory


class TestValidateSQL:
    """Test SQL validation functionality."""

    def test_valid_select(self):
        """Test that valid SELECT queries pass validation."""
        sql = "SELECT id, name FROM users WHERE active = true"
        result = validate_sql(sql)

        assert result.is_valid
        assert result.statement_type == SQLCategory.SELECT
        assert len(result.errors) == 0

    def test_valid_select_with_join(self):
        """Test SELECT with JOIN."""
        sql = """
        SELECT u.name, o.total
        FROM users u
        JOIN orders o ON u.id = o.user_id
        WHERE o.status = 'completed'
        """
        result = validate_sql(sql)

        assert result.is_valid
        assert result.statement_type == SQLCategory.SELECT

    def test_valid_cte(self):
        """Test valid CTE (WITH) query."""
        sql = """
        WITH active_users AS (
            SELECT id, name FROM users WHERE active = true
        )
        SELECT * FROM active_users
        """
        result = validate_sql(sql)

        assert result.is_valid
        # CTEs are parsed as SELECT since they always end with a SELECT
        assert result.statement_type in (SQLCategory.WITH, SQLCategory.SELECT)

    def test_block_drop(self):
        """Test that DROP statements are blocked."""
        sql = "DROP TABLE users"
        result = validate_sql(sql)

        assert not result.is_valid
        assert any("DROP" in err for err in result.errors)

    def test_block_delete(self):
        """Test that DELETE statements are blocked."""
        sql = "DELETE FROM users WHERE id = 1"
        result = validate_sql(sql)

        assert not result.is_valid
        assert any("DELETE" in err for err in result.errors)

    def test_block_insert(self):
        """Test that INSERT statements are blocked."""
        sql = "INSERT INTO users (name) VALUES ('test')"
        result = validate_sql(sql)

        assert not result.is_valid
        assert any("INSERT" in err for err in result.errors)

    def test_block_update(self):
        """Test that UPDATE statements are blocked."""
        sql = "UPDATE users SET name = 'test' WHERE id = 1"
        result = validate_sql(sql)

        assert not result.is_valid
        assert any("UPDATE" in err for err in result.errors)

    def test_block_truncate(self):
        """Test that TRUNCATE statements are blocked."""
        sql = "TRUNCATE TABLE users"
        result = validate_sql(sql)

        assert not result.is_valid
        assert any("TRUNCATE" in err for err in result.errors)

    def test_block_alter(self):
        """Test that ALTER statements are blocked."""
        sql = "ALTER TABLE users ADD COLUMN email VARCHAR(255)"
        result = validate_sql(sql)

        assert not result.is_valid
        assert any("ALTER" in err for err in result.errors)

    def test_syntax_error(self):
        """Test that syntax errors are caught."""
        sql = "SELEC * FORM users"
        result = validate_sql(sql)

        assert not result.is_valid
        assert len(result.errors) > 0

    def test_warning_select_star(self):
        """Test warning for SELECT *."""
        sql = "SELECT * FROM users"
        result = validate_sql(sql)

        assert result.is_valid
        assert any("SELECT *" in w for w in result.warnings)

    def test_warning_no_limit(self):
        """Test warning for missing LIMIT."""
        sql = "SELECT id, name FROM users"
        result = validate_sql(sql)

        assert result.is_valid
        assert any("LIMIT" in w for w in result.warnings)

    def test_no_warning_with_limit(self):
        """Test no warning when LIMIT is present."""
        sql = "SELECT id, name FROM users LIMIT 10"
        result = validate_sql(sql)

        assert result.is_valid
        assert not any("LIMIT" in w for w in result.warnings)

    def test_case_insensitive_blocking(self):
        """Test that dangerous keywords are blocked regardless of case."""
        sqls = [
            "drop table users",
            "DROP TABLE users",
            "Drop Table Users",
        ]

        for sql in sqls:
            result = validate_sql(sql)
            assert not result.is_valid

    def test_complex_valid_query(self):
        """Test a complex but valid query."""
        sql = """
        WITH monthly_sales AS (
            SELECT
                DATE_TRUNC('month', created_at) AS month,
                SUM(amount) AS total_sales
            FROM orders
            WHERE status = 'completed'
            GROUP BY DATE_TRUNC('month', created_at)
        ),
        ranked_months AS (
            SELECT
                month,
                total_sales,
                RANK() OVER (ORDER BY total_sales DESC) as sales_rank
            FROM monthly_sales
        )
        SELECT month, total_sales, sales_rank
        FROM ranked_months
        WHERE sales_rank <= 5
        ORDER BY sales_rank
        LIMIT 5
        """
        result = validate_sql(sql)

        assert result.is_valid
        # CTEs are parsed as SELECT since they always end with a SELECT
        assert result.statement_type in (SQLCategory.WITH, SQLCategory.SELECT)
        assert len(result.warnings) == 0
