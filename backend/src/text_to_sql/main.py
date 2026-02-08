"""FastAPI application entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from text_to_sql import __version__
from text_to_sql.api.v1 import router as v1_router
from text_to_sql.services.checkpointer import get_session_manager
from text_to_sql.services.database import get_database_service
from text_to_sql.services.sql_pair_candidates import get_candidate_manager


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup: Initialize database connection pool
    db_service = get_database_service()
    await db_service.connect()

    # Startup: Initialize session manager (MongoDB connection, etc.)
    session_manager = get_session_manager()
    await session_manager.initialize()

    # Startup: Initialize SQL pair candidate manager
    candidate_manager = get_candidate_manager()
    await candidate_manager.initialize()

    yield

    # Shutdown: Close candidate manager
    await candidate_manager.close()

    # Shutdown: Close session manager
    await session_manager.close()

    # Shutdown: Close database connections
    await db_service.close()


app = FastAPI(
    title="Text-to-SQL Agent",
    description="AI-powered natural language to SQL conversion service",
    version=__version__,
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(v1_router)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "Text-to-SQL Agent",
        "version": __version__,
        "docs": "/docs",
    }
