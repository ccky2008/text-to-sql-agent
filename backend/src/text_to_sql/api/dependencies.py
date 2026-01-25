"""FastAPI dependencies for dependency injection."""

from typing import Annotated

from fastapi import Depends

from text_to_sql.agents.graph import get_agent_graph
from text_to_sql.services.checkpointer import SessionManager, get_session_manager
from text_to_sql.services.database import DatabaseService, get_database_service
from text_to_sql.services.vector_store import VectorStoreService, get_vector_store_service

# Type aliases for dependency injection
VectorStoreDep = Annotated[VectorStoreService, Depends(get_vector_store_service)]
DatabaseDep = Annotated[DatabaseService, Depends(get_database_service)]
SessionManagerDep = Annotated[SessionManager, Depends(get_session_manager)]


def get_graph():
    """Dependency to get the agent graph."""
    return get_agent_graph()


GraphDep = Annotated[object, Depends(get_graph)]
