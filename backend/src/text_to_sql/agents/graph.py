"""LangGraph agent graph definition."""

from typing import Literal

from langgraph.graph import END, StateGraph

from text_to_sql.agents.nodes.executor import executor_node
from text_to_sql.agents.nodes.responder import responder_node
from text_to_sql.agents.nodes.retrieval import retrieval_node
from text_to_sql.agents.nodes.sql_generator import sql_generator_node
from text_to_sql.agents.nodes.tool_executor import tool_executor_node
from text_to_sql.agents.nodes.validator import validator_node
from text_to_sql.agents.state import AgentState
from text_to_sql.services.checkpointer import get_session_manager

# Maximum retry attempts for SQL regeneration
MAX_RETRIES = 2

# Maximum exploration queries per request (to prevent infinite loops)
MAX_EXPLORATIONS = 3


def should_validate_or_respond(
    state: AgentState,
) -> Literal["validator", "responder", "tool_executor"]:
    """Determine if SQL should be validated, tool executed, or skip to response.

    Routes to tool_executor if LLM requested a tool call.
    Routes directly to responder if this is a special response (out-of-scope, read-only).
    Otherwise, routes to validator for normal SQL processing.
    """
    # Check if there's a pending tool call
    if state.get("pending_tool_call"):
        return "tool_executor"

    special_type = state.get("special_response_type")
    if special_type in ("OUT_OF_SCOPE", "READ_ONLY"):
        return "responder"
    return "validator"


def should_execute(state: AgentState) -> Literal["executor", "responder"]:
    """Determine if SQL should be executed.

    Routes to executor if valid, otherwise to responder.
    """
    if state.get("is_valid", False):
        return "executor"
    return "responder"


def should_retry(state: AgentState) -> Literal["sql_generator", "responder"]:
    """Determine if SQL generation should be retried.

    Retries if validation failed and retry count is below threshold.
    Does not retry for special response types (out-of-scope, read-only, resource not found).
    """
    special_type = state.get("special_response_type")
    if special_type in ("OUT_OF_SCOPE", "READ_ONLY", "RESOURCE_NOT_FOUND"):
        return "responder"

    if not state.get("is_valid", False) and state.get("retry_count", 0) < MAX_RETRIES:
        return "sql_generator"
    return "responder"


def increment_retry(state: AgentState) -> dict:
    """Increment retry counter."""
    return {"retry_count": state.get("retry_count", 0) + 1}


def route_after_tool_execution(
    state: AgentState,
) -> Literal["sql_generator", "responder"]:
    """Determine next step after tool execution.

    Routes back to sql_generator if this was an exploration query and
    the exploration count is below the limit. Otherwise routes to responder.
    """
    tool_results = state.get("tool_results", [])
    if not tool_results:
        return "responder"

    last_result = tool_results[-1]
    tool_name = last_result.get("tool_name", "")

    if tool_name == "explore_column_values":
        exploration_count = state.get("exploration_count", 0)
        if exploration_count < MAX_EXPLORATIONS:
            return "sql_generator"

    return "responder"


def _build_graph() -> StateGraph:
    """Build the graph structure without compiling.

    Graph flow:
    1. Retrieval - Fetch context from vector stores
    2. SQL Generator - Generate SQL from question + context
       - If exploration tool call requested -> Tool Executor -> SQL Generator (loop)
       - If execute_sql tool call requested -> Tool Executor -> Responder
       - If out-of-scope or read-only request -> Responder (skip validation/execution)
    3. Validator - Validate SQL syntax and safety
       - If resource not found -> Responder (skip execution)
    4. Executor - Execute SQL (if valid)
    5. Responder - Generate natural language response

    The exploration loop allows the LLM to discover correct database values before
    generating the final SQL query (up to MAX_EXPLORATIONS times).

    If validation fails (and not a special response), retry SQL generation up to MAX_RETRIES times.
    """
    # Create the graph
    graph = StateGraph(AgentState)

    # Add nodes
    graph.add_node("retrieval", retrieval_node)
    graph.add_node("sql_generator", sql_generator_node)
    graph.add_node("validator", validator_node)
    graph.add_node("executor", executor_node)
    graph.add_node("tool_executor", tool_executor_node)
    graph.add_node("responder", responder_node)
    graph.add_node("increment_retry", increment_retry)

    # Set entry point
    graph.set_entry_point("retrieval")

    # Add edges
    graph.add_edge("retrieval", "sql_generator")

    # Conditional routing after SQL generation
    # - Route to tool_executor if LLM requested a tool call
    # - Skip validation for special responses (out-of-scope, read-only)
    graph.add_conditional_edges(
        "sql_generator",
        should_validate_or_respond,
        {
            "validator": "validator",
            "responder": "responder",
            "tool_executor": "tool_executor",
        },
    )

    # Conditional routing after tool execution
    # - For exploration queries: loop back to sql_generator to use discovered values
    # - For SQL execution: go to responder
    graph.add_conditional_edges(
        "tool_executor",
        route_after_tool_execution,
        {
            "sql_generator": "sql_generator",
            "responder": "responder",
        },
    )

    # Conditional routing after validation
    graph.add_conditional_edges(
        "validator",
        should_execute,
        {
            "executor": "executor",
            "responder": "increment_retry",
        },
    )

    # After execution, go to responder
    graph.add_edge("executor", "responder")

    # After incrementing retry, decide whether to retry or respond
    graph.add_conditional_edges(
        "increment_retry",
        should_retry,
        {
            "sql_generator": "sql_generator",
            "responder": "responder",
        },
    )

    # Responder is the end
    graph.add_edge("responder", END)

    return graph


async def create_agent_graph(with_checkpointer: bool = True):
    """Create and compile the text-to-SQL agent graph."""
    graph = _build_graph()

    if with_checkpointer:
        session_manager = get_session_manager()
        checkpointer = await session_manager._init_checkpointer()
        return graph.compile(checkpointer=checkpointer)

    return graph.compile()


# Singleton graph instance
_agent_graph = None


async def get_agent_graph():
    """Get the singleton agent graph instance."""
    global _agent_graph
    if _agent_graph is None:
        _agent_graph = await create_agent_graph()
    return _agent_graph
