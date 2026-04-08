"""
config.py — Centralized configuration, database clients, and shared AI state.
All other modules import from here instead of re-reading env vars.
"""

import os

# Load .env file automatically — searches current dir and parent dirs
try:
    from dotenv import load_dotenv, find_dotenv
    _env_path = find_dotenv(usecwd=True)
    if _env_path:
        load_dotenv(_env_path, override=True)
    else:
        load_dotenv(override=True)
except ImportError:
    pass

import chromadb
from motor.motor_asyncio import AsyncIOMotorClient
import google.generativeai as genai  # pyright: ignore[reportMissingImports]

# ── MongoDB ──────────────────────────────────────────────────────────────────
MONGO_URL = os.getenv("MONGO_URI", "mongodb+srv://twinx:twinx@twinx.0a4mucd.mongodb.net/?appName=TwinX")
mongo_client = AsyncIOMotorClient(MONGO_URL)
db = mongo_client["twin_database"]
users_collection = db["users"]
chat_sessions_col = db["chat_sessions"]
goals_col = db["goals"]
calendar_col = db["calendar_events"]

# ── ChromaDB (Cloud Migration) ───────────────────────────────────────────────
chroma_client = chromadb.CloudClient(
    api_key=os.getenv("CHROMA_API_KEY", "ck-tgR3CaYYNZhWXcimYwjPqkhXhRbZE7dUafEeDMeDf26"),
    tenant=os.getenv("CHROMA_TENANT", "ad6cacfa-6fa9-406c-8cf4-aeb743865dd9"),
    database=os.getenv("CHROMA_DATABASE", "prod")
)
knowledge_col = chroma_client.get_or_create_collection(name="user_knowledge")

# ── In-memory chat history ────────────────────────────────────────────────────
chat_histories: dict = {}

# ── AI Provider Keys ─────────────────────────────────────────────────────────
GEMINI_KEY      = (os.getenv("GEMINI_API_KEY", "") or os.getenv("GOOGLE_API_KEY", "")).strip()
OPENROUTER_KEY  = os.getenv("OPENROUTER_API_KEY", "").strip()
GROQ_KEY        = os.getenv("GROQ_API_KEY", "").strip()
HUGGINGFACE_KEY = os.getenv("HUGGINGFACE_API_KEY", "").strip()
TOGETHER_KEY    = os.getenv("TOGETHER_API_KEY", "").strip()

MODEL_NAME     = "gemini-flash-latest"
TOGETHER_MODEL = "meta-llama/Llama-3-8b-chat-hf"
HUGGINGFACE_MODEL = "mistralai/Mistral-7B-Instruct-v0.3"

OPENROUTER_MODELS = [
    "openrouter/auto",
    "meta-llama/llama-3.2-3b-instruct:free",
    "google/gemma-3-1b-it:free",
    "microsoft/phi-3-mini-128k-instruct:free",
]

# Configure Gemini with key at startup
genai.configure(api_key=GEMINI_KEY)

# ── Email / OAuth Config ──────────────────────────────────────────────────────
BREVO_API_KEY      = os.getenv("BREVO_API_KEY", "").strip()
BREVO_SENDER_EMAIL = os.getenv("BREVO_SENDER_EMAIL", "").strip()
BREVO_SENDER_NAME  = os.getenv("BREVO_SENDER_NAME", "AI Digital Twin").strip()

RESEND_API_KEY    = os.getenv("RESEND_API_KEY", "").strip()
RESEND_FROM_EMAIL = os.getenv("RESEND_FROM_EMAIL", "onboarding@resend.dev").strip()

SMTP_HOST     = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT     = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER     = os.getenv("SMTP_USER", "").strip()
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "").replace(" ", "").strip()

GOOGLE_CLIENT_ID     = os.getenv("GOOGLE_CLIENT_ID", "").strip()
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "").strip()
GOOGLE_REDIRECT_URI  = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/auth/google/callback").strip()
STREAMLIT_URL        = os.getenv("STREAMLIT_URL", "http://localhost:8501").strip()
