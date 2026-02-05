"""SQL execution node."""

import re

from text_to_sql.agents.state import AgentState
from text_to_sql.agents.streaming import get_writer
from text_to_sql.config import get_settings
from text_to_sql.services.database import get_database_service
from text_to_sql.services.query_cache import get_query_cache


def _make_user_friendly_error(error: str) -> tuple[str, str | None]:
    """Convert database errors to user-friendly messages.

    Returns:
        Tuple of (user_friendly_message, special_response_type)
    """
    error_lower = error.lower()

    # Check for "relation does not exist" (table not found) errors
    table_not_found = re.search(
        r'relation ["\']?(\w+)["\']? does not exist', error_lower
    )
    if table_not_found or ("relation" in error_lower and "does not exist" in error_lower):
        table_name = table_not_found.group(1) if table_not_found else "requested"
        return (
            f"The requested resource type '{table_name}' does not exist in our database. "
            "We cannot provide information about resources that are not tracked. "
            "Please try asking about a different resource type.",
            "RESOURCE_NOT_FOUND",
        )

    # Check for "column does not exist" errors
    column_not_found = re.search(
        r'column ["\']?(\w+)["\']? does not exist', error_lower
    )
    if column_not_found or ("column" in error_lower and "does not exist" in error_lower):
        column_name = column_not_found.group(1) if column_not_found else "requested"
        return (
            f"The requested field '{column_name}' does not exist for this resource type. "
            "Please check the available fields or try a different query.",
            "RESOURCE_NOT_FOUND",
        )

    # Check for permission denied errors
    if "permission denied" in error_lower:
        return (
            "Access to the requested resource is not permitted. "
            "Please try asking about a different resource type.",
            None,
        )

    # Default: return original error
    return error, None


async def executor_node(state: AgentState) -> dict:
    """Execute the validated SQL query with pagination support.

    Only executes if the SQL is valid and execution is requested.
    First runs a COUNT query to get total rows, then runs paginated query.
    """
    writer = get_writer()
    writer({"type": "step_started", "step": "executor", "label": "Executing query"})

    sql = state.get("generated_sql")

    # Base error response (immutable pattern - create fresh dict each return)
    def make_error(msg: str, special_type: str | None = None) -> dict:
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
            "special_response_type": special_type,
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
            # Convert database error to user-friendly message
            user_msg, special_type = _make_user_friendly_error(
                result.error or "Query execution failed"
            )
            return make_error(user_msg, special_type)

    except Exception as e:
        # Convert exception to user-friendly message
        user_msg, special_type = _make_user_friendly_error(str(e))
        return make_error(user_msg, special_type)
