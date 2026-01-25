"""Natural language response generation node."""

import json
from typing import AsyncIterator

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_openai import AzureChatOpenAI

from text_to_sql.agents.state import AgentState
from text_to_sql.config import get_settings

SYSTEM_PROMPT = """You are a helpful data analyst assistant. Your task is to explain SQL query results in clear, natural language.

When presenting results:
1. Start with a direct answer to the user's question
2. Summarize key findings from the data
3. Mention the number of rows returned if relevant
4. Highlight any notable patterns or outliers
5. Keep the response concise but informative

If the query failed or returned no results, explain what happened and suggest possible reasons or next steps."""


def _format_results_for_prompt(state: AgentState) -> str:
    """Format query results for the response prompt."""
    parts = []

    parts.append(f"## Original Question\n{state['question']}")
    parts.append(f"\n## Generated SQL\n```sql\n{state.get('generated_sql', 'N/A')}\n```")

    if state.get("sql_explanation"):
        parts.append(f"\n## SQL Explanation\n{state['sql_explanation']}")

    if not state.get("is_valid"):
        parts.append(f"\n## Validation Failed\nErrors: {state.get('validation_errors', [])}")
    elif not state.get("executed"):
        parts.append("\n## Query Not Executed")
        if state.get("execution_error"):
            parts.append(f"Error: {state['execution_error']}")
    else:
        parts.append(f"\n## Query Results")
        parts.append(f"Rows returned: {state.get('row_count', 0)}")

        if state.get("columns"):
            parts.append(f"Columns: {', '.join(state['columns'])}")

        if state.get("results"):
            # Limit results shown to LLM for token efficiency
            results_to_show = state["results"][:20]
            parts.append(f"\nData (first {len(results_to_show)} rows):")
            parts.append(json.dumps(results_to_show, indent=2, default=str))

            if len(state["results"]) > 20:
                parts.append(f"\n... and {len(state['results']) - 20} more rows")

    if state.get("validation_warnings"):
        parts.append(f"\n## Warnings\n{state['validation_warnings']}")

    return "\n".join(parts)


async def responder_node(state: AgentState) -> dict:
    """Generate a natural language response based on query results.

    Summarizes the SQL results in human-readable form.
    """
    settings = get_settings()

    llm = AzureChatOpenAI(
        azure_endpoint=settings.azure_openai_endpoint,
        api_key=settings.azure_openai_api_key.get_secret_value(),
        api_version=settings.azure_openai_api_version,
        azure_deployment=settings.azure_openai_deployment_name,
        temperature=0.3,
    )

    context = _format_results_for_prompt(state)

    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=context),
    ]

    response = await llm.ainvoke(messages)
    content = response.content if isinstance(response.content, str) else str(response.content)

    return {
        "natural_language_response": content,
        "messages": [AIMessage(content=content)],
    }


async def responder_node_streaming(state: AgentState) -> AsyncIterator[str]:
    """Generate a natural language response with streaming.

    Yields tokens as they are generated for SSE streaming.
    """
    settings = get_settings()

    llm = AzureChatOpenAI(
        azure_endpoint=settings.azure_openai_endpoint,
        api_key=settings.azure_openai_api_key.get_secret_value(),
        api_version=settings.azure_openai_api_version,
        azure_deployment=settings.azure_openai_deployment_name,
        temperature=0.3,
        streaming=True,
    )

    context = _format_results_for_prompt(state)

    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=context),
    ]

    async for chunk in llm.astream(messages):
        if chunk.content:
            yield chunk.content
