"""Suggestions API endpoint for question suggestions."""

import logging
from datetime import datetime, timedelta

from fastapi import APIRouter

from text_to_sql.models.responses import SuggestedQuestionsResponse
from text_to_sql.services.suggestions import get_suggestions_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/suggestions")

# Simple in-memory cache for initial questions
_cache: dict[str, tuple[list[str], datetime]] = {}
CACHE_TTL_MINUTES = 5


def _get_cached_questions() -> list[str] | None:
    """Get cached initial questions if still valid."""
    if "initial" in _cache:
        questions, timestamp = _cache["initial"]
        if datetime.now() - timestamp < timedelta(minutes=CACHE_TTL_MINUTES):
            return questions
    return None


def _set_cached_questions(questions: list[str]) -> None:
    """Cache initial questions."""
    _cache["initial"] = (questions, datetime.now())


@router.get("/initial", response_model=SuggestedQuestionsResponse)
async def get_initial_suggestions() -> SuggestedQuestionsResponse:
    """Get initial question suggestions for a new chat.

    Returns up to 3 suggested questions based on the database schema.
    Results are cached for 5 minutes to reduce LLM calls.
    """
    # Check cache first
    cached = _get_cached_questions()
    if cached:
        logger.debug("Returning cached initial questions")
        return SuggestedQuestionsResponse(
            questions=cached,
            context_type="initial",
        )

    # Generate new questions
    service = get_suggestions_service()
    questions = await service.generate_initial_questions(n=3)

    # Cache the results
    _set_cached_questions(questions)

    return SuggestedQuestionsResponse(
        questions=questions,
        context_type="initial",
    )
