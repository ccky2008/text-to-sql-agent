"""Natural language response generation node."""

import json
from collections.abc import AsyncIterator

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_openai import AzureChatOpenAI

from text_to_sql.agents.state import AgentState
from text_to_sql.config import get_settings

# Response templates for special scenarios
RESPONSE_TEMPLATES = {
    "OUT_OF_SCOPE": (
        "I'm designed to help you query Azure and AWS cloud resource metadata only. "
        "I can help with questions about your cloud resources, their configurations, "
        "tags, and relationships. Please ask a question about your cloud resources."
    ),
    "READ_ONLY": (
        "This system only supports querying (reading) cloud resource data. "
        "Data modifications are not permitted. "
        "How can I help you find information about your cloud resources?"
    ),
    "RESOURCE_NOT_FOUND": (
        "The information you requested cannot be provided because the resource type "
        "is not tracked in our database. Please try asking about a different resource type."
    ),
    "NO_RESULTS": (
        "No resources were found matching your criteria. "
        "This could mean the resources don't exist or don't match your filters. "
        "Try adjusting your query or ask about a different resource type."
    ),
}

SYSTEM_PROMPT = """You are a helpful data analyst assistant specializing in Azure and AWS cloud resource metadata. Your task is to explain SQL query results in clear, natural language.

## CONTEXT
This system queries cloud resource metadata from Azure and AWS. Users ask questions about their cloud infrastructure, resources, configurations, tags, and relationships.

## RESPONSE GUIDELINES
When presenting results:
1. Start with a direct answer to the user's question
2. Summarize key findings from the data
3. Mention the number of rows returned if relevant
4. Highlight any notable patterns or outliers
5. Keep the response concise but informative

## HANDLING SPECIAL SCENARIOS

If the query returned no results:
- Explain that no matching cloud resources were found
- Suggest the resources might not exist or might not match the specified criteria
- Offer to help refine the query

If there was a validation error about tables not existing:
- Explain that the requested resource type is not tracked in the database
- Suggest asking about a different resource type

If there was a validation error about prohibited operations:
- Explain that this system is read-only and only supports querying data
- Offer to help find information instead

If the query failed for other reasons:
- Explain what happened in simple terms
- Suggest possible solutions or alternative questions"""


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
        parts.append("\n## Query Results")
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


def _get_template_response(state: AgentState) -> str | None:
    """Check if state requires a template response.

    Returns the template response string if a special case is detected,
    or None if the LLM should generate the response.
    """
    # Check if there's already a response set (from special response types)
    if state.get("natural_language_response") and state.get("special_response_type"):
        return state["natural_language_response"]

    # Check for special response types that need template responses
    special_type = state.get("special_response_type")
    if special_type and special_type in RESPONSE_TEMPLATES:
        return RESPONSE_TEMPLATES[special_type]

    # Check for no results scenario
    if (
        state.get("executed")
        and state.get("results") is not None
        and len(state.get("results", [])) == 0
    ):
        return RESPONSE_TEMPLATES["NO_RESULTS"]

    return None


async def responder_node(state: AgentState) -> dict:
    """Generate a natural language response based on query results.

    Handles special response types (out-of-scope, read-only, resource not found)
    and summarizes SQL results in human-readable form.
    """
    # Check for template responses (special types, no results)
    template_response = _get_template_response(state)
    if template_response:
        return {
            "natural_language_response": template_response,
            "messages": [AIMessage(content=template_response)],
        }

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

    Handles special response types and yields tokens as they are generated for SSE streaming.
    """
    # Check for template responses (special types, no results)
    template_response = _get_template_response(state)
    if template_response:
        yield template_response
        return

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
