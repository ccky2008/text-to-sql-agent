"""SQL generation node using Azure OpenAI."""

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import AzureChatOpenAI

from text_to_sql.agents.state import AgentState
from text_to_sql.config import get_settings
from text_to_sql.services.system_rules import get_system_rules_service

BASE_SYSTEM_PROMPT = """You are an expert SQL developer specializing in PostgreSQL. Your task is to convert natural language questions into accurate SQL queries.

IMPORTANT RULES:
1. Only generate SELECT or WITH (CTE) statements - never INSERT, UPDATE, DELETE, DROP, etc.
2. Use proper PostgreSQL syntax and functions
3. Always consider performance - use appropriate indexes and avoid SELECT *
4. Include LIMIT clauses when appropriate to prevent large result sets
5. Use table aliases for clarity in complex queries
6. Handle NULL values appropriately

{system_rules}

Based on the context provided, generate a SQL query that accurately answers the user's question.

Respond with:
1. The SQL query wrapped in ```sql ... ``` code blocks
2. A brief explanation of what the query does and why you chose this approach

If you cannot generate a valid query due to missing schema information, explain what additional information you need."""


def _get_system_prompt() -> str:
    """Build system prompt with system rules."""
    rules_service = get_system_rules_service()
    system_rules = rules_service.format_for_prompt()
    return BASE_SYSTEM_PROMPT.format(system_rules=system_rules)


def _format_context(state: AgentState) -> str:
    """Format retrieved context for the prompt."""
    parts = []

    # Format SQL pairs (few-shot examples)
    if state["sql_pairs"]:
        parts.append("## Similar SQL Examples")
        for i, pair in enumerate(state["sql_pairs"][:3], 1):
            meta = pair.get("metadata", pair)
            parts.append(f"\n### Example {i}")
            parts.append(f"Question: {meta.get('question', 'N/A')}")
            parts.append(f"SQL: {meta.get('sql_query', 'N/A')}")
            if meta.get("explanation"):
                parts.append(f"Explanation: {meta.get('explanation')}")

    # Format database schema
    if state["database_info"]:
        parts.append("\n## Relevant Database Schema")
        for table in state["database_info"]:
            doc = table.get("document", "")
            if doc:
                parts.append(f"\n{doc}")

    # Format domain metadata
    if state["metadata"]:
        parts.append("\n## Domain Knowledge")
        for entry in state["metadata"][:3]:
            meta = entry.get("metadata", entry)
            parts.append(f"\n### {meta.get('title', 'Info')}")
            parts.append(meta.get("content", ""))

    return "\n".join(parts) if parts else "No additional context available."


def _parse_sql_response(content: str) -> tuple[str | None, str | None]:
    """Parse the LLM response to extract SQL and explanation."""
    import re

    # Extract SQL from code block
    sql_match = re.search(r"```sql\s*(.*?)\s*```", content, re.DOTALL | re.IGNORECASE)
    sql = sql_match.group(1).strip() if sql_match else None

    # If no code block, try to find SELECT/WITH statement
    if not sql:
        select_match = re.search(
            r"((?:WITH\s+.*?\s+AS\s*\(.*?\)\s*)?SELECT\s+.*?)(?:;|$)",
            content,
            re.DOTALL | re.IGNORECASE,
        )
        if select_match:
            sql = select_match.group(1).strip()

    # Extract explanation (text after SQL block or before it)
    explanation = content
    if sql_match:
        # Get text after the code block
        after_sql = content[sql_match.end() :].strip()
        before_sql = content[: sql_match.start()].strip()
        explanation = after_sql if after_sql else before_sql

    # Clean up explanation
    explanation = re.sub(r"```.*?```", "", explanation, flags=re.DOTALL).strip()

    return sql, explanation if explanation else None


async def sql_generator_node(state: AgentState) -> dict:
    """Generate SQL query from natural language question.

    Uses retrieved context (SQL pairs, schema, metadata) to generate
    an accurate SQL query.
    """
    settings = get_settings()

    llm = AzureChatOpenAI(
        azure_endpoint=settings.azure_openai_endpoint,
        api_key=settings.azure_openai_api_key.get_secret_value(),
        api_version=settings.azure_openai_api_version,
        azure_deployment=settings.azure_openai_deployment_name,
        temperature=0,
    )

    context = _format_context(state)

    messages = [
        SystemMessage(content=_get_system_prompt()),
        HumanMessage(content=f"## Context\n{context}\n\n## Question\n{state['question']}"),
    ]

    # Add conversation history for context
    if state["messages"]:
        # Insert previous messages before the current question
        history_messages = state["messages"][-10:]  # Last 10 messages for context
        messages = [messages[0]] + list(history_messages) + [messages[1]]

    response = await llm.ainvoke(messages)
    content = response.content if isinstance(response.content, str) else str(response.content)

    sql, explanation = _parse_sql_response(content)

    return {
        "generated_sql": sql,
        "sql_explanation": explanation,
        "messages": [HumanMessage(content=state["question"])],
    }
