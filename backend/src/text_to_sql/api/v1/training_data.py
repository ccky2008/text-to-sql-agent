"""Training data candidate review API endpoints."""

import logging

from fastapi import APIRouter, HTTPException, Query

from text_to_sql.models.data_sources import SQLPair
from text_to_sql.models.training_data import (
    BulkActionRequest,
    BulkActionResponse,
    CandidateCountsResponse,
    CandidateEditRequest,
    CandidateStatus,
    SQLPairCandidateListResponse,
    SQLPairCandidateResponse,
)
from text_to_sql.services.sql_pair_candidates import get_candidate_manager
from text_to_sql.services.vector_store import get_vector_store_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/training-data")


def _doc_to_response(doc: dict) -> SQLPairCandidateResponse:
    """Convert a MongoDB document dict to a response model."""
    return SQLPairCandidateResponse.model_validate(doc)


@router.get("/candidates", response_model=SQLPairCandidateListResponse)
async def list_candidates(
    status: CandidateStatus | None = Query(None, description="Filter by status"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
) -> SQLPairCandidateListResponse:
    """List SQL pair candidates with optional status filter and pagination."""
    manager = get_candidate_manager()
    items, total = await manager.list_candidates(status=status, page=page, page_size=page_size)

    total_pages = (total + page_size - 1) // page_size if total > 0 else 0

    return SQLPairCandidateListResponse(
        items=[_doc_to_response(doc) for doc in items],
        total=total,
        page=page,
        page_size=page_size,
        has_next=page < total_pages,
        has_prev=page > 1,
    )


@router.get("/candidates/counts", response_model=CandidateCountsResponse)
async def get_counts() -> CandidateCountsResponse:
    """Get counts of candidates by status."""
    manager = get_candidate_manager()
    counts = await manager.get_counts()
    return CandidateCountsResponse(
        pending=counts.get("pending", 0),
        approved=counts.get("approved", 0),
        rejected=counts.get("rejected", 0),
        total=counts.get("total", 0),
    )


@router.get("/candidates/{candidate_id}", response_model=SQLPairCandidateResponse)
async def get_candidate(candidate_id: str) -> SQLPairCandidateResponse:
    """Get a single candidate by ID."""
    manager = get_candidate_manager()
    doc = await manager.get_candidate(candidate_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Candidate not found")
    return _doc_to_response(doc)


@router.put("/candidates/{candidate_id}", response_model=SQLPairCandidateResponse)
async def update_candidate(
    candidate_id: str, request: CandidateEditRequest
) -> SQLPairCandidateResponse:
    """Update a candidate's question and/or SQL query."""
    manager = get_candidate_manager()
    doc = await manager.update_candidate(
        candidate_id, question=request.question, sql_query=request.sql_query
    )
    if doc is None:
        raise HTTPException(status_code=404, detail="Candidate not found")
    return _doc_to_response(doc)


@router.post("/candidates/{candidate_id}/approve", response_model=SQLPairCandidateResponse)
async def approve_candidate(
    candidate_id: str, request: CandidateEditRequest | None = None
) -> SQLPairCandidateResponse:
    """Approve a candidate and add it to ChromaDB as a training SQL pair.

    Optionally override question/SQL before approving.
    """
    manager = get_candidate_manager()
    doc = await manager.get_candidate(candidate_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Candidate not found")

    # Apply overrides if provided
    has_overrides = request and (request.question is not None or request.sql_query is not None)
    if has_overrides:
        await manager.update_candidate(
            candidate_id, question=request.question, sql_query=request.sql_query
        )
        doc = await manager.get_candidate(candidate_id)

    # Add to ChromaDB (idempotent via upsert)
    vector_store = get_vector_store_service()
    vector_store.add_sql_pair(SQLPair(question=doc["question"], sql_query=doc["sql_query"]))

    # Update status and re-fetch
    await manager.update_candidate_status(candidate_id, CandidateStatus.APPROVED)
    doc = await manager.get_candidate(candidate_id)
    if doc is None:
        raise HTTPException(status_code=500, detail="Failed to fetch updated candidate")
    return _doc_to_response(doc)


@router.post("/candidates/{candidate_id}/reject", response_model=SQLPairCandidateResponse)
async def reject_candidate(candidate_id: str) -> SQLPairCandidateResponse:
    """Reject a candidate."""
    manager = get_candidate_manager()
    updated = await manager.update_candidate_status(candidate_id, CandidateStatus.REJECTED)
    if not updated:
        raise HTTPException(status_code=404, detail="Candidate not found")

    doc = await manager.get_candidate(candidate_id)
    if doc is None:
        raise HTTPException(status_code=500, detail="Failed to fetch updated candidate")
    return _doc_to_response(doc)


@router.delete("/candidates/{candidate_id}")
async def delete_candidate(candidate_id: str) -> dict:
    """Delete a candidate."""
    manager = get_candidate_manager()
    deleted = await manager.delete_candidate(candidate_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Candidate not found")
    return {"deleted": True}


@router.post("/candidates/bulk-approve", response_model=BulkActionResponse)
async def bulk_approve(request: BulkActionRequest) -> BulkActionResponse:
    """Approve multiple candidates and add them to ChromaDB."""
    manager = get_candidate_manager()
    vector_store = get_vector_store_service()
    success_count = 0
    errors: list[str] = []

    for candidate_id in request.ids:
        try:
            doc = await manager.get_candidate(candidate_id)
            if doc is None:
                errors.append(f"{candidate_id}: not found")
                continue

            pair = SQLPair(question=doc["question"], sql_query=doc["sql_query"])
            vector_store.add_sql_pair(pair)
            await manager.update_candidate_status(candidate_id, CandidateStatus.APPROVED)
            success_count += 1
        except Exception as e:
            errors.append(f"{candidate_id}: {e}")

    return BulkActionResponse(
        success_count=success_count,
        error_count=len(errors),
        errors=errors,
    )


@router.post("/candidates/bulk-reject", response_model=BulkActionResponse)
async def bulk_reject(request: BulkActionRequest) -> BulkActionResponse:
    """Reject multiple candidates."""
    manager = get_candidate_manager()
    success_count = 0
    errors: list[str] = []

    for candidate_id in request.ids:
        try:
            updated = await manager.update_candidate_status(
                candidate_id, CandidateStatus.REJECTED
            )
            if updated:
                success_count += 1
            else:
                errors.append(f"{candidate_id}: not found")
        except Exception as e:
            errors.append(f"{candidate_id}: {e}")

    return BulkActionResponse(
        success_count=success_count,
        error_count=len(errors),
        errors=errors,
    )
