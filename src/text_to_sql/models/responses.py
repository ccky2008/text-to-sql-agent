"""API response models."""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class QueryResponse(BaseModel):
    """Response model for non-streaming query endpoint."""

    question: str = Field(..., description="Original question")
    generated_sql: str | None = Field(default=None, description="Generated SQL query")
    explanation: str | None = Field(default=None, description="Explanation of the SQL")
    is_valid: bool = Field(default=False, description="Whether the SQL is valid")
    validation_errors: list[str] = Field(default_factory=list, description="Validation errors")
    validation_warnings: list[str] = Field(default_factory=list, description="Validation warnings")
    executed: bool = Field(default=False, description="Whether the SQL was executed")
    results: list[dict[str, Any]] | None = Field(default=None, description="Query results")
    row_count: int | None = Field(default=None, description="Number of rows returned")
    columns: list[str] | None = Field(default=None, description="Column names")
    natural_language_response: str | None = Field(
        default=None, description="Natural language response"
    )
    session_id: str = Field(..., description="Session ID for conversation continuity")
    error: str | None = Field(default=None, description="Error message if any")


class StreamEvent(BaseModel):
    """Model for SSE stream events."""

    event: Literal[
        "retrieval_complete",
        "sql_generated",
        "validation_complete",
        "execution_complete",
        "token",
        "response_complete",
        "error",
        "done",
    ]
    data: dict[str, Any]


class HealthResponse(BaseModel):
    """Health check response."""

    status: Literal["healthy", "degraded", "unhealthy"]
    version: str
    services: dict[str, bool] = Field(
        default_factory=dict, description="Status of dependent services"
    )


class SessionInfo(BaseModel):
    """Session information."""

    session_id: str
    created_at: datetime
    last_active: datetime
    message_count: int


class SessionListResponse(BaseModel):
    """Response for listing sessions."""

    sessions: list[SessionInfo]
    total: int


class SearchResult(BaseModel):
    """Search result from vector store."""

    id: str
    content: str
    metadata: dict[str, Any]
    score: float


class SQLPairListResponse(BaseModel):
    """Response for listing SQL pairs."""

    pairs: list[dict[str, Any]]
    total: int


class MetadataListResponse(BaseModel):
    """Response for listing metadata entries."""

    entries: list[dict[str, Any]]
    total: int


class TableInfoListResponse(BaseModel):
    """Response for listing table info."""

    tables: list[dict[str, Any]]
    total: int
