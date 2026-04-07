"""
routes/health.py — Comprehensive health-check endpoint.

  GET /health        → full status of all services (latency + detail)
  GET /health/ping   → ultra-fast liveness probe (returns 200 immediately)
"""

import time
import os
from typing import Any

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from config import (
    mongo_client, chroma_client, knowledge_col,
    GEMINI_KEY, OPENROUTER_KEY, GROQ_KEY, HUGGINGFACE_KEY, TOGETHER_KEY,
    BREVO_API_KEY, BREVO_SENDER_EMAIL,
    RESEND_API_KEY,
    SMTP_USER, SMTP_PASSWORD,
    GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET,
)

router = APIRouter()


# ── Helper: timed check ───────────────────────────────────────────────────────

def _ok(detail: Any = None, latency_ms: float = 0.0) -> dict:
    return {"status": "ok", "detail": detail, "latency_ms": round(latency_ms, 1)}


def _err(detail: Any, latency_ms: float = 0.0) -> dict:
    return {"status": "error", "detail": str(detail), "latency_ms": round(latency_ms, 1)}


def _key_status(key: str, label: str) -> dict:
    """Return configured/missing status for an API key — never reveals the key itself."""
    if key:
        masked = key[:6] + "…" + key[-3:] if len(key) > 10 else "***"
        return {"status": "configured", "detail": f"{label} key present ({masked})"}
    return {"status": "missing", "detail": f"{label} key not set in .env"}


# ── Individual service checks ─────────────────────────────────────────────────

async def _check_mongodb() -> dict:
    t0 = time.perf_counter()
    try:
        result = await mongo_client.admin.command("ping")
        latency = (time.perf_counter() - t0) * 1000
        ok = result.get("ok") == 1.0
        if ok:
            # Also count documents in users collection as a sanity check
            db = mongo_client["twin_database"]
            user_count = await db["users"].count_documents({})
            return _ok(f"Connected — {user_count} user(s) in DB", latency)
        return _err("Ping returned ok≠1", latency)
    except Exception as e:
        return _err(e, (time.perf_counter() - t0) * 1000)


def _check_chromadb() -> dict:
    t0 = time.perf_counter()
    try:
        heartbeat = chroma_client.heartbeat()
        doc_count = knowledge_col.count()
        latency = (time.perf_counter() - t0) * 1000
        return _ok(f"Connected — {doc_count} document(s) in knowledge collection", latency)
    except Exception as e:
        return _err(e, (time.perf_counter() - t0) * 1000)


def _check_gemini() -> dict:
    t0 = time.perf_counter()
    if not GEMINI_KEY:
        return _err("GEMINI_API_KEY not set in .env")
    try:
        import google.generativeai as genai  # pyright: ignore
        genai.configure(api_key=GEMINI_KEY)
        models = list(genai.list_models())
        latency = (time.perf_counter() - t0) * 1000
        gemini_models = [m.name for m in models if "generateContent" in getattr(m, "supported_generation_methods", [])]
        return _ok(f"Authenticated — {len(gemini_models)} generative model(s) available", latency)
    except Exception as e:
        return _err(e, (time.perf_counter() - t0) * 1000)


def _check_openrouter() -> dict:
    if not OPENROUTER_KEY:
        return _err("OPENROUTER_API_KEY not set in .env")
    t0 = time.perf_counter()
    try:
        import urllib.request, json
        req = urllib.request.Request(
            "https://openrouter.ai/api/v1/models",
            headers={"Authorization": f"Bearer {OPENROUTER_KEY}"},
        )
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read())
            count = len(data.get("data", []))
            latency = (time.perf_counter() - t0) * 1000
            return _ok(f"Authenticated — {count} model(s) available", latency)
    except Exception as e:
        return _err(e, (time.perf_counter() - t0) * 1000)


def _check_groq() -> dict:
    if not GROQ_KEY:
        return _err("GROQ_API_KEY not set in .env")
    t0 = time.perf_counter()
    try:
        import urllib.request, json
        req = urllib.request.Request(
            "https://api.groq.com/openai/v1/models",
            headers={"Authorization": f"Bearer {GROQ_KEY}"},
        )
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read())
            count = len(data.get("data", []))
            latency = (time.perf_counter() - t0) * 1000
            return _ok(f"Authenticated — {count} model(s) available", latency)
    except Exception as e:
        return _err(e, (time.perf_counter() - t0) * 1000)


def _check_huggingface() -> dict:
    if not HUGGINGFACE_KEY:
        return _err("HUGGINGFACE_API_KEY not set in .env")
    t0 = time.perf_counter()
    try:
        import urllib.request, json
        req = urllib.request.Request(
            "https://huggingface.co/api/whoami-v2",
            headers={"Authorization": f"Bearer {HUGGINGFACE_KEY}"},
        )
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read())
            name = data.get("name") or data.get("fullname") or "unknown"
            latency = (time.perf_counter() - t0) * 1000
            return _ok(f"Authenticated as '{name}'", latency)
    except Exception as e:
        return _err(e, (time.perf_counter() - t0) * 1000)


def _check_together() -> dict:
    if not TOGETHER_KEY:
        return _err("TOGETHER_API_KEY not set in .env")
    t0 = time.perf_counter()
    try:
        import urllib.request, json
        req = urllib.request.Request(
            "https://api.together.xyz/v1/models",
            headers={"Authorization": f"Bearer {TOGETHER_KEY}"},
        )
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read())
            count = len(data) if isinstance(data, list) else len(data.get("data", []))
            latency = (time.perf_counter() - t0) * 1000
            return _ok(f"Authenticated — {count} model(s) listed", latency)
    except Exception as e:
        return _err(e, (time.perf_counter() - t0) * 1000)


def _check_email_providers() -> dict:
    providers = {}

    # Brevo
    if BREVO_API_KEY and BREVO_SENDER_EMAIL:
        providers["brevo"] = {"status": "configured", "detail": f"Sender: {BREVO_SENDER_EMAIL}"}
    else:
        providers["brevo"] = {"status": "missing", "detail": "BREVO_API_KEY / BREVO_SENDER_EMAIL not set"}

    # Resend
    if RESEND_API_KEY:
        providers["resend"] = {"status": "configured", "detail": "RESEND_API_KEY present"}
    else:
        providers["resend"] = {"status": "missing", "detail": "RESEND_API_KEY not set"}

    # SMTP
    if SMTP_USER and SMTP_PASSWORD:
        providers["smtp"] = {"status": "configured", "detail": f"SMTP user: {SMTP_USER}"}
    else:
        providers["smtp"] = {"status": "missing", "detail": "SMTP_USER / SMTP_PASSWORD not set"}

    any_ok = any(p["status"] == "configured" for p in providers.values())
    return {
        "status": "ok" if any_ok else "warning",
        "detail": "At least one email provider is configured" if any_ok else "No email provider configured — OTP emails will print to terminal only",
        "providers": providers,
    }


def _check_google_oauth() -> dict:
    if GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET:
        return {
            "status": "configured",
            "detail": f"Client ID: {GOOGLE_CLIENT_ID[:12]}…",
        }
    return {
        "status": "missing",
        "detail": "GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET not set — Google OAuth disabled",
    }


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/health/ping")
async def health_ping():
    """Ultra-fast liveness probe — always returns 200 if the server is alive."""
    return {"status": "alive", "timestamp": time.time()}


@router.get("/health")
async def health_check():
    """
    Full health check — probes every integrated service and returns:
    - status: 'healthy' | 'degraded' | 'unhealthy'
    - per-service status, latency, and detail
    - overall summary counts
    """
    started_at = time.time()

    # Run all checks (MongoDB and Gemini are async/blocking; others are sync)
    checks = {}

    checks["mongodb"]     = await _check_mongodb()
    checks["chromadb"]    = _check_chromadb()
    checks["gemini"]      = _check_gemini()
    checks["openrouter"]  = _check_openrouter()
    checks["groq"]        = _check_groq()
    checks["huggingface"] = _check_huggingface()
    checks["together_ai"] = _check_together()
    checks["email"]       = _check_email_providers()
    checks["google_oauth"] = _check_google_oauth()

    # ── Tally results ─────────────────────────────────────────────────────────
    critical_services = ["mongodb", "chromadb"]
    ai_services = ["gemini", "openrouter", "groq", "huggingface", "together_ai"]

    critical_ok = all(checks[s]["status"] == "ok" for s in critical_services)
    ai_count_ok = sum(1 for s in ai_services if checks[s]["status"] == "ok")

    if critical_ok and ai_count_ok >= 1:
        overall = "healthy"
    elif critical_ok:
        overall = "degraded"
    else:
        overall = "unhealthy"

    http_status = 200 if overall == "healthy" else (207 if overall == "degraded" else 503)

    body = {
        "status": overall,
        "timestamp": started_at,
        "elapsed_ms": round((time.time() - started_at) * 1000, 1),
        "summary": {
            "critical_services": f"{sum(1 for s in critical_services if checks[s]['status'] == 'ok')}/{len(critical_services)} ok",
            "ai_providers": f"{ai_count_ok}/{len(ai_services)} ok",
        },
        "services": checks,
    }

    return JSONResponse(content=body, status_code=http_status)
