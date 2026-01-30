"""Query endpoint with streaming support."""

import json
from collections.abc import AsyncIterator
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from sse_starlette.sse import EventSourceResponse

from text_to_sql.agents.graph import get_agent_graph
from text_to_sql.agents.nodes.responder import responder_node_streaming
from text_to_sql.agents.state import create_initial_state
from text_to_sql.models.requests import QueryRequest
from text_to_sql.models.responses import PaginationInfo, QueryResponse
from text_to_sql.services.checkpointer import get_session_manager

router = APIRouter()


async def stream_query(request: QueryRequest) -> AsyncIterator[dict]:
    """Stream query processing events."""
    session_id = request.session_id or str(uuid4())
    session_manager = get_session_manager()

    # Create or get session
    if not session_manager.get_session(session_id):
        session_manager.create_session(session_id)

    # Create initial state with pagination
    state = create_initial_state(
        request.question,
        session_id,
        page=request.page,
        page_size=request.page_size,
    )

    # Get graph and config
    graph = await get_agent_graph()
    config = session_manager.get_config(session_id)

    try:
        # Stream through the graph nodes
        collected_state = dict(state)

        async for event in graph.astream(state, config=config):
            for node_name, node_output in event.items():
                collected_state.update(node_output)

                if node_name == "retrieval":
                    yield {
                        "event": "retrieval_complete",
                        "data": json.dumps({
                            "sql_pairs": len(node_output.get("sql_pairs", [])),
                            "metadata": len(node_output.get("metadata", [])),
                            "database_info": len(node_output.get("database_info", [])),
                        }),
                    }

                elif node_name == "sql_generator":
                    yield {
                        "event": "sql_generated",
                        "data": json.dumps({
                            "sql": node_output.get("generated_sql"),
                            "explanation": node_output.get("sql_explanation"),
                        }),
                    }

                elif node_name == "validator":
                    yield {
                        "event": "validation_complete",
                        "data": json.dumps({
                            "is_valid": node_output.get("is_valid", False),
                            "errors": node_output.get("validation_errors", []),
                            "warnings": node_output.get("validation_warnings", []),
                        }),
                    }

                elif node_name == "executor":
                    if node_output.get("executed"):
                        yield {
                            "event": "execution_complete",
                            "data": json.dumps({
                                "row_count": node_output.get("row_count"),
                                "columns": node_output.get("columns"),
                                "results": node_output.get("results", []),
                                "total_count": node_output.get("total_count"),
                                "has_more": node_output.get("has_more_results", False),
                                "page": request.page,
                                "page_size": request.page_size,
                                "csv_available": node_output.get("csv_available", False),
                                "csv_exceeds_limit": node_output.get("csv_exceeds_limit", False),
                                "query_token": node_output.get("query_token"),
                            }, default=str),
                        }

                elif node_name == "tool_executor":
                    # Handle LLM-driven tool execution results
                    tool_results = node_output.get("tool_results", [])
                    for tool_result in tool_results:
                        result_data = tool_result.get("result") or {}
                        yield {
                            "event": "tool_execution_complete",
                            "data": json.dumps({
                                "tool_name": tool_result.get("tool_name", ""),
                                "success": tool_result.get("success", False),
                                "rows": result_data.get("rows"),
                                "columns": result_data.get("columns"),
                                "row_count": result_data.get("row_count", 0),
                                "total_count": result_data.get("total_count"),
                                "has_more": result_data.get("has_more", False),
                                "page": result_data.get("page", 1),
                                "page_size": result_data.get("page_size", 100),
                                "query_token": result_data.get("query_token"),
                                "error": tool_result.get("error"),
                            }, default=str),
                        }

        # Stream the natural language response tokens
        async for token in responder_node_streaming(collected_state):
            yield {
                "event": "token",
                "data": json.dumps({"content": token}),
            }

        # Update session
        session_manager.update_session(session_id)

        # Send done event
        yield {
            "event": "done",
            "data": json.dumps({"session_id": session_id}),
        }

    except Exception as e:
        yield {
            "event": "error",
            "data": json.dumps({"error": str(e)}),
        }


@router.post("/query")
async def query(request: QueryRequest):
    """Process a natural language query and return SQL with results.

    Supports both streaming (SSE) and non-streaming responses.
    """
    if request.stream:
        return EventSourceResponse(stream_query(request))

    # Non-streaming response
    session_id = request.session_id or str(uuid4())
    session_manager = get_session_manager()

    if not session_manager.get_session(session_id):
        session_manager.create_session(session_id)

    state = create_initial_state(
        request.question,
        session_id,
        page=request.page,
        page_size=request.page_size,
    )
    graph = await get_agent_graph()
    config = session_manager.get_config(session_id)

    try:
        # Run the graph to completion
        final_state = await graph.ainvoke(state, config=config)

        session_manager.update_session(session_id)

        # Build pagination info if total_count is available
        total_count = final_state.get("total_count")
        pagination = None
        if total_count is not None:
            total_pages = (total_count + request.page_size - 1) // request.page_size
            pagination = PaginationInfo(
                page=request.page,
                page_size=request.page_size,
                total_count=total_count,
                total_pages=total_pages,
                has_next=final_state.get("has_more_results", False),
                has_prev=request.page > 1,
            )

        return QueryResponse(
            question=request.question,
            generated_sql=final_state.get("generated_sql"),
            explanation=final_state.get("sql_explanation"),
            is_valid=final_state.get("is_valid", False),
            validation_errors=final_state.get("validation_errors", []),
            validation_warnings=final_state.get("validation_warnings", []),
            executed=final_state.get("executed", False),
            results=final_state.get("results"),
            row_count=final_state.get("row_count"),
            columns=final_state.get("columns"),
            natural_language_response=final_state.get("natural_language_response"),
            session_id=session_id,
            error=final_state.get("execution_error"),
            pagination=pagination,
            csv_available=final_state.get("csv_available", False),
            csv_exceeds_limit=final_state.get("csv_exceeds_limit", False),
            query_token=final_state.get("query_token"),
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
