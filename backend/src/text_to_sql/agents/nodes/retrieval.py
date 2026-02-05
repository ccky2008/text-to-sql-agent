"""Retrieval node for fetching context from vector stores."""

from text_to_sql.agents.state import AgentState
from text_to_sql.agents.streaming import get_writer
from text_to_sql.services.vector_store import get_vector_store_service


def retrieval_node(state: AgentState) -> dict:
    """Retrieve relevant context from ChromaDB collections.

    This node searches:
    1. SQL pairs - for few-shot examples
    2. Domain metadata - for business rules and context
    3. Database info - for schema information
    """
    writer = get_writer()
    writer({"type": "step_started", "step": "retrieval", "label": "Retrieving context"})

    question = state["question"]
    vector_store = get_vector_store_service()

    # Search for similar SQL pairs (few-shot examples)
    sql_pairs = vector_store.search_sql_pairs(question, n_results=5)

    # Search for domain metadata (business rules, terms)
    metadata = vector_store.search_metadata(question, n_results=5)

    # Search for relevant database schema
    database_info = vector_store.search_database_info(question, n_results=10)

    return {
        "sql_pairs": sql_pairs,
        "metadata": metadata,
        "database_info": database_info,
    }
