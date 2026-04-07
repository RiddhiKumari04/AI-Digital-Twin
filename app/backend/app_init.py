"""
app_init.py — FastAPI App Factory.
This module provides a function to create the FastAPI application and register all modular routers.
Use this in your entry point (e.g., a new main.py or server.py) to keep it clean.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routes import (
    auth, twin, developer, newsroom, 
    chat, goals, calendar, misc, health, docs
)

def create_app() -> FastAPI:
    """Initialize the FastAPI app with all routers and middleware."""
    app = FastAPI(
        title="AI Digital Twin API",
        description="Modular backend for the AI Digital Twin ecosystem.",
        version="2.1.0"
    )

    # ── Middleware ────────────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Router Registration ───────────────────────────────────────────────────
    # Public & Auth
    app.include_router(auth.router, tags=["Authentication"])
    app.include_router(docs.router, tags=["Documentation"])
    app.include_router(health.router, tags=["System Health"])
    
    # Core Twin Features
    app.include_router(twin.router, tags=["Twin Core"])
    app.include_router(newsroom.router, tags=["Newsroom"])
    
    # Productivity & Developer 
    app.include_router(developer.router, tags=["Shadow Developer"])
    app.include_router(chat.router, tags=["Chat Persistence"])
    app.include_router(goals.router, tags=["Goals & Habits"])
    app.include_router(calendar.router, tags=["Calendar Sync"])
    
    # Utilities
    app.include_router(misc.router, tags=["Utilities"])

    return app
