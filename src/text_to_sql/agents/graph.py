"""LangGraph agent graph definition."""

from typing import Literal

from langgraph.graph import END, StateGraph

from text_to_sql.agents.nodes.executor import executor_node
from text_to_sql.agents.nodes.responder import responder_node
from text_to_sql.agents.nodes.retrieval import retrieval_node
from text_to_sql.agents.nodes.sql_generator import sql_generator_node
from text_to_sql.agents.nodes.validator import validator_node
from text_to_sql.agents.state import AgentState
from text_to_sql.services.checkpointer import get_session_manager

# Maximum retry attempts for SQL regeneration
MAX_RETRIES = 2


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
    """
    if not state.get("is_valid", False) and state.get("retry_count", 0) < MAX_RETRIES:
        return "sql_generator"
    return "responder"


def increment_retry(state: AgentState) -> dict:
    """Increment retry counter."""
    return {"retry_count": state.get("retry_count", 0) + 1}


def create_agent_graph(with_checkpointer: bool = True) -> StateGraph:
    """Create the text-to-SQL agent graph.

    Graph flow:
    1. Retrieval - Fetch context from vector stores
    2. SQL Generator - Generate SQL from question + context
    3. Validator - Validate SQL syntax and safety
    4. Executor - Execute SQL (if valid)
    5. Responder - Generate natural language response

    If validation fails, retry SQL generation up to MAX_RETRIES times.
    """
    # Create the graph
    graph = StateGraph(AgentState)

    # Add nodes
    graph.add_node("retrieval", retrieval_node)
    graph.add_node("sql_generator", sql_generator_node)
    graph.add_node("validator", validator_node)
    graph.add_node("executor", executor_node)
    graph.add_node("responder", responder_node)
    graph.add_node("increment_retry", increment_retry)

    # Set entry point
    graph.set_entry_point("retrieval")

    # Add edges
    graph.add_edge("retrieval", "sql_generator")
    graph.add_edge("sql_generator", "validator")

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

    # Compile with checkpointer for session persistence
    if with_checkpointer:
        session_manager = get_session_manager()
        return graph.compile(checkpointer=session_manager.checkpointer)

    return graph.compile()


# Singleton graph instance
_agent_graph = None


def get_agent_graph() -> StateGraph:
    """Get the singleton agent graph instance."""
    global _agent_graph
    if _agent_graph is None:
        _agent_graph = create_agent_graph()
    return _agent_graph
