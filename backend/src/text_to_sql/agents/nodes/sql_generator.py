"""SQL generation node using Azure OpenAI."""

import re
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import AzureChatOpenAI

from text_to_sql.agents.state import AgentState
from text_to_sql.agents.tools.exploration_tools import explore_column_values
from text_to_sql.agents.tools.sql_tools import execute_sql_query
from text_to_sql.config import get_settings
from text_to_sql.services.system_rules import (
    EXCLUDED_SELECT_COLUMNS,
    get_system_rules_service,
)

BASE_SYSTEM_PROMPT = """You are an expert SQL developer specializing in PostgreSQL. Your task is to convert natural language questions into accurate SQL queries for querying cloud resource metadata.

## PURPOSE AND SCOPE
This system is designed to query metadata about Azure and AWS cloud resources. Valid questions include:
- Resource inventory (e.g., "List all VMs", "Show S3 buckets", "Count EC2 instances")
- Resource configuration and properties
- Tags and metadata for cloud resources
- Resource relationships and dependencies
- Cost and billing information for cloud resources
- Security and compliance status of resources

## OUT-OF-SCOPE REQUESTS
If the user asks about topics unrelated to Azure/AWS cloud resources, you MUST respond with ONLY:
[OUT_OF_SCOPE] I'm designed to help you query Azure and AWS cloud resource metadata only. I can help with questions about your cloud resources, their configurations, tags, and relationships. Please ask a question about your cloud resources.

Examples of out-of-scope questions:
- General knowledge questions (weather, news, math, etc.)
- Questions about non-cloud databases or systems
- Personal assistant requests
- Programming help unrelated to cloud queries

## DATA MODIFICATION REQUESTS
This system is READ-ONLY. If the user attempts to modify, insert, update, or delete data, respond with ONLY:
[READ_ONLY] This system only supports querying (reading) cloud resource data. Data modifications are not permitted. How can I help you find information about your cloud resources?

## IMPORTANT RULES FOR VALID QUERIES
1. Only generate SELECT or WITH (CTE) statements - never INSERT, UPDATE, DELETE, DROP, etc.
2. Use proper PostgreSQL syntax and functions
3. Always consider performance - use appropriate indexes and avoid SELECT *
4. Include LIMIT clauses when appropriate to prevent large result sets
5. Use table aliases for clarity in complex queries
6. Handle NULL values appropriately

BATCH DOWNLOAD SUPPORT:
When users request data in batches or specify record ranges, you should:
- For "first N records" or "get N records": Use LIMIT N
- For "records X to Y" or "rows X through Y": Use LIMIT (Y-X+1) OFFSET (X-1)
- For "next batch" or "next N records": Refer to the conversation context for the previous offset and add the batch size
- For "skip first N" or "starting from record N": Use OFFSET (N-1)

Examples of batch requests:
- "Get me the first 2000 records" -> Add LIMIT 2000
- "Get records 2001 to 4000" -> Add LIMIT 2000 OFFSET 2000
- "Show me the next 2500 rows" -> Determine previous offset from context, add LIMIT 2500 OFFSET (previous_offset + previous_limit)
- "Get the first 3000 products sorted by price" -> Add ORDER BY price LIMIT 3000

When handling batch requests:
- Always include an ORDER BY clause to ensure consistent ordering across batches (use primary key if no specific order is requested)
- The recommended maximum batch size is 2500 records
- If the user doesn't specify a batch size, suggest using 2000-2500 records per batch

## TOOL USAGE
You have access to the following tools:

### 1. `explore_column_values` - Value Discovery Tool
Use this tool BEFORE generating a final SQL query when you need to discover the actual values stored in the database.

**When to use explore_column_values:**
- User uses descriptive terms that may not match exact database values (e.g., "PostgreSQL" vs "postgres")
- Filtering on categorical columns (engine, instance_type, region, status, provider, etc.)
- User asks about specific vendors, products, or types
- You are uncertain about the exact value format in the database

**Tool parameters:**
- table_name: The table to query (e.g., "aws_rds", "aws_ec2")
- column_name: The column to explore (e.g., "engine", "instance_type")
- search_term: Optional filter for partial matching (case-insensitive)
- limit: Maximum values to return (default: 20)

**Examples of when to explore:**
- User says "PostgreSQL RDS instances" → explore_column_values(table_name="aws_rds", column_name="engine", search_term="postgres")
- User says "large EC2 instances" → explore_column_values(table_name="aws_ec2", column_name="instance_type", search_term="large")
- User says "running instances" → explore_column_values(table_name="aws_ec2", column_name="status")
- User says "Windows servers" → explore_column_values(table_name="aws_ec2", column_name="platform", search_term="windows")

**Important exploration rules:**
- Limit to 2-3 exploration queries per request to avoid excessive queries
- Only explore when uncertain about exact values
- Use the discovered values in your final SQL query
- After exploration, generate the final query with the correct values found

### 2. `execute_sql_query` - Direct Execution Tool
When the user asks you to "run", "execute", or "show results" for a query, you SHOULD use this tool to execute the SQL and return the actual results. The tool will:
- Validate the SQL for safety (read-only operations only)
- Execute the query with pagination support
- Return the results in a format suitable for display as an interactive table

**Tool parameters:**
- sql: The SQL query to execute (required)
- page: Page number for pagination (default: 1)
- page_size: Number of rows per page (default: 100, max: 500)

**Use execute_sql_query when:**
- The user explicitly asks to run/execute a query
- The user wants to see actual data results
- You need to verify query results

**Do NOT use execute_sql_query when:**
- The user just asks you to write/generate a query
- The request is out-of-scope or read-only violation
- You're explaining query structure without execution

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


def _filter_system_columns_from_doc(
    doc: str, excluded: frozenset[str] = EXCLUDED_SELECT_COLUMNS
) -> str:
    """Filter system columns from a schema document string.

    Removes lines containing system column definitions from the schema text.

    Args:
        doc: The schema document text (typically from to_embedding_text()).
        excluded: Set of column names to filter out.

    Returns:
        Filtered document with system columns removed.
    """
    # Build a single pattern matching any excluded column name
    escaped_names = "|".join(re.escape(name) for name in excluded)
    pattern = re.compile(rf"^\s+-\s+({escaped_names})\s+\(")

    return "\n".join(
        line for line in doc.split("\n") if not pattern.match(line)
    )


def _format_discovered_values(state: AgentState) -> str:
    """Format discovered values from exploration queries for the prompt."""
    exploration_queries = state.get("exploration_queries", [])
    if not exploration_queries:
        return ""

    parts = [
        "## Previously Discovered Database Values",
        "Use these actual database values in your SQL query:\n",
    ]

    for exploration in exploration_queries:
        if not exploration.get("success"):
            continue

        table = exploration.get("table", "unknown")
        column = exploration.get("column", "unknown")
        values = exploration.get("values", [])
        search_term = exploration.get("search_term")

        if not values:
            continue

        parts.append(f"### {table}.{column}")
        if search_term:
            parts.append(f"(searched for: '{search_term}')")

        counts = exploration.get("counts", {})
        value_strs = [
            f"'{v}' ({counts[v]} rows)" if counts.get(v) else f"'{v}'"
            for v in values[:10]
        ]
        parts.append(f"Values found: {', '.join(value_strs)}")
        parts.append("")

    return "\n".join(parts) if len(parts) > 2 else ""


def _format_context(state: AgentState) -> str:
    """Format retrieved context for the prompt."""
    parts = []

    # Format discovered values from exploration (if any) - put this first for emphasis
    discovered_context = _format_discovered_values(state)
    if discovered_context:
        parts.append(discovered_context)

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

    # Format database schema (filter system columns)
    if state["database_info"]:
        parts.append("\n## Relevant Database Schema")
        for table in state["database_info"]:
            doc = table.get("document", "")
            if doc:
                filtered_doc = _filter_system_columns_from_doc(doc)
                parts.append(f"\n{filtered_doc}")

    # Format domain metadata
    if state["metadata"]:
        parts.append("\n## Domain Knowledge")
        for entry in state["metadata"][:3]:
            meta = entry.get("metadata", entry)
            parts.append(f"\n### {meta.get('title', 'Info')}")
            parts.append(meta.get("content", ""))

    return "\n".join(parts) if parts else "No additional context available."


def _parse_sql_response(content: str) -> tuple[str | None, str | None, str | None]:
    """Parse the LLM response to extract SQL, explanation, and special markers.

    Returns:
        Tuple of (sql, explanation, special_response_type)
        special_response_type is one of: "OUT_OF_SCOPE", "READ_ONLY", or None
    """
    # Check for special response markers first
    if content.strip().startswith("[OUT_OF_SCOPE]"):
        message = content.replace("[OUT_OF_SCOPE]", "").strip()
        return None, message, "OUT_OF_SCOPE"

    if content.strip().startswith("[READ_ONLY]"):
        message = content.replace("[READ_ONLY]", "").strip()
        return None, message, "READ_ONLY"

    # Extract SQL from code block (semicolons are stripped by database service)
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

    return sql, explanation if explanation else None, None


def _parse_tool_calls(response: Any) -> list[dict[str, Any]]:
    """Extract tool calls from LLM response.

    Handles malformed tool call structures gracefully by skipping invalid entries.

    Returns:
        List of tool call dictionaries with id, name, and args.
    """
    if not hasattr(response, "tool_calls") or not response.tool_calls:
        return []

    tool_calls = []
    for tc in response.tool_calls:
        try:
            if not isinstance(tc, dict):
                continue
            tool_calls.append({
                "id": str(tc.get("id", "")),
                "name": str(tc.get("name", "")),
                "args": tc.get("args") if isinstance(tc.get("args"), dict) else {},
            })
        except (TypeError, AttributeError):
            continue
    return tool_calls


async def sql_generator_node(state: AgentState) -> dict:
    """Generate SQL query from natural language question.

    Uses retrieved context (SQL pairs, schema, metadata) to generate
    an accurate SQL query.

    May return special response types for out-of-scope or read-only requests.
    Can also return tool calls for direct SQL execution.
    """
    settings = get_settings()

    # Create LLM with tool binding
    base_llm = AzureChatOpenAI(
        azure_endpoint=settings.azure_openai_endpoint,
        api_key=settings.azure_openai_api_key.get_secret_value(),
        api_version=settings.azure_openai_api_version,
        azure_deployment=settings.azure_openai_deployment_name,
        temperature=0,
    )

    # Bind both exploration and execution tools
    llm = base_llm.bind_tools([explore_column_values, execute_sql_query])

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

    # Check for tool calls first
    tool_calls = _parse_tool_calls(response)
    if tool_calls:
        # LLM wants to execute SQL directly
        first_tool_call = tool_calls[0]
        sql_from_tool = first_tool_call.get("args", {}).get("sql")

        return {
            "generated_sql": sql_from_tool,
            "sql_explanation": "Executing query via tool call.",
            "messages": [HumanMessage(content=state["question"])],
            "special_response_type": None,
            "tool_calls": tool_calls,
            "pending_tool_call": first_tool_call,
        }

    # No tool calls - parse the text response
    content = response.content if isinstance(response.content, str) else str(response.content)

    sql, explanation, special_response_type = _parse_sql_response(content)

    result: dict[str, Any] = {
        "generated_sql": sql,
        "sql_explanation": explanation,
        "messages": [HumanMessage(content=state["question"])],
        "special_response_type": special_response_type,
        "tool_calls": [],
        "pending_tool_call": None,
    }

    # If this is a special response (out-of-scope or read-only), skip SQL generation
    if special_response_type:
        result["natural_language_response"] = explanation
        result["is_valid"] = False  # Mark as invalid to skip execution
        result["validation_errors"] = []  # No validation errors, just skip

    return result
