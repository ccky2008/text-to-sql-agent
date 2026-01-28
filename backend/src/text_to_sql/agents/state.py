"""LangGraph state definitions for the text-to-SQL agent."""

from typing import Annotated, Any, TypedDict

from langgraph.graph import add_messages
from langchain_core.messages import BaseMessage


class AgentState(TypedDict):
    """State for the text-to-SQL agent graph."""

    # Conversation messages (with memory via add_messages reducer)
    messages: Annotated[list[BaseMessage], add_messages]

    # Current question being processed
    question: str

    # Retrieved context from vector stores
    sql_pairs: list[dict[str, Any]]
    metadata: list[dict[str, Any]]
    database_info: list[dict[str, Any]]

    # Generated SQL
    generated_sql: str | None
    sql_explanation: str | None

    # Validation results
    is_valid: bool
    validation_errors: list[str]
    validation_warnings: list[str]

    # Execution results
    executed: bool
    results: list[dict[str, Any]] | None
    row_count: int | None
    columns: list[str] | None
    execution_error: str | None

    # Final response
    natural_language_response: str | None

    # Session tracking
    session_id: str

    # Retry tracking
    retry_count: int

    # Pagination state
    page: int
    page_size: int
    total_count: int | None
    has_more_results: bool

    # CSV metadata
    csv_available: bool
    csv_exceeds_limit: bool
    query_token: str | None


def create_initial_state(
    question: str,
    session_id: str,
    page: int = 1,
    page_size: int = 100,
) -> AgentState:
    """Create initial state for a new query."""
    # Cap page_size to prevent abuse from internal callers
    page_size = min(page_size, 500)

    return AgentState(
        messages=[],
        question=question,
        sql_pairs=[],
        metadata=[],
        database_info=[],
        generated_sql=None,
        sql_explanation=None,
        is_valid=False,
        validation_errors=[],
        validation_warnings=[],
        executed=False,
        results=None,
        row_count=None,
        columns=None,
        execution_error=None,
        natural_language_response=None,
        session_id=session_id,
        retry_count=0,
        # Pagination state
        page=page,
        page_size=page_size,
        total_count=None,
        has_more_results=False,
        # CSV metadata
        csv_available=False,
        csv_exceeds_limit=False,
        query_token=None,
    )
