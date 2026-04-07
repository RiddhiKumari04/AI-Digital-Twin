# main.py — FastAPI application entry point.
import os
import sys

# Ensure backend directory is in Python path for modular imports
sys.path.append(os.path.join(os.path.dirname(__file__), "backend"))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routes import auth, twin, developer, newsroom, chat, goals, calendar, misc, health, docs

app = FastAPI(
    title="AI Digital Twin API",
    description="Backend powering TwinX — your AI Digital Twin.",
    version="2.1.0",
)

# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # For production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Route modules ─────────────────────────────────────────────────────────────
app.include_router(auth.router)
app.include_router(twin.router)
app.include_router(developer.router)
app.include_router(newsroom.router)
app.include_router(chat.router)
app.include_router(goals.router)
app.include_router(calendar.router)
app.include_router(misc.router)
app.include_router(health.router)
app.include_router(docs.router)


# ── Dev server ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)