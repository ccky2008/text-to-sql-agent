"""Session management endpoints."""

from fastapi import APIRouter, HTTPException

from text_to_sql.models.responses import SessionInfo, SessionListResponse
from text_to_sql.services.checkpointer import get_session_manager

router = APIRouter(prefix="/sessions")


@router.get("", response_model=SessionListResponse)
async def list_sessions() -> SessionListResponse:
    """List all active sessions."""
    session_manager = get_session_manager()
    sessions = session_manager.list_sessions()

    return SessionListResponse(
        sessions=[
            SessionInfo(
                session_id=s["session_id"],
                created_at=s["created_at"],
                last_active=s["last_active"],
                message_count=s["message_count"],
            )
            for s in sessions
        ],
        total=len(sessions),
    )


@router.get("/{session_id}", response_model=SessionInfo)
async def get_session(session_id: str) -> SessionInfo:
    """Get information about a specific session."""
    session_manager = get_session_manager()
    session = session_manager.get_session(session_id)

    if not session:
        raise HTTPException(status_code=404, detail=f"Session not found: {session_id}")

    return SessionInfo(
        session_id=session["session_id"],
        created_at=session["created_at"],
        last_active=session["last_active"],
        message_count=session["message_count"],
    )


@router.delete("/{session_id}")
async def delete_session(session_id: str) -> dict:
    """Delete a session."""
    session_manager = get_session_manager()

    if not session_manager.delete_session(session_id):
        raise HTTPException(status_code=404, detail=f"Session not found: {session_id}")

    return {"status": "deleted", "session_id": session_id}
