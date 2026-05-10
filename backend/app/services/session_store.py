"""
Session storage — file-based, no login required.
Each session = JSON file with UUID.
Supports save/load/share without authentication.
"""

import json
import uuid
import os
from datetime import datetime
from pathlib import Path
from typing import Any

SESSIONS_DIR = Path(__file__).parent / "sessions"
SESSIONS_DIR.mkdir(exist_ok=True)


def create_session(messages: list[dict], itinerary: dict | None = None, title: str = "") -> dict:
    """Create a new session and save to disk."""
    session_id = str(uuid.uuid4())[:8]  # Short IDs for easy sharing
    session = {
        "id": session_id,
        "title": title or _auto_title(messages),
        "messages": messages,
        "itinerary": itinerary,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    }
    _save(session_id, session)
    return session


def load_session(session_id: str) -> dict | None:
    """Load session from disk."""
    path = SESSIONS_DIR / f"{session_id}.json"
    if not path.exists():
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def update_session(session_id: str, messages: list[dict], itinerary: dict | None = None) -> dict | None:
    """Update existing session."""
    session = load_session(session_id)
    if not session:
        return None
    session["messages"] = messages
    if itinerary is not None:
        session["itinerary"] = itinerary
    session["updated_at"] = datetime.now().isoformat()
    session["title"] = _auto_title(messages) or session.get("title", "")
    _save(session_id, session)
    return session


def list_sessions() -> list[dict]:
    """List all sessions (summary only)."""
    sessions = []
    for f in sorted(SESSIONS_DIR.glob("*.json"), key=os.path.getmtime, reverse=True):
        try:
            with open(f, "r", encoding="utf-8") as fh:
                data = json.load(fh)
                sessions.append({
                    "id": data["id"],
                    "title": data.get("title", "Untitled"),
                    "message_count": len(data.get("messages", [])),
                    "has_itinerary": data.get("itinerary") is not None,
                    "created_at": data.get("created_at", ""),
                    "updated_at": data.get("updated_at", ""),
                })
        except:
            continue
    return sessions[:50]  # Max 50 recent


def delete_session(session_id: str) -> bool:
    path = SESSIONS_DIR / f"{session_id}.json"
    if path.exists():
        path.unlink()
        return True
    return False


def _save(session_id: str, data: dict):
    path = SESSIONS_DIR / f"{session_id}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _auto_title(messages: list[dict]) -> str:
    """Generate title from first user message."""
    for msg in messages:
        if msg.get("role") == "user":
            text = msg.get("content", "")[:60]
            return text.strip() or "New Trip"
    return "New Trip"
