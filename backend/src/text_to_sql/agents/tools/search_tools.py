"""ChromaDB search tools for the agent."""

from typing import Any

from langchain_core.tools import tool

from text_to_sql.services.vector_store import get_vector_store_service


@tool
def search_sql_pairs(query: str, n_results: int = 5) -> list[dict[str, Any]]:
    """Search for similar SQL query examples based on the question.

    Args:
        query: The natural language question to search for
        n_results: Number of results to return (default: 5)

    Returns:
        List of similar SQL pair examples with question and SQL
    """
    vector_store = get_vector_store_service()
    results = vector_store.search_sql_pairs(query, n_results=n_results)
    return [
        {
            "question": r["metadata"].get("question", ""),
            "sql_query": r["metadata"].get("sql_query", ""),
            "similarity_score": 1 - r["distance"] if r.get("distance") else None,
        }
        for r in results
    ]


@tool
def search_domain_metadata(
    query: str, n_results: int = 5, category: str | None = None
) -> list[dict[str, Any]]:
    """Search for domain knowledge and business rules.

    Args:
        query: The search query
        n_results: Number of results to return (default: 5)
        category: Optional category filter (business_rule, domain_term, context)

    Returns:
        List of relevant domain metadata entries
    """
    vector_store = get_vector_store_service()
    results = vector_store.search_metadata(query, n_results=n_results, category=category)
    return [
        {
            "title": r["metadata"].get("title", ""),
            "content": r["metadata"].get("content", ""),
            "category": r["metadata"].get("category", ""),
            "related_tables": r["metadata"].get("related_tables", "").split(","),
            "keywords": r["metadata"].get("keywords", "").split(","),
            "similarity_score": 1 - r["distance"] if r.get("distance") else None,
        }
        for r in results
    ]


@tool
def search_database_schema(query: str, n_results: int = 10) -> list[dict[str, Any]]:
    """Search for database schema information relevant to the query.

    Args:
        query: The search query describing what tables/columns are needed
        n_results: Number of results to return (default: 10)

    Returns:
        List of relevant table schema information
    """
    vector_store = get_vector_store_service()
    results = vector_store.search_database_info(query, n_results=n_results)
    return [
        {
            "table_name": r["metadata"].get("full_name", ""),
            "schema_name": r["metadata"].get("schema_name", ""),
            "columns": r["metadata"].get("column_names", "").split(","),
            "description": r["metadata"].get("description", ""),
            "ddl": r["document"],
            "similarity_score": 1 - r["distance"] if r.get("distance") else None,
        }
        for r in results
    ]


def get_search_tools() -> list:
    """Get all search tools."""
    return [search_sql_pairs, search_domain_metadata, search_database_schema]
