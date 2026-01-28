"""Main API v1 router."""

from fastapi import APIRouter

from text_to_sql.api.v1.csv import router as csv_router
from text_to_sql.api.v1.health import router as health_router
from text_to_sql.api.v1.query import router as query_router
from text_to_sql.api.v1.sessions import router as sessions_router

router = APIRouter(prefix="/api/v1")

router.include_router(health_router, tags=["health"])
router.include_router(query_router, tags=["query"])
router.include_router(sessions_router, tags=["sessions"])
router.include_router(csv_router, tags=["csv"])
