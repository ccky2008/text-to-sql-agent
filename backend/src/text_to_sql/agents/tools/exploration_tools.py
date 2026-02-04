"""Value exploration tools for discovering correct database values."""

import re
from typing import Any

from langchain_core.tools import tool

from text_to_sql.services.database import get_database_service
from text_to_sql.services.vector_store import get_vector_store_service


def _validate_identifier(name: str) -> bool:
    """Validate that a name is a safe SQL identifier.

    Only allows alphanumeric characters and underscores.
    Prevents SQL injection in table/column names.
    """
    return bool(re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', name))


def _normalize_table_name(table_name: str) -> str:
    """Normalize table name by stripping schema prefix if present.

    Handles cases where LLM passes schema-qualified names like 'public.aws_rds'.
    Returns just the table name portion.

    Args:
        table_name: Table name, possibly with schema prefix (e.g., "public.aws_rds")

    Returns:
        Just the table name without schema (e.g., "aws_rds")
    """
    if "." in table_name:
        # Split on dot and take the last part (table name)
        parts = table_name.split(".")
        return parts[-1]
    return table_name


def _get_known_tables() -> set[str]:
    """Get set of known table names from vector store."""
    vector_store = get_vector_store_service()
    db_tables = vector_store.list_database_info(limit=1000)
    return {
        t["metadata"].get("table_name", "").lower()
        for t in db_tables
        if t.get("metadata", {}).get("table_name")
    }


@tool
async def explore_column_values(
    table_name: str,
    column_name: str,
    search_term: str | None = None,
    limit: int = 20,
) -> dict[str, Any]:
    """Explore distinct values in a column to find the correct database value.

    Use this tool BEFORE generating a final SQL query when you need to discover
    the actual values stored in the database. This is especially useful when:
    - User uses descriptive terms that may not match exact database values
    - Filtering on categorical columns (engine, instance_type, region, status, etc.)
    - User asks about specific vendors, products, or types

    Examples:
    - User says "PostgreSQL" -> explore engine column -> find "postgres"
    - User says "large instances" -> explore instance_type -> find "t2.large", "m5.large"
    - User says "running instances" -> explore status -> find actual status values

    Args:
        table_name: The table to query (e.g., "aws_rds", "aws_ec2")
        column_name: The column to get distinct values from (e.g., "engine", "instance_type")
        search_term: Optional term to filter values (case-insensitive partial match)
        limit: Maximum number of distinct values to return (default: 20)

    Returns:
        Dictionary with:
        - success: Whether the exploration succeeded
        - values: List of distinct values found (with counts)
        - total_distinct: Total number of distinct values
        - search_term: The search term used (if any)
        - error: Error message if exploration failed
    """
    # Normalize table name (strip schema prefix if present, e.g., "public.aws_rds" -> "aws_rds")
    table_name = _normalize_table_name(table_name)

    # Validate inputs
    if not _validate_identifier(table_name):
        return {
            "success": False,
            "values": [],
            "total_distinct": 0,
            "search_term": search_term,
            "error": f"Invalid table name: {table_name}",
        }

    if not _validate_identifier(column_name):
        return {
            "success": False,
            "values": [],
            "total_distinct": 0,
            "search_term": search_term,
            "error": f"Invalid column name: {column_name}",
        }

    # Validate table exists in known tables
    known_tables = _get_known_tables()
    if table_name.lower() not in known_tables:
        return {
            "success": False,
            "values": [],
            "total_distinct": 0,
            "search_term": search_term,
            "error": (
                f"Table '{table_name}' not found. "
                f"Available tables include: {', '.join(sorted(list(known_tables)[:10]))}"
            ),
        }

    # Enforce reasonable limit
    limit = min(max(limit, 1), 50)

    db_service = get_database_service()

    try:
        # Build the exploration query
        # Using double quotes for identifiers to handle case sensitivity
        if search_term:
            # Filter with ILIKE for case-insensitive partial match
            # Note: We use string formatting here but the values are validated above
            sql = f"""
                SELECT "{column_name}" as value, COUNT(*) as count
                FROM "{table_name}"
                WHERE "{column_name}" IS NOT NULL
                  AND "{column_name}"::TEXT ILIKE '%' || $1 || '%'
                GROUP BY "{column_name}"
                ORDER BY count DESC
                LIMIT {limit}
            """
            # For parameterized query we need to use the connection directly
            async with db_service.get_connection() as conn:
                rows = await conn.fetch(sql, search_term)
        else:
            sql = f"""
                SELECT "{column_name}" as value, COUNT(*) as count
                FROM "{table_name}"
                WHERE "{column_name}" IS NOT NULL
                GROUP BY "{column_name}"
                ORDER BY count DESC
                LIMIT {limit}
            """
            async with db_service.get_connection() as conn:
                rows = await conn.fetch(sql)

        # Get total distinct count
        count_sql = f"""
            SELECT COUNT(DISTINCT "{column_name}") as total
            FROM "{table_name}"
            WHERE "{column_name}" IS NOT NULL
        """
        async with db_service.get_connection() as conn:
            count_row = await conn.fetchrow(count_sql)
            total_distinct = count_row["total"] if count_row else 0

        # Format results
        values = [
            {"value": str(row["value"]), "count": row["count"]}
            for row in rows
        ]

        return {
            "success": True,
            "values": values,
            "total_distinct": total_distinct,
            "search_term": search_term,
            "table": table_name,
            "column": column_name,
            "error": None,
        }

    except Exception as e:
        return {
            "success": False,
            "values": [],
            "total_distinct": 0,
            "search_term": search_term,
            "error": f"Exploration failed: {str(e)}",
        }


def get_exploration_tools() -> list:
    """Get all exploration tools."""
    return [explore_column_values]
