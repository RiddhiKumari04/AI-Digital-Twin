"""
main.py — FastAPI application entry point.

Only responsibilities:
  - Create the FastAPI app
  - Configure CORS middleware
  - Include all route modules
  - Start uvicorn (when run directly)

All business logic lives in the submodules:
  config.py        — env vars, DB clients, shared state
  ai_providers.py  — multi-provider AI fallback chain
  models.py        — Pydantic request/response models
  utils.py         — utility helpers (syntax check, code exec, web search, …)
  routes/
    auth.py        — register, login, OTP, Google OAuth, profile photo
    twin.py        — ask, ask_stream, train, memories, export, analytics, …
    developer.py   — debug_code, repo_files  (Shadow Developer)
    newsroom.py    — morning_briefing  (Twin Newsroom)
    chat.py        — persistent chat sessions
    goals.py       — goals & habits
    calendar.py    — calendar events + Google Calendar sync
    misc.py        — translate
    health.py      — /health, /health/ping (service status)
    docs.py        — /api-docs (custom branded API documentation)
"""

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