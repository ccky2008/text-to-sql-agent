"""API response models."""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class PaginationInfo(BaseModel):
    """Pagination metadata."""

    page: int = Field(..., description="Current page number (1-indexed)")
    page_size: int = Field(..., description="Results per page")
    total_count: int | None = Field(default=None, description="Total number of rows")
    total_pages: int | None = Field(default=None, description="Total number of pages")
    has_next: bool = Field(default=False, description="Whether there are more pages")
    has_prev: bool = Field(default=False, description="Whether there are previous pages")


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
    pagination: PaginationInfo | None = Field(default=None, description="Pagination metadata")
    csv_available: bool = Field(default=False, description="Whether CSV download is available")
    csv_exceeds_limit: bool = Field(default=False, description="Whether total rows exceed CSV limit")
    query_token: str | None = Field(default=None, description="Token for CSV download (valid for 1 hour)")


class StreamEvent(BaseModel):
    """Model for SSE stream events."""

    event: Literal[
        "retrieval_complete",
        "sql_generated",
        "validation_complete",
        "execution_complete",
        "tool_execution_complete",  # New: for LLM-driven tool execution
        "token",
        "response_complete",
        "error",
        "done",
    ]
    data: dict[str, Any]


class ToolExecutionEvent(BaseModel):
    """Event data for tool_execution_complete SSE event."""

    tool_name: str = Field(..., description="Name of the executed tool")
    success: bool = Field(..., description="Whether tool execution succeeded")
    rows: list[dict[str, Any]] | None = Field(default=None, description="Query results")
    columns: list[str] | None = Field(default=None, description="Column names")
    row_count: int = Field(default=0, description="Number of rows returned")
    total_count: int | None = Field(default=None, description="Total rows matching query")
    has_more: bool = Field(default=False, description="Whether more rows exist")
    page: int = Field(default=1, description="Current page number")
    page_size: int = Field(default=100, description="Rows per page")
    query_token: str | None = Field(default=None, description="Token for CSV download")
    error: str | None = Field(default=None, description="Error message if failed")


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


class CSVLimitsResponse(BaseModel):
    """Response for CSV download limits."""

    max_rows_per_download: int = Field(..., description="Maximum rows per CSV download")
    batch_download_available: bool = Field(default=True, description="Whether batch download is available")
    batch_download_instructions: str = Field(..., description="Instructions for batch downloading")
