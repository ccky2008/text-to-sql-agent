"""CSV download endpoint."""

import csv
import io
from typing import AsyncIterator

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from text_to_sql.config import get_settings
from text_to_sql.models.requests import CSVDownloadRequest
from text_to_sql.models.responses import CSVLimitsResponse
from text_to_sql.services.database import get_database_service
from text_to_sql.services.query_cache import get_query_cache

router = APIRouter()


async def generate_csv_stream(
    sql: str,
    offset: int,
    limit: int,
) -> AsyncIterator[str]:
    """Stream CSV rows from database query.

    The caller is responsible for capping `limit` to csv_max_rows.
    """
    db_service = get_database_service()

    result = await db_service.execute_query_paginated(
        sql, offset=offset, limit=limit
    )

    if not result.success:
        raise HTTPException(
            status_code=400, detail=result.error or "Query execution failed"
        )

    if not result.rows or not result.columns:
        yield ""  # Empty CSV
        return

    # Create CSV in memory chunks
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=result.columns)

    # Write header
    writer.writeheader()
    header_line = output.getvalue()
    output.truncate(0)
    output.seek(0)
    yield header_line

    # Write rows in chunks
    chunk_size = 100
    for i in range(0, len(result.rows), chunk_size):
        chunk = result.rows[i : i + chunk_size]
        for row in chunk:
            # Convert any non-string values to strings for CSV
            cleaned_row = {k: str(v) if v is not None else "" for k, v in row.items()}
            writer.writerow(cleaned_row)
        chunk_content = output.getvalue()
        output.truncate(0)
        output.seek(0)
        yield chunk_content


@router.post("/csv")
async def download_csv(request: CSVDownloadRequest):
    """Download query results as CSV.

    Requires a valid query_token from a previously executed query.
    Enforces maximum row limit (csv_max_rows) to prevent memory issues.
    """
    settings = get_settings()

    # Look up the validated SQL from the query cache
    query_cache = get_query_cache()
    cached_query = query_cache.get(request.query_token)

    if cached_query is None:
        raise HTTPException(
            status_code=400,
            detail="Invalid or expired query token. Please re-run your query.",
        )

    sql = cached_query.sql
    limit = min(request.limit or settings.csv_max_rows, settings.csv_max_rows)

    # Sanitize filename (allow alphanumeric, dots, underscores, hyphens)
    safe_filename = "".join(
        c for c in request.filename if c.isalnum() or c in "._-"
    ).rstrip()
    if not safe_filename or safe_filename in ("", ".csv"):
        safe_filename = "query_results.csv"
    elif not safe_filename.endswith(".csv"):
        safe_filename += ".csv"

    headers = {
        "Content-Disposition": f'attachment; filename="{safe_filename}"',
        "Content-Type": "text/csv; charset=utf-8",
    }

    return StreamingResponse(
        generate_csv_stream(sql, request.offset, limit),
        headers=headers,
    )


@router.get("/csv/limits", response_model=CSVLimitsResponse)
async def get_csv_limits():
    """Get CSV download limits for frontend information."""
    settings = get_settings()
    return CSVLimitsResponse(
        max_rows_per_download=settings.csv_max_rows,
        batch_download_available=True,
        batch_download_instructions=(
            f"For datasets larger than {settings.csv_max_rows} rows, you can ask the assistant to fetch "
            "results in batches. For example: 'Get me the first 2000 records' or "
            "'Get me records 2001 to 4000'."
        ),
    )
