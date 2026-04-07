"""
routes/chat.py — Persistent chat session endpoints:
  POST   /chat/save
  GET    /chat/sessions
  GET    /chat/load
  DELETE /chat/session/{session_id}
"""

from datetime import datetime

from fastapi import APIRouter, HTTPException

from config import chat_sessions_col

router = APIRouter()


@router.post("/chat/save")
async def save_chat_session(data: dict):
    """Save or update a chat session for a user."""
    user_id    = data.get("user_id")
    session_id = data.get("session_id")
    messages   = data.get("messages", [])
    timestamps = data.get("timestamps", [])
    title      = data.get("title", "Chat")
    if not user_id or not session_id:
        raise HTTPException(status_code=400, detail="user_id and session_id required")
    await chat_sessions_col.update_one(
        {"user_id": user_id, "session_id": session_id},
        {"$set": {
            "user_id": user_id,
            "session_id": session_id,
            "messages": messages,
            "timestamps": timestamps,
            "title": title,
            "updated_at": datetime.utcnow().isoformat()
        }},
        upsert=True
    )
    return {"status": "saved"}


@router.get("/chat/sessions")
async def get_chat_sessions(user_id: str):
    """List all chat sessions for a user, newest first — metadata only (no messages)."""
    cursor = chat_sessions_col.find(
        {"user_id": user_id},
        {"_id": 0, "session_id": 1, "title": 1, "updated_at": 1, "message_count": 1}
    ).sort("updated_at", -1).limit(50)
    sessions = await cursor.to_list(length=50)
    return {"sessions": sessions}


@router.get("/chat/load")
async def load_chat_session(user_id: str, session_id: str):
    """Load a specific chat session."""
    doc = await chat_sessions_col.find_one(
        {"user_id": user_id, "session_id": session_id},
        {"_id": 0}
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Session not found")
    return doc


@router.delete("/chat/session/{session_id}")
async def delete_chat_session(session_id: str, user_id: str):
    """Delete a chat session."""
    await chat_sessions_col.delete_one({"user_id": user_id, "session_id": session_id})
    return {"status": "deleted"}
