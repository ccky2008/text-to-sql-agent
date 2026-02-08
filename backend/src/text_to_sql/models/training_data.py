"""Models for SQL pair candidate training data review."""

import hashlib
from datetime import UTC, datetime
from enum import Enum

from pydantic import BaseModel, Field


class CandidateStatus(str, Enum):
    """Status of a SQL pair candidate."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class SQLPairCandidateResponse(BaseModel):
    """Response model for a single SQL pair candidate."""

    id: str = Field(..., description="MongoDB document ID")
    question: str = Field(..., description="Natural language question")
    sql_query: str = Field(..., description="Generated SQL query")
    question_hash: str = Field(..., description="Dedup hash of the question")
    status: CandidateStatus = Field(default=CandidateStatus.PENDING)
    session_id: str | None = Field(default=None, description="Session that generated this pair")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class SQLPairCandidateListResponse(BaseModel):
    """Paginated list of SQL pair candidates."""

    items: list[SQLPairCandidateResponse] = Field(default_factory=list)
    total: int = Field(default=0)
    page: int = Field(default=1)
    page_size: int = Field(default=20)
    has_next: bool = Field(default=False)
    has_prev: bool = Field(default=False)


class CandidateEditRequest(BaseModel):
    """Request to edit a candidate's question and/or SQL query.

    Used for both standalone updates and approve-with-overrides.
    """

    question: str | None = Field(default=None)
    sql_query: str | None = Field(default=None)


class BulkActionRequest(BaseModel):
    """Request for bulk approve/reject operations."""

    ids: list[str] = Field(..., description="List of candidate IDs")


class BulkActionResponse(BaseModel):
    """Response for bulk operations."""

    success_count: int = Field(default=0)
    error_count: int = Field(default=0)
    errors: list[str] = Field(default_factory=list)


class CandidateCountsResponse(BaseModel):
    """Counts of candidates by status."""

    pending: int = Field(default=0)
    approved: int = Field(default=0)
    rejected: int = Field(default=0)
    total: int = Field(default=0)


def compute_question_hash(question: str) -> str:
    """Compute a dedup hash for a question."""
    return hashlib.sha256(question.strip().lower().encode()).hexdigest()[:16]
