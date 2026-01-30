"""Tool execution node for LLM-driven tool calls."""

import logging
from typing import Any

from text_to_sql.agents.state import AgentState
from text_to_sql.agents.tools.sql_tools import execute_sql_query
from text_to_sql.config import get_settings

logger = logging.getLogger(__name__)

# Registry of available tools
TOOL_REGISTRY = {
    "execute_sql_query": execute_sql_query,
}


async def tool_executor_node(state: AgentState) -> dict[str, Any]:
    """Execute pending tool calls from the LLM.

    This node processes tool calls requested by the LLM during SQL generation.
    It dispatches each tool call to the appropriate handler and collects results.

    Currently supports:
    - execute_sql_query: Execute SQL and return paginated results

    Returns:
        Updated state with tool execution results.
    """
    pending = state.get("pending_tool_call")
    if not pending:
        return {"tool_results": [], "pending_tool_call": None}

    tool_name = pending.get("name", "")
    tool_args = pending.get("args", {})
    tool_id = pending.get("id", "")

    # Look up the tool
    tool_fn = TOOL_REGISTRY.get(tool_name)
    if not tool_fn:
        error_result = {
            "tool_call_id": tool_id,
            "tool_name": tool_name,
            "success": False,
            "error": f"Unknown tool: {tool_name}",
            "result": None,
        }
        return {
            "tool_results": state.get("tool_results", []) + [error_result],
            "pending_tool_call": None,
        }

    # Inject session_id if the tool accepts it
    if "session_id" not in tool_args:
        tool_args["session_id"] = state.get("session_id", "default")

    # Execute the tool
    try:
        # Tools decorated with @tool return dicts directly
        result = await tool_fn.ainvoke(tool_args)

        tool_result = {
            "tool_call_id": tool_id,
            "tool_name": tool_name,
            "success": result.get("success", False),
            "error": result.get("error"),
            "result": result,
        }

        existing_results = state.get("tool_results", [])
        state_updates: dict[str, Any] = {
            "tool_results": existing_results + [tool_result],
            "pending_tool_call": None,
        }

        # For SQL execution, update the main execution state
        if tool_name == "execute_sql_query":
            if result.get("success"):
                settings = get_settings()
                total_count = result.get("total_count")
                state_updates.update({
                    "executed": True,
                    "results": result.get("rows"),
                    "row_count": result.get("row_count"),
                    "columns": result.get("columns"),
                    "total_count": total_count,
                    "has_more_results": result.get("has_more", False),
                    "query_token": result.get("query_token"),
                    "csv_available": True,
                    "csv_exceeds_limit": (
                        total_count is not None and total_count > settings.csv_max_rows
                    ),
                    "execution_error": None,
                })
            else:
                state_updates.update({
                    "executed": False,
                    "execution_error": result.get("error"),
                })

        return state_updates

    except Exception as e:
        logger.exception("Tool execution failed for %s: %s", tool_name, e)
        error_result = {
            "tool_call_id": tool_id,
            "tool_name": tool_name,
            "success": False,
            "error": str(e),
            "result": None,
        }
        existing_results = state.get("tool_results", [])
        return {
            "tool_results": existing_results + [error_result],
            "pending_tool_call": None,
            "execution_error": str(e),
        }
