"""
Sessions endpoint — save, load, share chat sessions. No login required.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Any

from app.services.session_store import (
    create_session, load_session, update_session, list_sessions, delete_session,
)

router = APIRouter()


class SaveSessionRequest(BaseModel):
    session_id: str | None = None  # None = create new
    messages: list[dict] = Field(default_factory=list)
    itinerary: dict[str, Any] | None = None


class SessionResponse(BaseModel):
    id: str
    title: str
    messages: list[dict]
    itinerary: dict[str, Any] | None
    created_at: str
    updated_at: str


class SessionSummary(BaseModel):
    id: str
    title: str
    message_count: int
    has_itinerary: bool
    created_at: str
    updated_at: str


@router.post("/sessions", tags=["Sessions"])
async def save_session(req: SaveSessionRequest):
    """Create or update a session."""
    if req.session_id:
        result = update_session(req.session_id, req.messages, req.itinerary)
        if not result:
            raise HTTPException(404, "Session not found")
        return result
    else:
        return create_session(req.messages, req.itinerary)


@router.get("/sessions", tags=["Sessions"], response_model=list[SessionSummary])
async def get_sessions():
    """List all saved sessions."""
    return list_sessions()


@router.get("/sessions/{session_id}", tags=["Sessions"])
async def get_session(session_id: str):
    """Load a session by ID (for sharing)."""
    session = load_session(session_id)
    if not session:
        raise HTTPException(404, "Session not found")
    return session


@router.delete("/sessions/{session_id}", tags=["Sessions"])
async def remove_session(session_id: str):
    """Delete a session."""
    if delete_session(session_id):
        return {"status": "deleted"}
    raise HTTPException(404, "Session not found")
