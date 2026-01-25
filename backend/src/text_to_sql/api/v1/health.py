"""Health check endpoint."""

from fastapi import APIRouter

from text_to_sql import __version__
from text_to_sql.models.responses import HealthResponse
from text_to_sql.services.database import get_database_service
from text_to_sql.services.vector_store import get_vector_store_service

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Check the health of the service and its dependencies."""
    services = {}

    # Check vector store
    try:
        vs = get_vector_store_service()
        vs.get_sql_pairs_count()  # Simple operation to verify connection
        services["vector_store"] = True
    except Exception:
        services["vector_store"] = False

    # Check database
    try:
        db = get_database_service()
        services["database"] = await db.test_connection()
    except Exception:
        services["database"] = False

    # Determine overall status
    all_healthy = all(services.values())
    some_healthy = any(services.values())

    if all_healthy:
        status = "healthy"
    elif some_healthy:
        status = "degraded"
    else:
        status = "unhealthy"

    return HealthResponse(
        status=status,  # type: ignore
        version=__version__,
        services=services,
    )
