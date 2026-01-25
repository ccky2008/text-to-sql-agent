"""SQL execution node."""

from text_to_sql.agents.state import AgentState
from text_to_sql.config import get_settings
from text_to_sql.services.database import get_database_service


async def executor_node(state: AgentState) -> dict:
    """Execute the validated SQL query.

    Only executes if the SQL is valid and execution is requested.
    """
    sql = state.get("generated_sql")

    if not sql:
        return {
            "executed": False,
            "results": None,
            "row_count": None,
            "columns": None,
            "execution_error": "No SQL query to execute",
        }

    if not state.get("is_valid", False):
        return {
            "executed": False,
            "results": None,
            "row_count": None,
            "columns": None,
            "execution_error": "SQL validation failed",
        }

    settings = get_settings()
    db_service = get_database_service()

    try:
        result = await db_service.execute_query(sql, max_rows=settings.sql_max_rows)

        if result.success:
            return {
                "executed": True,
                "results": result.rows,
                "row_count": result.row_count,
                "columns": result.columns,
                "execution_error": None,
            }
        else:
            return {
                "executed": False,
                "results": None,
                "row_count": None,
                "columns": None,
                "execution_error": result.error,
            }
    except Exception as e:
        return {
            "executed": False,
            "results": None,
            "row_count": None,
            "columns": None,
            "execution_error": str(e),
        }
