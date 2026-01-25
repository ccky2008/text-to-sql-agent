"""Query endpoint with streaming support."""

import json
from typing import AsyncIterator
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from sse_starlette.sse import EventSourceResponse

from text_to_sql.agents.graph import get_agent_graph
from text_to_sql.agents.nodes.responder import responder_node_streaming
from text_to_sql.agents.state import create_initial_state
from text_to_sql.models.requests import QueryRequest
from text_to_sql.models.responses import QueryResponse
from text_to_sql.services.checkpointer import get_session_manager

router = APIRouter()


async def stream_query(request: QueryRequest) -> AsyncIterator[dict]:
    """Stream query processing events."""
    session_id = request.session_id or str(uuid4())
    session_manager = get_session_manager()

    # Create or get session
    if not session_manager.get_session(session_id):
        session_manager.create_session(session_id)

    # Create initial state
    state = create_initial_state(request.question, session_id)

    # Get graph and config
    graph = get_agent_graph()
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
                                "results": node_output.get("results", [])[:10],  # Limit for SSE
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

    state = create_initial_state(request.question, session_id)
    graph = get_agent_graph()
    config = session_manager.get_config(session_id)

    try:
        # Run the graph to completion
        final_state = await graph.ainvoke(state, config=config)

        session_manager.update_session(session_id)

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
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
