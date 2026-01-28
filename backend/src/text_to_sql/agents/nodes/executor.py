"""SQL execution node."""

from text_to_sql.agents.state import AgentState
from text_to_sql.config import get_settings
from text_to_sql.services.database import get_database_service
from text_to_sql.services.query_cache import get_query_cache


async def executor_node(state: AgentState) -> dict:
    """Execute the validated SQL query with pagination support.

    Only executes if the SQL is valid and execution is requested.
    First runs a COUNT query to get total rows, then runs paginated query.
    """
    sql = state.get("generated_sql")

    # Base error response (immutable pattern - create fresh dict each return)
    def make_error(msg: str) -> dict:
        return {
            "executed": False,
            "results": None,
            "row_count": None,
            "columns": None,
            "execution_error": msg,
            "total_count": None,
            "has_more_results": False,
            "csv_available": False,
            "csv_exceeds_limit": False,
            "query_token": None,
        }

    if not sql:
        return make_error("No SQL query to execute")

    if not state.get("is_valid", False):
        return make_error("SQL validation failed")

    settings = get_settings()
    db_service = get_database_service()

    # Get pagination parameters from state
    page = state.get("page", 1)
    page_size = state.get("page_size", settings.pagination_default_limit)
    offset = (page - 1) * page_size

    try:
        # First, get total count (with timeout protection)
        total_count = await db_service.execute_count_query(sql)

        # Then execute paginated query
        result = await db_service.execute_query_paginated(
            sql, offset=offset, limit=page_size
        )

        if result.success:
            # Determine if there are more results
            has_more = (
                total_count is not None
                and (offset + len(result.rows or [])) < total_count
            )
            # Check if CSV would exceed limit
            csv_exceeds = (
                total_count is not None and total_count > settings.csv_max_rows
            )

            # Generate query token for CSV downloads
            query_cache = get_query_cache()
            query_token = query_cache.store(sql, state.get("session_id", ""))

            return {
                "executed": True,
                "results": result.rows,
                "row_count": result.row_count,
                "columns": result.columns,
                "execution_error": None,
                "total_count": total_count,
                "has_more_results": has_more,
                "csv_available": True,
                "csv_exceeds_limit": csv_exceeds,
                "query_token": query_token,
            }
        else:
            return make_error(result.error or "Query execution failed")

    except Exception as e:
        return make_error(str(e))
