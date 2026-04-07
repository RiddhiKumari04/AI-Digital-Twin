import os
import random
import io
import re
import ast
import sys
import subprocess
import tempfile
import difflib
import traceback
from pathlib import Path
from typing import List, Optional

# Load .env file automatically — searches current dir and parent dirs
try:
    from dotenv import load_dotenv, find_dotenv  # pip install python-dotenv
    _env_path = find_dotenv(usecwd=True)   # finds .env in cwd or any parent folder
    if _env_path:
        load_dotenv(_env_path, override=True)
    else:
        load_dotenv(override=True)         # fallback: try cwd directly
except ImportError:
    pass  # python-dotenv not installed — env vars must be set in system environment

import pandas as pd
from fastapi import FastAPI, HTTPException, File, UploadFile, Form, Request
from fastapi.responses import StreamingResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
import httpx
import chromadb
from motor.motor_asyncio import AsyncIOMotorClient
from langchain_google_genai import GoogleGenerativeAI
from langchain_core.prompts import PromptTemplate
from pydantic import BaseModel
import google.generativeai as genai  # pyright: ignore[reportMissingImports]

app = FastAPI()

# --- CORS SETUP ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- DATABASE SETUP ---
MONGO_URL = os.getenv("MONGO_URI", "mongodb+srv://admin:admin@twinx.wzsopcx.mongodb.net/?appName=TwinX")
mongo_client = AsyncIOMotorClient(MONGO_URL)
db = mongo_client["twin_database"]
users_collection = db["users"]

chroma_client = chromadb.PersistentClient(path="./twin_db")
knowledge_col = chroma_client.get_or_create_collection(name="user_knowledge")

# --- CHAT HISTORY STORAGE ---
chat_histories = {}

# --- AI SETUP ---
GEMINI_KEY      = os.getenv("GEMINI_API_KEY", "").strip()
OPENROUTER_KEY  = os.getenv("OPENROUTER_API_KEY", "").strip()
GROQ_KEY        = os.getenv("GROQ_API_KEY", "").strip()
HUGGINGFACE_KEY = os.getenv("HUGGINGFACE_API_KEY", "").strip()
TOGETHER_KEY    = os.getenv("TOGETHER_API_KEY", "").strip()

genai.configure(api_key=GEMINI_KEY)

MODEL_NAME = "gemini-flash-latest"

# OpenRouter free models to try in order (auto = best available free model)
OPENROUTER_MODELS = [
    "openrouter/auto",
    "meta-llama/llama-3.2-3b-instruct:free",
    "google/gemma-3-1b-it:free",
    "microsoft/phi-3-mini-128k-instruct:free",
]

# Together AI model
TOGETHER_MODEL = "meta-llama/Llama-3-8b-chat-hf"

# Hugging Face model
HUGGINGFACE_MODEL = "mistralai/Mistral-7B-Instruct-v0.3"


def _openrouter_generate(prompt: str, model: str = "openrouter/auto") -> str:
    """Call OpenRouter API with specified model. Raises on error."""
    import urllib.request as _ur
    import json as _j
    payload = _j.dumps({
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 1024,
        "temperature": 0.4,
    }).encode("utf-8")
    req = _ur.Request(
        "https://openrouter.ai/api/v1/chat/completions",
        data=payload,
        headers={
            "Authorization": f"Bearer {OPENROUTER_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost:8501",
            "X-Title": "AI Digital Twin",
        },
        method="POST",
    )
    try:
        with _ur.urlopen(req, timeout=30) as resp:
            data = _j.loads(resp.read().decode())
            text = data["choices"][0]["message"]["content"].strip()
            if not text:
                raise RuntimeError("Empty response from OpenRouter")
            return text
    except Exception as e:
        raise RuntimeError(f"OpenRouter[{model}] error: {e}")


def _groq_generate(prompt: str) -> str:
    """Call Groq API (OpenAI-compatible). Raises on error."""
    import urllib.request as _ur
    import json as _j
    payload = _j.dumps({
        "model": "llama-3.1-8b-instant",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 1024,
        "temperature": 0.4,
    }).encode("utf-8")
    req = _ur.Request(
        "https://api.groq.com/openai/v1/chat/completions",
        data=payload,
        headers={
            "Authorization": f"Bearer {GROQ_KEY}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with _ur.urlopen(req, timeout=20) as resp:
            data = _j.loads(resp.read().decode())
            text = data["choices"][0]["message"]["content"].strip()
            if not text: raise RuntimeError("Empty response from Groq")
            return text
    except Exception as e:
        raise RuntimeError(f"Groq error: {e}")


def _together_generate(prompt: str) -> str:
    """Call Together AI API (OpenAI-compatible). Raises on error."""
    import urllib.request as _ur
    import json as _j
    payload = _j.dumps({
        "model": TOGETHER_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 1024,
        "temperature": 0.4,
    }).encode("utf-8")
    req = _ur.Request(
        "https://api.together.xyz/v1/chat/completions",
        data=payload,
        headers={
            "Authorization": f"Bearer {TOGETHER_KEY}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with _ur.urlopen(req, timeout=30) as resp:
            data = _j.loads(resp.read().decode())
            text = data["choices"][0]["message"]["content"].strip()
            if not text:
                raise RuntimeError("Empty response from Together AI")
            return text
    except Exception as e:
        raise RuntimeError(f"Together AI error: {e}")


def _huggingface_generate(prompt: str) -> str:
    """Call Hugging Face Inference API. Raises on error."""
    import urllib.request as _ur
    import json as _j
    payload = _j.dumps({
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 1024,
        "temperature": 0.4,
    }).encode("utf-8")
    req = _ur.Request(
        f"https://api-inference.huggingface.co/models/{HUGGINGFACE_MODEL}/v1/chat/completions",
        data=payload,
        headers={
            "Authorization": f"Bearer {HUGGINGFACE_KEY}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with _ur.urlopen(req, timeout=30) as resp:
            data = _j.loads(resp.read().decode())
            text = data["choices"][0]["message"]["content"].strip()
            if not text:
                raise RuntimeError("Empty response from Hugging Face")
            return text
    except Exception as e:
        raise RuntimeError(f"Hugging Face error: {e}")


def generate_ai_response(prompt: str) -> str:
    """
    Generate an AI response with automatic fallback:
      1. Gemini          (priority 1)
      2. OpenRouter/auto (priority 2)
      3. Groq            (priority 3)
      4. Hugging Face    (priority 4)
      5. Together AI     (priority 5)
    Never shows an absolute error unless all 5 providers fail.
    """
    # ── 1. Try Gemini ──────────────────────────────────
    try:
        genai.configure(api_key=GEMINI_KEY)
        gem_model = genai.GenerativeModel("gemini-1.5-flash") # Use flash for speed
        response = gem_model.generate_content(prompt)
        print("[AI] ✓ Gemini responded")
        return response.text
    except Exception as e:
        print(f"[AI] Gemini failed ({e}), trying OpenRouter...")

    # ── 2. Try OpenRouter ───────────────────────
    try:
        result = _openrouter_generate(prompt, model="openrouter/auto")
        print("[AI] ✓ OpenRouter responded")
        return result
    except Exception as e:
        print(f"[AI] OpenRouter failed ({e}), trying Groq...")

    # ── 3. Try Groq ──────────────────────────
    try:
        result = _groq_generate(prompt)
        print("[AI] ✓ Groq responded")
        return result
    except Exception as e:
        print(f"[AI] Groq failed ({e}), trying Hugging Face...")

    # ── 4. Try Hugging Face ──────────────────────────
    try:
        result = _huggingface_generate(prompt)
        print("[AI] ✓ Hugging Face responded")
        return result
    except Exception as e:
        print(f"[AI] Hugging Face failed ({e}), trying Together AI...")

    # ── 5. Try Together AI ──────────────────────────
    try:
        result = _together_generate(prompt)
        print("[AI] ✓ Together AI responded")
        return result
    except Exception as e:
        print(f"[AI] Together AI also failed ({e})")
        raise RuntimeError("All 5 AI providers are offline or at capacity. Please try again later.")


def _looks_like_realtime_request(text: str) -> bool:
    t = (text or "").lower()
    keywords = [
        "price", "prices", "best price", "cheapest", "buy",
        "where to buy", "amazon", "flipkart", "myntra",
        "ajio", "shop", "link", "available",
    ]
    return any(k in t for k in keywords)


def web_search_snippets(query: str, max_results: int = 5) -> str:
    try:
        try:
            from ddgs import DDGS  # type: ignore  # new package name (pip install ddgs)
        except ImportError:
            from duckduckgo_search import DDGS  # type: ignore  # old package name fallback
    except Exception:
        return ""
    results = []
    try:
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=max_results):
                title = (r.get("title") or "").strip()
                href = (r.get("href") or r.get("link") or "").strip()
                body = (r.get("body") or "").strip()
                if title and href:
                    if body:
                        results.append(f"- {title} — {href}\n  {body}")
                    else:
                        results.append(f"- {title} — {href}")
    except Exception:
        return ""
    return "\n".join(results)


# llm: uses the full fallback chain (Groq → Gemini → OpenRouter)
class _FallbackLLM:
    """Drop-in replacement for LangChain LLM — uses the full fallback chain."""
    def invoke(self, prompt: str) -> str:
        return generate_ai_response(prompt)

llm = _FallbackLLM()

RAG_TEMPLATE = (
    "You are the AI Digital Twin of {user_id}. Personality Mode: {mood}\n"
    "Conversation History:\n{history}\n\n"
    "RULES:\n"
    "- Answer strictly based ONLY on the Context provided below.\n"
    '- If the answer is not in the context, you MUST say: "Sorry i dont have any knowledge about this."\n'
    "- Use Web Search only if the user asks for real-time information like prices or gifts.\n"
    "- Be natural and keep responses concise.\n\n"
    "Context:\n{context}\n\n"
    "Question:\n{question}\n\n"
    "Answer:"
)

rag_prompt = PromptTemplate(
    template=RAG_TEMPLATE,
    input_variables=["user_id", "context", "question", "mood", "history"],
)


class UserRegister(BaseModel):
    name: str
    email: str
    password: str


# ─────────────────────────────────────────────
# SHADOW DEVELOPER — HELPER UTILITIES
# ─────────────────────────────────────────────

LANGUAGE_EXTENSIONS = {
    "python": ".py",
    "javascript": ".js",
    "typescript": ".ts",
    "java": ".java",
    "c++": ".cpp",
    "c": ".c",
    "go": ".go",
    "rust": ".rs",
    "bash": ".sh",
    "other": ".txt",
}

RUNNABLE_LANGUAGES = {"python", "javascript", "bash"}


def detect_syntax_errors(code: str, language: str) -> dict:
    """
    Attempt static syntax checking before sending to Gemini.
    Returns {"has_errors": bool, "errors": [str], "warnings": [str]}
    """
    lang = language.lower()
    errors = []
    warnings = []

    if lang == "python":
        try:
            ast.parse(code)
        except SyntaxError as e:
            errors.append(
                f"SyntaxError on line {e.lineno}: {e.msg}"
                + (f" — near `{e.text.strip()}`" if e.text else "")
            )
        except Exception as e:
            errors.append(f"Parse error: {str(e)}")

        # Simple heuristic warnings
        lines = code.splitlines()
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if stripped.startswith("print ") and not stripped.startswith("print("):
                warnings.append(f"Line {i}: Looks like Python 2 print statement — use print()")
            if "==" in stripped and stripped.startswith("if") and "is None" not in stripped and "== None" in stripped:
                warnings.append(f"Line {i}: Use `is None` instead of `== None`")
            if stripped.startswith("except:") or stripped == "except :":
                warnings.append(f"Line {i}: Bare `except:` catches everything — consider `except Exception as e:`")

    elif lang in ("javascript", "typescript"):
        # Basic JS/TS heuristics
        lines = code.splitlines()
        open_braces = code.count("{")
        close_braces = code.count("}")
        if open_braces != close_braces:
            errors.append(
                f"Mismatched braces: {open_braces} opening vs {close_braces} closing."
            )
        open_parens = code.count("(")
        close_parens = code.count(")")
        if open_parens != close_parens:
            errors.append(
                f"Mismatched parentheses: {open_parens} opening vs {close_parens} closing."
            )
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if stripped.startswith("var "):
                warnings.append(f"Line {i}: Consider replacing `var` with `let` or `const`.")
            if "==" in stripped and "===" not in stripped and "!==" not in stripped:
                warnings.append(f"Line {i}: Prefer `===` over `==` for strict equality.")

    elif lang in ("c", "c++"):
        lines = code.splitlines()
        open_braces = code.count("{")
        close_braces = code.count("}")
        if open_braces != close_braces:
            errors.append(
                f"Mismatched braces: {open_braces} opening vs {close_braces} closing."
            )
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if "gets(" in stripped:
                warnings.append(f"Line {i}: `gets()` is unsafe — use `fgets()` instead.")
            if "strcpy(" in stripped:
                warnings.append(f"Line {i}: `strcpy()` can overflow — consider `strncpy()`.")

    elif lang == "java":
        lines = code.splitlines()
        open_braces = code.count("{")
        close_braces = code.count("}")
        if open_braces != close_braces:
            errors.append(
                f"Mismatched braces: {open_braces} opening vs {close_braces} closing."
            )
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if "System.out.print" not in stripped and "==" in stripped:
                if ".equals(" not in stripped:
                    # Only warn for String-looking comparisons
                    if '"' in stripped:
                        warnings.append(
                            f"Line {i}: String comparison with `==` may fail — use `.equals()`."
                        )

    return {
        "has_errors": len(errors) > 0,
        "errors": errors,
        "warnings": warnings,
    }


def execute_code(code: str, language: str, timeout: int = 10) -> dict:
    """
    Safely execute code in a subprocess and return stdout/stderr.
    Only runs Python, JavaScript (node), and Bash.
    """
    lang = language.lower()
    if lang not in RUNNABLE_LANGUAGES:
        return {
            "ran": False,
            "reason": f"Execution not supported for {language}. Supported: Python, JavaScript, Bash.",
            "stdout": "",
            "stderr": "",
            "exit_code": None,
        }

    ext = LANGUAGE_EXTENSIONS.get(lang, ".txt")

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=ext, delete=False, encoding="utf-8"
    ) as tmp:
        tmp.write(code)
        tmp_path = tmp.name

    try:
        if lang == "python":
            cmd = [sys.executable, tmp_path]
        elif lang == "javascript":
            cmd = ["node", tmp_path]
        elif lang == "bash":
            cmd = ["bash", tmp_path]
        else:
            return {"ran": False, "reason": "Unknown language", "stdout": "", "stderr": "", "exit_code": None}

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return {
            "ran": True,
            "stdout": result.stdout[:3000],   # cap output
            "stderr": result.stderr[:1500],
            "exit_code": result.returncode,
            "reason": "",
        }
    except subprocess.TimeoutExpired:
        return {
            "ran": True,
            "stdout": "",
            "stderr": f"⏰ Execution timed out after {timeout} seconds.",
            "exit_code": -1,
            "reason": "timeout",
        }
    except FileNotFoundError as e:
        return {
            "ran": False,
            "stdout": "",
            "stderr": "",
            "exit_code": None,
            "reason": f"Runtime not found: {str(e)}. Make sure the interpreter is installed.",
        }
    except Exception as e:
        return {
            "ran": False,
            "stdout": "",
            "stderr": "",
            "exit_code": None,
            "reason": f"Execution error: {str(e)}",
        }
    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass


def generate_diff(original: str, fixed: str, filename: str = "code") -> str:
    """Generate a unified diff between original and fixed code."""
    original_lines = original.splitlines(keepends=True)
    fixed_lines = fixed.splitlines(keepends=True)
    diff = list(
        difflib.unified_diff(
            original_lines,
            fixed_lines,
            fromfile=f"a/{filename}",
            tofile=f"b/{filename}",
            lineterm="",
        )
    )
    if not diff:
        return "No changes detected."
    return "".join(diff)


def read_git_repo_files(
    repo_path: str,
    extensions: Optional[List[str]] = None,
    max_files: int = 20,
    max_bytes_per_file: int = 8000,
) -> dict:
    """
    Walk a local git repo and return file contents.
    Returns {"files": {relative_path: content}, "errors": [str], "truncated": bool}
    """
    if extensions is None:
        extensions = [
            ".py", ".js", ".ts", ".java", ".c", ".cpp", ".go",
            ".rs", ".sh", ".html", ".css", ".json", ".md",
        ]

    repo = Path(repo_path).expanduser().resolve()
    if not repo.exists():
        return {"files": {}, "errors": [f"Path does not exist: {repo_path}"], "truncated": False}
    if not repo.is_dir():
        return {"files": {}, "errors": [f"Path is not a directory: {repo_path}"], "truncated": False}

    # Check it's actually a git repo (optional, non-blocking)
    is_git = (repo / ".git").exists()

    collected = {}
    errors = []
    truncated = False
    skipped_dirs = {
        ".git", "node_modules", "__pycache__", ".venv", "venv",
        "env", "dist", "build", ".next", ".nuxt", "target",
    }

    for root, dirs, files in os.walk(repo):
        # Prune unwanted dirs in-place
        dirs[:] = [d for d in dirs if d not in skipped_dirs and not d.startswith(".")]

        for fname in files:
            if len(collected) >= max_files:
                truncated = True
                break
            fpath = Path(root) / fname
            if fpath.suffix.lower() not in extensions:
                continue
            rel = str(fpath.relative_to(repo))
            try:
                content = fpath.read_text(encoding="utf-8", errors="replace")
                if len(content) > max_bytes_per_file:
                    content = content[:max_bytes_per_file] + f"\n... [truncated at {max_bytes_per_file} chars]"
                collected[rel] = content
            except Exception as e:
                errors.append(f"{rel}: {str(e)}")

        if truncated:
            break

    return {
        "files": collected,
        "errors": errors,
        "truncated": truncated,
        "is_git_repo": is_git,
        "total_files_found": len(collected),
    }


def extract_code_block(ai_response: str) -> str:
    """
    Pull the first fenced code block out of an AI response.
    Falls back to the whole response if no block found.
    """
    pattern = r"```(?:\w+)?\n(.*?)```"
    match = re.search(pattern, ai_response, re.DOTALL)
    if match:
        return match.group(1).strip()
    return ai_response.strip()


# ─────────────────────────────────────────────
# EXISTING FEATURES (unchanged)
# ─────────────────────────────────────────────

@app.get("/analytics")
async def get_analytics(user_id: str):
    results = knowledge_col.get(where={"user": user_id})
    categories = [meta.get("category", "General") for meta in results["metadatas"]]
    counts = {cat: categories.count(cat) for cat in set(categories)}
    return {"counts": counts}


@app.get("/status")
async def get_status():
    return {"mongodb": "Connected", "chromadb": "Active", "ai": MODEL_NAME}


@app.get("/memories")
async def get_memories(user_id: str):
    results = knowledge_col.get(where={"user": user_id})
    return {"memories": results["documents"], "ids": results["ids"]}


@app.delete("/memories/{memory_id}")
async def delete_memory(memory_id: str):
    knowledge_col.delete(ids=[memory_id])
    return {"status": "deleted"}


@app.get("/export")
async def export_memories(user_id: str):
    results = knowledge_col.get(where={"user": user_id})
    if not results["documents"]:
        raise HTTPException(status_code=404)
    df = pd.DataFrame(
        {
            "Memory": results["documents"],
            "Category": [m.get("category", "General") for m in results["metadatas"]],
        }
    )
    stream = io.StringIO()
    df.to_csv(stream, index=False)
    return StreamingResponse(
        io.BytesIO(stream.getvalue().encode()),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={user_id}_memories.csv"},
    )


@app.post("/train")
async def train_twin(user_id: str, details: str):
    cat_prompt = f"Categorize this fact into one word (Personal, Work, Hobby, Coding): {details}"
    category = llm.invoke(cat_prompt).strip()
    count = knowledge_col.count()
    knowledge_col.add(
        documents=[details],
        metadatas=[{"user": user_id, "category": category}],
        ids=[f"{user_id}_{count}_{random.randint(100, 999)}"],
    )
    return {"status": "success"}


# ─────────────────────────────────────────────
# AUTH — REGISTER / LOGIN / FORGOT PASSWORD (OTP)
# ─────────────────────────────────────────────

import hashlib
import time
import urllib.request
import urllib.parse
import json as _json

# In-memory OTP store  {email: {"otp": str, "expires": float}}
_otp_store: dict = {}

# ── EMAIL CONFIG ────────────────────────────────────────────────────────────
# The system tries 3 providers in order. Set at least ONE in your .env:
#
# OPTION 1 — Brevo (recommended, free 300/day, instant signup):
#   Sign up at https://app.brevo.com → API Keys → create key
#   BREVO_API_KEY=xkeysib-xxxxxxxxxxxxxxxx
#   BREVO_SENDER_EMAIL=your@email.com    ← must be verified in Brevo
#   BREVO_SENDER_NAME=AI Digital Twin    ← optional
#
# OPTION 2 — Resend (free 100/day):
#   Sign up at https://resend.com → API Keys → create key
#   RESEND_API_KEY=re_xxxxxxxxxxxx
#   RESEND_FROM_EMAIL=onboarding@resend.dev  ← use this exact address on free plan
#
# OPTION 3 — Gmail SMTP (requires App Password):
#   SMTP_USER=yourgmail@gmail.com
#   SMTP_PASSWORD=xxxx xxxx xxxx xxxx
# ───────────────────────────────────────────────────────────────────────────

BREVO_API_KEY      = os.getenv("BREVO_API_KEY", "").strip()
BREVO_SENDER_EMAIL = os.getenv("BREVO_SENDER_EMAIL", "").strip()
BREVO_SENDER_NAME  = os.getenv("BREVO_SENDER_NAME", "AI Digital Twin").strip()

RESEND_API_KEY    = os.getenv("RESEND_API_KEY", "").strip()
RESEND_FROM_EMAIL = os.getenv("RESEND_FROM_EMAIL", "onboarding@resend.dev").strip()

SMTP_HOST     = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT     = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER     = os.getenv("SMTP_USER", "").strip()
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "").replace(" ", "").strip()

# --- GOOGLE OAUTH CONFIG ---
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "").strip()
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "").strip()
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/auth/google/callback").strip()
STREAMLIT_URL = os.getenv("STREAMLIT_URL", "http://localhost:8501").strip()


def _hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def _otp_html(otp: str, purpose: str = "Verification") -> tuple:
    """Returns (plain_text, html_string) for an OTP email."""
    plain = f"Your AI Digital Twin OTP is: {otp}\nIt expires in 10 minutes.\nIf you didn't request this, ignore this email."
    html = f"""
    <div style="font-family:sans-serif;max-width:480px;margin:auto;background:#0f172a;
                color:#e2e8f0;padding:32px;border-radius:16px;border:1px solid #1e293b;">
      <h2 style="color:#38bdf8;margin-bottom:4px;">🧠 AI Digital Twin</h2>
      <p style="color:#94a3b8;margin-bottom:24px;font-size:14px;">{purpose}</p>
      <div style="background:#1e293b;border-radius:12px;padding:24px;text-align:center;
                  border:1px solid #334155;">
        <p style="margin:0 0 8px;color:#94a3b8;font-size:13px;">Your One-Time Password</p>
        <h1 style="margin:0;color:#38bdf8;font-size:3rem;letter-spacing:12px;font-family:monospace;">{otp}</h1>
      </div>
      <p style="color:#94a3b8;font-size:12px;margin-top:20px;line-height:1.6;">
        ⏰ Expires in <strong style="color:#f59e0b;">10 minutes</strong>.<br>
        If you did not request this, you can safely ignore this email.
      </p>
    </div>"""
    return plain, html


def _send_via_brevo(to_email: str, otp: str, purpose: str) -> bool:
    """Send OTP using Brevo (Sendinblue) REST API — free 300 emails/day."""
    if not BREVO_API_KEY or not BREVO_SENDER_EMAIL:
        return False
    plain, html = _otp_html(otp, purpose)
    payload = _json.dumps({
        "sender":      {"name": BREVO_SENDER_NAME, "email": BREVO_SENDER_EMAIL},
        "to":          [{"email": to_email}],
        "subject":     f"AI Digital Twin — Your OTP Code: {otp}",
        "htmlContent": html,
        "textContent": plain,
    }).encode("utf-8")
    req = urllib.request.Request(
        "https://api.brevo.com/v3/smtp/email",
        data=payload,
        headers={
            "accept":       "application/json",
            "content-type": "application/json",
            "api-key":      BREVO_API_KEY,
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            ok = resp.status in (200, 201)
            print(f"[EMAIL/Brevo] {'✓ Sent' if ok else '✗ Failed'} to {to_email} (status {resp.status})")
            return ok
    except Exception as e:
        print(f"[EMAIL/Brevo] Error: {e}")
        return False


def _send_via_resend(to_email: str, otp: str, purpose: str) -> bool:
    """Send OTP using Resend REST API — free 100 emails/day."""
    if not RESEND_API_KEY:
        return False
    plain, html = _otp_html(otp, purpose)
    payload = _json.dumps({
        "from":    RESEND_FROM_EMAIL,
        "to":      [to_email],
        "subject": f"AI Digital Twin — Your OTP Code: {otp}",
        "html":    html,
        "text":    plain,
    }).encode("utf-8")
    req = urllib.request.Request(
        "https://api.resend.com/emails",
        data=payload,
        headers={
            "Authorization": f"Bearer {RESEND_API_KEY}",
            "Content-Type":  "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            ok = resp.status in (200, 201)
            print(f"[EMAIL/Resend] {'✓ Sent' if ok else '✗ Failed'} to {to_email} (status {resp.status})")
            return ok
    except Exception as e:
        print(f"[EMAIL/Resend] Error: {e}")
        return False


def _send_via_smtp(to_email: str, otp: str, purpose: str) -> bool:
    """Send OTP via SMTP (Gmail or any provider)."""
    if not SMTP_USER or not SMTP_PASSWORD:
        return False
    import smtplib
    import ssl
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart
    plain, html = _otp_html(otp, purpose)
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"AI Digital Twin — Your OTP Code: {otp}"
    msg["From"]    = SMTP_USER
    msg["To"]      = to_email
    msg.attach(MIMEText(plain, "plain"))
    msg.attach(MIMEText(html,  "html"))
    # Try SSL/465 first, fallback STARTTLS/587
    try:
        ctx = ssl.create_default_context()
        with smtplib.SMTP_SSL(SMTP_HOST, 465, context=ctx, timeout=15) as s:
            s.login(SMTP_USER, SMTP_PASSWORD)
            s.sendmail(SMTP_USER, to_email, msg.as_string())
        print(f"[EMAIL/SMTP-SSL] ✓ Sent to {to_email}")
        return True
    except Exception as e1:
        print(f"[EMAIL/SMTP-SSL] Failed ({e1}), trying STARTTLS...")
    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as s:
            s.ehlo(); s.starttls(); s.ehlo()
            s.login(SMTP_USER, SMTP_PASSWORD)
            s.sendmail(SMTP_USER, to_email, msg.as_string())
        print(f"[EMAIL/SMTP-TLS] ✓ Sent to {to_email}")
        return True
    except Exception as e2:
        print(f"[EMAIL/SMTP-TLS] Failed ({e2})")
        return False


def _send_otp_email(to_email: str, otp: str, purpose: str = "OTP Verification") -> bool:
    """
    Universal OTP sender — tries Brevo → Resend → SMTP in order.
    If none configured, prints to terminal (dev mode).
    """
    # Try each provider in priority order
    if _send_via_brevo(to_email, otp, purpose):
        return True
    if _send_via_resend(to_email, otp, purpose):
        return True
    if _send_via_smtp(to_email, otp, purpose):
        return True

    # No provider configured — DEV MODE: print to terminal
    print(f"\n{'='*65}")
    print(f"  [DEV MODE] No email provider configured in backend/.env")
    print(f"  [DEV MODE] OTP for {to_email}  →  {otp}")
    print(f"  [DEV MODE] To send real emails, add ONE of these to backend/.env:")
    print(f"  [DEV MODE]   BREVO_API_KEY=...  +  BREVO_SENDER_EMAIL=you@gmail.com")
    print(f"  [DEV MODE]   RESEND_API_KEY=...  (free at resend.com)")
    print(f"  [DEV MODE]   SMTP_USER=you@gmail.com  +  SMTP_PASSWORD=app_password")
    print(f"{'='*65}\n")
    return True   # return True so the flow completes — user gets OTP from terminal



class ResetPasswordRequest(BaseModel):
    email: str
    otp: str
    new_password: str


@app.post("/register")
async def register(user: UserRegister):
    existing = await users_collection.find_one({"email": user.email})
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered.")
    doc = user.dict()
    doc["password"] = _hash_password(doc["password"])
    doc["is_first_login"] = True
    await users_collection.insert_one(doc)
    return {"status": "success"}


@app.get("/login")
async def login(email: str, password: str):
    hashed = _hash_password(password)
    # Try hashed password first, then plain-text (backward compat for existing accounts)
    user = await users_collection.find_one(
        {"email": email, "password": hashed}
    )
    if not user:
        # Fallback: old accounts stored plain-text — migrate on successful login
        user = await users_collection.find_one({"email": email, "password": password})
        if user:
            # Upgrade to hashed password silently
            await users_collection.update_one(
                {"email": email},
                {"$set": {"password": hashed}},
            )
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password.")
        
    is_first_login = user.get("is_first_login", False)
    if is_first_login:
        await users_collection.update_one({"email": email}, {"$set": {"is_first_login": False}})

    return {"status": "success", "name": user["name"], "is_first_login": is_first_login}


@app.post("/forgot_password/send_otp")
async def forgot_password_send_otp(email: str):
    """Check email exists, generate OTP, send via email."""
    user = await users_collection.find_one({"email": email})
    if not user:
        raise HTTPException(status_code=404, detail="No account found with this email.")
    otp = str(random.randint(100000, 999999))
    _otp_store[email] = {"otp": otp, "expires": time.time() + 600}  # 10 min
    sent = _send_otp_email(email, otp, purpose="Password Reset")
    if not sent:
        raise HTTPException(status_code=500, detail="Failed to send OTP email. Check your email provider config.")
    return {"status": "otp_sent", "message": f"OTP sent to {email}"}


@app.post("/forgot_password/verify_otp")
async def forgot_password_verify_otp(email: str, otp: str):
    """Verify the OTP without resetting — lets frontend show password fields only after valid OTP."""
    record = _otp_store.get(email)
    if not record:
        raise HTTPException(status_code=400, detail="No OTP requested for this email.")
    if time.time() > record["expires"]:
        _otp_store.pop(email, None)
        raise HTTPException(status_code=400, detail="OTP has expired. Please request a new one.")
    if record["otp"] != otp.strip():
        raise HTTPException(status_code=400, detail="Incorrect OTP.")
    return {"status": "otp_valid"}


@app.post("/forgot_password/reset")
async def forgot_password_reset(req: ResetPasswordRequest):
    """Verify OTP one final time, then update password."""
    record = _otp_store.get(req.email)
    if not record:
        raise HTTPException(status_code=400, detail="No OTP session found. Start over.")
    if time.time() > record["expires"]:
        _otp_store.pop(req.email, None)
        raise HTTPException(status_code=400, detail="OTP expired. Please request a new one.")
    if record["otp"] != req.otp.strip():
        raise HTTPException(status_code=400, detail="Incorrect OTP.")
    if len(req.new_password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters.")
    hashed = _hash_password(req.new_password)
    result = await users_collection.update_one(
        {"email": req.email},
        {"$set": {"password": hashed}},
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found.")
    _otp_store.pop(req.email, None)
    return {"status": "success", "message": "Password reset successfully. You can now log in."}



# ── PROFILE PHOTO ENDPOINTS ────────────────────────────────────────────────
@app.post("/profile/save_photo")
async def save_profile_photo(data: dict):
    user_id = data.get("user_id")
    pic_b64 = data.get("pic_b64")
    if not user_id:
        raise HTTPException(status_code=400, detail="user_id required")
    await users_collection.update_one(
        {"email": user_id},
        {"$set": {"pic_b64": pic_b64}}
    )
    return {"status": "success"}

@app.get("/profile/get_photo")
async def get_profile_photo(user_id: str):
    user = await users_collection.find_one({"email": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {"pic_b64": user.get("pic_b64")}


# ── LOGIN VIA OTP ─────────────────────────────────────────────────────────────
# Separate OTP store for login (so it doesn't clash with forgot-password OTPs)
_login_otp_store: dict = {}


@app.post("/login_otp/send")
async def login_otp_send(email: str):
    """Check account exists, send a 6-digit OTP to email for passwordless login."""
    user = await users_collection.find_one({"email": email})
    if not user:
        raise HTTPException(status_code=404, detail="No account found with this email.")
    otp = str(random.randint(100000, 999999))
    _login_otp_store[email] = {"otp": otp, "expires": time.time() + 600}  # 10 min
    sent = _send_otp_email(email, otp, purpose="Login Verification")
    if not sent:
        raise HTTPException(status_code=500, detail="Failed to send OTP. Check your email provider config.")
    return {"status": "otp_sent", "message": f"OTP sent to {email}"}


@app.post("/login_otp/verify")
async def login_otp_verify(email: str, otp: str):
    """Verify OTP and log the user in — returns name on success."""
    record = _login_otp_store.get(email)
    if not record:
        raise HTTPException(status_code=400, detail="No OTP requested for this email. Please request one first.")
    if time.time() > record["expires"]:
        _login_otp_store.pop(email, None)
        raise HTTPException(status_code=400, detail="OTP has expired. Please request a new one.")
    if record["otp"] != otp.strip():
        raise HTTPException(status_code=400, detail="Incorrect OTP. Please try again.")
    # OTP valid — clear it and return user info
    _login_otp_store.pop(email, None)
    user = await users_collection.find_one({"email": email})
    if not user:
        raise HTTPException(status_code=404, detail="Account not found.")
        
    is_first_login = user.get("is_first_login", False)
    if is_first_login:
        await users_collection.update_one({"email": email}, {"$set": {"is_first_login": False}})

    return {"status": "success", "name": user["name"], "is_first_login": is_first_login}

# ── GOOGLE OAUTH ─────────────────────────────────────────────────────────────

@app.get("/auth/google/start")
async def google_auth_start():
    """Returns the Google Authorization URL."""
    if not GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=500, detail="Google Client ID not configured.")
    
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "prompt": "select_account"
    }
    url = "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode(params)
    return {"url": url}

@app.get("/auth/google/callback")
async def google_auth_callback(code: str):
    """Handles callback from Google, exchanges code for token, and fetches profile."""
    if not code:
        raise HTTPException(status_code=400, detail="Missing authorization code.")

    # 1. Exchange code for access token
    token_url = "https://oauth2.googleapis.com/token"
    data = {
        "code": code,
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "grant_type": "authorization_code",
    }
    
    async with httpx.AsyncClient() as client:
        token_resp = await client.post(token_url, data=data)
        if token_resp.status_code != 200:
            raise HTTPException(status_code=400, detail=f"Failed to fetch token: {token_resp.text}")
        token_data = token_resp.json()
        access_token = token_data.get("access_token")

        # 2. Fetch user profile from Google
        profile_url = "https://www.googleapis.com/oauth2/v3/userinfo"
        profile_resp = await client.get(profile_url, headers={"Authorization": f"Bearer {access_token}"})
        if profile_resp.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to fetch profile.")
        profile = profile_resp.json()

    email = profile.get("email")
    name = profile.get("name")
    
    if not email:
        raise HTTPException(status_code=400, detail="No email provided by Google.")

    # 3. Create or Update user in MongoDB
    user = await users_collection.find_one({"email": email})
    if not user:
        # Create user with a dummy password since it's an OAuth user
        await users_collection.insert_one({
            "email": email,
            "name": name or email,
            "password": _hash_password(f"google_oauth_{random.randint(0, 999999)}")
        })
    
    # 4. Redirect to Streamlit with auth params
    # We use query params to pass login state back to Streamlit
    # IMPORTANT: In a production app, use a secure session or JWT token instead!
    final_params = {
        "_act": "google_login",
        "_email": email,
        "_name": name or email
    }
    redirect_url = f"{STREAMLIT_URL}/?{urllib.parse.urlencode(final_params)}"
    return RedirectResponse(url=redirect_url)


@app.get("/recommend_gift")
async def recommend_gift(user_id: str, person_name: str, mood: str):
    results = knowledge_col.query(
        query_texts=[f"About {person_name}"], n_results=5, where={"user": user_id}
    )
    context = (
        "\n".join(results["documents"][0])
        if results["documents"]
        else f"No specific memories of {person_name}."
    )
    search_block = web_search_snippets(
        f"best gift ideas for {person_name} price India", max_results=5
    )
    prompt = (
        f"You are the AI Digital Twin of {user_id}. Personality: {mood}\n"
        f"MEMORIES OF {person_name}: {context}\n"
        f"TASK: Recommend 3 gift ideas for {person_name} based on these memories. "
        "If web results are provided, use them to suggest real products and approximate prices.\n\n"
        f"WEB RESULTS:\n{search_block if search_block else 'No web results available.'}\n"
    )
    try:
        answer = generate_ai_response(prompt)
        return {"answer": answer}
    except Exception as e:
        return {"answer": f"Gift Agent Error: {str(e)}"}


@app.post("/analyze_image")
async def analyze_image(
    user_id: str,
    question: str,
    mood: str,
    files: List[UploadFile] = File(...),
):
    results = knowledge_col.query(
        query_texts=[question, "fashion preferences"], n_results=5, where={"user": user_id}
    )
    context = (
        "\n".join(results["documents"][0])
        if results["documents"]
        else "No specific personal preference found."
    )
    image_parts = []
    for f in files:
        image_data = await f.read()
        image_parts.append({"mime_type": f.content_type, "data": image_data})

    prompt = (
        f"You are the AI Digital Twin of {user_id}. Personality Mode: {mood}\n"
        f"USER PERSONAL CONTEXT: {context}\n"
        f"QUESTION: {question}\n\n"
        "Analyze the image and user preferences."
    )
    if _looks_like_realtime_request(question):
        search_block = web_search_snippets(f"{question} t-shirt price", max_results=6)
        prompt += f"\n\nWEB RESULTS:\n{search_block if search_block else 'No web results available.'}\n"

    try:
        # Vision: try Gemini first (it supports images), fallback to text-only for others
        try:
            genai.configure(api_key=GEMINI_KEY)
            vision_model = genai.GenerativeModel(MODEL_NAME)
            response = vision_model.generate_content([prompt] + image_parts)
            answer = response.text
        except Exception:
            answer = generate_ai_response(prompt)  # fallback: text-only
        if user_id not in chat_histories:
            chat_histories[user_id] = []
        chat_histories[user_id].extend(
            [f"User (Image): {question}", f"Twin: {answer}"]
        )
        return {"answer": answer}
    except Exception as e:
        return {"answer": f"Vision AI Error: {str(e)}"}


@app.get("/ask")
async def ask_twin(user_id: str, question: str, mood: str = "Natural"):
    results = knowledge_col.query(
        query_texts=[question], n_results=3, where={"user": user_id}
    )
    context = "\n".join(results["documents"][0]) if results["documents"] else ""
    # Keep only the last 3 exchanges (6 lines) for speed
    history_text = "\n".join(chat_histories.get(user_id, [])[-6:])
    try:
        prompt = (
            f"You are the AI Digital Twin of {user_id}. Personality Mode: {mood}\n"
            f"Context:\n{context}\n\n"
            f"Conversation History:\n{history_text}\n\n"
            f"User Question:\n{question}\n\n"
        )
        if _looks_like_realtime_request(question):
            search_block = web_search_snippets(question, max_results=4)
            prompt += f"WEB RESULTS:\n{search_block if search_block else 'No web results available.'}\n\n"
        prompt += "Answer:"

        answer = generate_ai_response(prompt)

        if user_id not in chat_histories:
            chat_histories[user_id] = []
        chat_histories[user_id].extend([f"User: {question}", f"Twin: {answer}"])
        return {"answer": answer}
    except Exception as e:
        return {"answer": f"AI Error: {str(e)}"}


@app.get("/ask_stream")
async def ask_twin_stream(user_id: str, question: str, mood: str = "Natural"):
    """
    Streaming version of /ask — returns Server-Sent Events (text/event-stream).
    Each chunk is sent as: data: <token>\n\n
    Final chunk is:         data: [DONE]\n\n
    """
    results = knowledge_col.query(
        query_texts=[question], n_results=3, where={"user": user_id}
    )
    context = "\n".join(results["documents"][0]) if results["documents"] else ""
    history_text = "\n".join(chat_histories.get(user_id, [])[-6:])
    prompt = (
        f"You are the AI Digital Twin of {user_id}. Personality Mode: {mood}\n"
        f"Context:\n{context}\n\n"
        f"Conversation History:\n{history_text}\n\n"
        f"User Question:\n{question}\n\n"
    )
    if _looks_like_realtime_request(question):
        search_block = web_search_snippets(question, max_results=4)
        prompt += f"WEB RESULTS:\n{search_block if search_block else 'No web results available.'}\n\n"
    prompt += "Answer:"

    import asyncio

    async def event_generator():
        full_answer = ""
        try:
            # Try Gemini streaming first; fall back to non-streaming via fallback chain
            try:
                genai.configure(api_key=GEMINI_KEY)
                chat_model = genai.GenerativeModel(MODEL_NAME)
                response = chat_model.generate_content(prompt, stream=True)
                for chunk in response:
                    chunk_text = getattr(chunk, "text", "") or ""
                    if chunk_text:
                        full_answer += chunk_text
                        # Cinematic: split chunk into words with intentional delays
                        for word in chunk_text.split(" "):
                            if word:
                                safe = (word + " ").replace("\n", "\\n")
                                yield f"data: {safe}\n\n"
                                await asyncio.sleep(0.025) # Smooth speed
                            else:
                                yield "data:  \n\n"
                                await asyncio.sleep(0.01)
            except Exception:
                # Fallback: get full answer from fallback chain, stream word-by-word
                full_answer = generate_ai_response(prompt)
                for word in full_answer.split(" "):
                    safe = (word + " ").replace("\n", "\\n")
                    yield f"data: {safe}\n\n"
                    await asyncio.sleep(0.03) # Slightly slower for fallbacks
        except Exception as e:
            yield f"data: AI Error: {str(e)}\n\n"
        finally:
            if full_answer:
                if user_id not in chat_histories:
                    chat_histories[user_id] = []
                chat_histories[user_id].extend([f"User: {question}", f"Twin: {full_answer}"])
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


# --- STYLE MIRROR: VISUAL FASHION GRADING ---
@app.post("/style_mirror")
async def style_mirror(
    user_id: str,
    mood: str = "Natural",
    occasion: str = "casual",
    files: List[UploadFile] = File(...),
):
    style_results = knowledge_col.query(
        query_texts=[
            "fashion style preference clothing outfit colour wardrobe",
            "favourite colors brands clothing style",
        ],
        n_results=8,
        where={"user": user_id},
    )
    style_context = (
        "\n".join(style_results["documents"][0])
        if style_results["documents"] and style_results["documents"][0]
        else "No personal style preferences found in memory."
    )
    image_parts = []
    for f in files:
        image_data = await f.read()
        image_parts.append({"mime_type": f.content_type, "data": image_data})

    prompt = (
        f"You are the AI Digital Twin and personal fashion stylist of {user_id}. "
        f"Personality Mode: {mood}\n\n"
        f"PERSONAL STYLE PROFILE (from memory):\n{style_context}\n\n"
        f"OCCASION: {occasion}\n\n"
        "TASK: Analyse the outfit in the uploaded photo(s) and act as a brutally honest yet "
        "encouraging personal stylist who knows the user intimately.\n\n"
        "Your response MUST follow this exact structure:\n\n"
        "## 👗 Style Mirror Report\n\n"
        "**Overall Score: X/10**  ← give a score out of 10\n\n"
        "**Verdict:** One punchy sentence (e.g. 'Classic you — clean lines, solid palette.')\n\n"
        "### ✅ What's Working\n"
        "- List 2–3 specific things done well, referencing their personal style profile where possible.\n\n"
        "### ⚠️ What Could Be Better\n"
        "- List 1–3 honest, constructive critiques tied to the occasion and their known preferences.\n\n"
        "### 💡 Stylist Tips\n"
        "- Give 2–3 actionable suggestions (accessories, swaps, colour tweaks) that align with their style.\n\n"
        "### 🔁 Style Match\n"
        "- Explain how well this outfit matches their personal style profile (high / medium / low match and why).\n\n"
        "Be specific — mention actual colours, garment types, fits you can see in the photo. "
        "If no style profile exists, base the score purely on general fashion principles for the occasion."
    )
    try:
        # Vision: Gemini preferred (image support), fallback to text-only
        try:
            genai.configure(api_key=GEMINI_KEY)
            vision_model = genai.GenerativeModel(MODEL_NAME)
            response = vision_model.generate_content([prompt] + image_parts)
            answer = response.text
        except Exception:
            answer = generate_ai_response(prompt)  # text-only fallback
        if user_id not in chat_histories:
            chat_histories[user_id] = []
        chat_histories[user_id].extend(
            [f"User (Style Mirror - {occasion}): [outfit photo]", f"Twin: {answer}"]
        )
        return {"answer": answer}
    except Exception as e:
        return {"answer": f"Style Mirror Error: {str(e)}"}


# ─────────────────────────────────────────────
# SHADOW DEVELOPER — ENHANCED /debug_code
# ─────────────────────────────────────────────

class DebugCodeRequest(BaseModel):
    user_id: str
    code: str
    language: str = "python"
    mode: str = "Find & Fix Bugs"   # Find & Fix Bugs | Code Review | Optimize Code | Explain This Code
    mood: str = "Natural"
    extra_context: str = ""
    run_code: bool = False           # execute original code before fixing?
    run_fixed: bool = False          # execute the fixed code after AI response?
    repo_path: str = ""              # optional: local repo path to include context


@app.post("/debug_code")
async def debug_code(req: DebugCodeRequest):
    """
    Enhanced Shadow Developer endpoint with:
    - Syntax error detection before Gemini
    - Optional code execution (original + fixed)
    - Diff generation between original and fixed
    - Optional git repo file context
    """
    lang = req.language.lower()
    response_payload: dict = {
        "syntax_check": {},
        "execution_original": {},
        "ai_analysis": "",
        "fixed_code": "",
        "diff": "",
        "execution_fixed": {},
        "repo_context_used": False,
        "repo_files_read": 0,
    }

    # ── 1. SYNTAX CHECK ──────────────────────────────────────────
    syntax = detect_syntax_errors(req.code, lang)
    response_payload["syntax_check"] = syntax

    # ── 2. OPTIONAL: RUN ORIGINAL CODE ───────────────────────────
    if req.run_code:
        exec_result = execute_code(req.code, lang)
        response_payload["execution_original"] = exec_result

    # ── 3. OPTIONAL: PULL REPO CONTEXT ───────────────────────────
    repo_context_block = ""
    if req.repo_path.strip():
        repo_data = read_git_repo_files(req.repo_path.strip())
        if repo_data["files"]:
            snippets = []
            for rel_path, content in list(repo_data["files"].items())[:10]:
                snippets.append(f"### {rel_path}\n```\n{content[:1500]}\n```")
            repo_context_block = (
                f"\n\nREPO CONTEXT ({repo_data['total_files_found']} files"
                f"{', truncated' if repo_data['truncated'] else ''}):\n"
                + "\n\n".join(snippets)
            )
            response_payload["repo_context_used"] = True
            response_payload["repo_files_read"] = repo_data["total_files_found"]
        if repo_data["errors"]:
            response_payload["repo_errors"] = repo_data["errors"]

    # ── 4. PULL USER CODING STYLE FROM MEMORY ───────────────────
    style_results = knowledge_col.query(
        query_texts=["coding style programming patterns habits"],
        n_results=6,
        where={"user": req.user_id},
    )
    style_context = (
        "\n".join(style_results["documents"][0])
        if style_results["documents"] and style_results["documents"][0]
        else "No personal coding style recorded."
    )

    # ── 5. BUILD SYNTAX ERROR BLOCK FOR PROMPT ──────────────────
    syntax_block = ""
    if syntax["errors"]:
        syntax_block += "\n\nPRE-ANALYSIS SYNTAX ERRORS DETECTED:\n"
        syntax_block += "\n".join(f"  ❌ {e}" for e in syntax["errors"])
    if syntax["warnings"]:
        syntax_block += "\n\nPRE-ANALYSIS WARNINGS:\n"
        syntax_block += "\n".join(f"  ⚠️  {w}" for w in syntax["warnings"])

    # ── 6. BUILD EXECUTION CONTEXT FOR PROMPT ───────────────────
    exec_block = ""
    if req.run_code and response_payload["execution_original"].get("ran"):
        eo = response_payload["execution_original"]
        exec_block = (
            f"\n\nORIGINAL CODE EXECUTION RESULT:\n"
            f"  Exit code: {eo['exit_code']}\n"
            f"  STDOUT:\n{eo['stdout'] or '(empty)'}\n"
            f"  STDERR:\n{eo['stderr'] or '(none)'}\n"
        )

    # ── 7. CALL AI (with fallback chain) ─────────────────────────
    prompt = (
        f"You are the AI Digital Twin and Shadow Developer of {req.user_id}. "
        f"Personality Mode: {req.mood}\n\n"
        f"PERSONAL CODING STYLE PROFILE:\n{style_context}\n"
        f"{syntax_block}"
        f"{exec_block}"
        f"{repo_context_block}\n\n"
        f"TASK: {req.mode}\n"
        f"LANGUAGE: {req.language}\n"
        f"EXTRA CONTEXT: {req.extra_context or 'None provided.'}\n\n"
        f"CODE TO ANALYSE:\n```{lang}\n{req.code}\n```\n\n"
        "INSTRUCTIONS:\n"
        "1. Identify the user's coding style from the style profile above.\n"
        "2. Perform the requested task.\n"
        "3. If fixing bugs or optimising, output the COMPLETE fixed code inside a single fenced "
        "   code block (``` ... ```) — no partial snippets.\n"
        "4. After the code block, provide a clear explanation of every change made.\n"
        "5. Match the user's exact style: variable naming, indentation, error-handling patterns.\n"
        "6. If syntax errors were detected above, address each one explicitly.\n"
        "7. Be specific — reference exact line numbers where relevant.\n"
    )

    try:
        ai_response = generate_ai_response(prompt)
        response_payload["ai_analysis"] = ai_response

        # ── 8. EXTRACT FIXED CODE + GENERATE DIFF ────────────────
        fixed_code = extract_code_block(ai_response)

        # Only treat it as real fixed code if it looks different from the original
        if fixed_code and fixed_code.strip() != req.code.strip():
            response_payload["fixed_code"] = fixed_code
            response_payload["diff"] = generate_diff(
                req.code,
                fixed_code,
                filename=f"code{LANGUAGE_EXTENSIONS.get(lang, '.txt')}",
            )
        else:
            response_payload["fixed_code"] = ""
            response_payload["diff"] = "No changes — code appears identical or AI did not produce a fix."

        # ── 9. OPTIONAL: RUN FIXED CODE ───────────────────────────
        if req.run_fixed and fixed_code and fixed_code.strip() != req.code.strip():
            exec_fixed = execute_code(fixed_code, lang)
            response_payload["execution_fixed"] = exec_fixed

        # ── 10. LOG TO CHAT HISTORY ───────────────────────────────
        if req.user_id not in chat_histories:
            chat_histories[req.user_id] = []
        chat_histories[req.user_id].extend(
            [
                f"User (Shadow Dev [{req.mode}|{req.language}]): [code snippet]",
                f"Twin: {ai_response[:300]}...",
            ]
        )

        return response_payload

    except Exception as e:
        response_payload["ai_analysis"] = f"AI Error: {str(e)}"
        return response_payload


# ─────────────────────────────────────────────
# REPO FILES — GIT REPO EXPLORER ENDPOINT
# ─────────────────────────────────────────────

@app.get("/repo_files")
async def get_repo_files(
    repo_path: str,
    extensions: Optional[str] = None,
    max_files: int = 25,
):
    """
    Browse a local git repo or clone a GitHub URL and return file contents.
    Query params:
      - repo_path: local path OR a https://github.com/... URL
      - extensions: comma-separated list e.g. '.py,.js,.ts'  (optional)
      - max_files: max number of files to return (default 25)
    """
    ext_list: Optional[List[str]] = None
    if extensions:
        ext_list = [e.strip() for e in extensions.split(",") if e.strip()]

    # ── Handle GitHub URLs ────────────────────────────────────────────────────
    tmp_dir = None
    actual_path = repo_path.strip()

    is_github_url = actual_path.startswith("https://github.com/") or actual_path.startswith("http://github.com/")

    if is_github_url:
        # Ensure URL ends without trailing slash and has no extra fragments
        clone_url = actual_path.rstrip("/")
        if not clone_url.endswith(".git"):
            clone_url = clone_url + ".git"

        tmp_dir = tempfile.mkdtemp(prefix="adt_repo_")
        try:
            result = subprocess.run(
                ["git", "clone", "--depth=1", clone_url, tmp_dir],
                capture_output=True,
                text=True,
                timeout=60,
            )
            if result.returncode != 0:
                # Clean up temp dir
                import shutil
                shutil.rmtree(tmp_dir, ignore_errors=True)
                err_msg = result.stderr.strip() or "git clone failed"
                raise HTTPException(
                    status_code=400,
                    detail=f"Could not clone GitHub repo: {err_msg}",
                )
            actual_path = tmp_dir
        except subprocess.TimeoutExpired:
            import shutil
            shutil.rmtree(tmp_dir, ignore_errors=True)
            raise HTTPException(status_code=408, detail="git clone timed out (60s). Try a smaller repo.")
        except FileNotFoundError:
            import shutil
            shutil.rmtree(tmp_dir, ignore_errors=True)
            raise HTTPException(
                status_code=500,
                detail="'git' command not found on server. Please install git or provide a local path.",
            )

    try:
        data = read_git_repo_files(actual_path, extensions=ext_list, max_files=max_files)
    finally:
        # Clean up cloned temp dir if we created one
        if tmp_dir:
            import shutil
            shutil.rmtree(tmp_dir, ignore_errors=True)

    if data["errors"] and not data["files"]:
        raise HTTPException(status_code=404, detail="; ".join(data["errors"]))

    return {
        "files": data["files"],
        "errors": data["errors"],
        "truncated": data["truncated"],
        "is_git_repo": data.get("is_git_repo", False),
        "total_files": data.get("total_files_found", len(data["files"])),
        "source": "github" if is_github_url else "local",
    }


# ─────────────────────────────────────────────
# TWIN NEWSROOM — PERSONALIZED MORNING BRIEFING
# ─────────────────────────────────────────────

class NewsroomRequest(BaseModel):
    user_id: str
    mood: str = "Natural"                      # Professional | Natural | Sarcastic
    locations: List[str] = ["Delhi", "India"]  # user-defined locations
    extra_topics: List[str] = []               # any extra topics user wants


def _build_news_search_queries(
    tech_stack: List[str],
    locations: List[str],
    extra_topics: List[str],
) -> List[str]:
    """Build a diverse set of search queries from user context."""
    queries = []

    # If the user provided extra topics, they want the briefing to stay focused on them.
    if extra_topics:
        for topic in extra_topics:
            queries.append(f"{topic} news today")
        for loc in locations:
            queries.append(f"{loc} latest news today")
        return queries

    # Tech stack news
    for tech in tech_stack[:4]:
        queries.append(f"{tech} latest news 2025")

    # Location news
    for loc in locations[:2]:
        queries.append(f"{loc} technology news today")
        queries.append(f"{loc} latest news today")

    # Extra topics
    for topic in extra_topics[:3]:
        queries.append(f"{topic} news today")

    # General tech pulse
    queries.append("AI developer tools news today")

    return queries


def _fetch_multi_search(queries: List[str], results_per_query: int = 4) -> List[dict]:
    """Run multiple DuckDuckGo searches and deduplicate by URL."""
    try:
        try:
            from ddgs import DDGS  # type: ignore  # new package name (pip install ddgs)
        except ImportError:
            from duckduckgo_search import DDGS  # type: ignore  # old package name fallback
    except Exception:
        return []

    seen_urls: set = set()
    all_results: List[dict] = []

    try:
        with DDGS() as ddgs:
            for query in queries:
                try:
                    for r in ddgs.text(query, max_results=results_per_query):
                        href = (r.get("href") or r.get("link") or "").strip()
                        if href and href not in seen_urls:
                            seen_urls.add(href)
                            all_results.append({
                                "title": (r.get("title") or "").strip(),
                                "url": href,
                                "body": (r.get("body") or "").strip()[:300],
                                "query": query,
                            })
                except Exception:
                    continue
    except Exception:
        return []

    return all_results


@app.post("/morning_briefing")
async def morning_briefing(req: NewsroomRequest):
    """
    Twin Newsroom: fetches live news relevant to the user's tech stack,
    location, and interests — then presents it as a personalised briefing
    written in the user's chosen personality/mood.
    """
    # ── 1. PULL USER INTERESTS FROM MEMORY ───────────────────────
    interest_results = knowledge_col.query(
        query_texts=[
            "tech stack programming languages frameworks tools",
            "interests hobbies work projects",
            "location city workplace",
        ],
        n_results=10,
        where={"user": req.user_id},
    )
    memory_context = (
        "\n".join(interest_results["documents"][0])
        if interest_results["documents"] and interest_results["documents"][0]
        else ""
    )

    # ── 2. EXTRACT TECH STACK FROM MEMORY VIA QUICK LLM CALL ─────
    tech_stack: List[str] = []
    if not req.extra_topics: # Only extract from memory if no specific topics provided
        if memory_context:
            try:
                extract_prompt = (
                    "From the following personal memory, extract a list of up to 6 specific "
                    "technologies, frameworks, or programming languages the person uses. "
                    "Return ONLY a comma-separated list, nothing else.\n\n"
                    f"MEMORY:\n{memory_context}"
                )
                raw_tech = llm.invoke(extract_prompt).strip()
                tech_stack = [t.strip() for t in raw_tech.split(",") if t.strip()][:6]
            except Exception:
                pass

    # Fall back to sensible defaults ONLY if memory is empty AND no extra topics provided
    if not tech_stack and not req.extra_topics:
        tech_stack = ["Python", "FastAPI", "AI", "Machine Learning"]

    # ── 3. FETCH LIVE NEWS ────────────────────────────────────────
    queries = _build_news_search_queries(tech_stack, req.locations, req.extra_topics)
    raw_articles = _fetch_multi_search(queries, results_per_query=4)

    if not raw_articles:
        return {
            "briefing": (
                "⚠️ Could not fetch live news right now. "
                "Make sure `duckduckgo_search` is installed (`pip install duckduckgo-search`) "
                "and you have an internet connection."
            ),
            "articles_found": 0,
            "tech_stack_detected": tech_stack,
        }

    # ── 4. FORMAT RAW ARTICLES FOR PROMPT ────────────────────────
    article_lines = []
    for i, art in enumerate(raw_articles[:20], 1):
        article_lines.append(
            f"{i}. [{art['query']}] {art['title']}\n   {art['url']}\n   {art['body']}"
        )
    articles_block = "\n\n".join(article_lines)

    # ── 5. MOOD-SPECIFIC PERSONA INSTRUCTIONS ────────────────────
    mood_instructions = {
        "Professional": (
            "Write in a crisp, executive-briefing style. Use confident, direct language. "
            "Group stories by category (Tech, Local, Industry). "
            "Conclude with one sharp 'Key Takeaway for Today'."
        ),
        "Sarcastic": (
            "Write like you're a snarky, self-aware version of the user reading the news to themselves. "
            "Add dry wit, light sarcasm, and the occasional eye-roll emoji. "
            "Still cover all key stories but make it entertaining. "
            "End with a sarcastic 'Deep Thought of the Morning'."
        ),
        "Natural": (
            "Write in a warm, conversational tone — like a smart friend catching you up over coffee. "
            "Be engaging but concise. End with a friendly 'One Thing to Watch Today'."
        ),
    }
    persona = mood_instructions.get(req.mood, mood_instructions["Natural"])

    # ── 6. BUILD GEMINI PROMPT ────────────────────────────────────
    from datetime import datetime
    today = datetime.now().strftime("%A, %B %d %Y")

    prompt = (
        f"You are the AI Digital Twin of {req.user_id}. Today is {today}.\n"
        f"Personality Mode: {req.mood}\n\n"
        f"USER PROFILE:\n"
        f"  Tech Stack: {', '.join(tech_stack)}\n"
        f"  Locations of interest: {', '.join(req.locations)}\n"
        f"  Additional topics: {', '.join(req.extra_topics) if req.extra_topics else 'None'}\n\n"
        f"PERSONA INSTRUCTION: {persona}\n\n"
        f"RAW NEWS ARTICLES (fetched live):\n{articles_block}\n\n"
        "TASK: Write a personalised Morning Briefing for the user based on the articles above.\n\n"
        "FORMAT YOUR RESPONSE EXACTLY LIKE THIS:\n\n"
        "## 📰 Good Morning — Your Twin Newsroom\n"
        f"*{today}*\n\n"
        "### 💻 Tech & Dev Updates\n"
        "- Cover 3–4 most relevant tech/dev stories from the articles. "
        "Include the source URL inline as a markdown link.\n\n"
        "### 🌍 Local & Regional News\n"
        "- Cover 2–3 local/regional stories relevant to their location(s).\n\n"
        "### 🔮 What's Trending in Your World\n"
        "- 2 stories that intersect their interests/stack with current events.\n\n"
        "### ☕ [Closing Section — title depends on mood]\n"
        "- Your mood-appropriate closing insight (Key Takeaway / Deep Thought / One Thing to Watch).\n\n"
        "RULES:\n"
        "- Only use stories from the provided articles — do not invent news.\n"
        "- Every story must include a clickable markdown URL link.\n"
        "- Keep the whole briefing under 600 words.\n"
        "- Write it AS the user's twin — speak directly to them in second person.\n"
        "- Make it feel personal by referencing their specific tech stack and location.\n"
    )

    try:
        briefing = generate_ai_response(prompt)

        # ── 7. LOG TO CHAT HISTORY ────────────────────────────────
        if req.user_id not in chat_histories:
            chat_histories[req.user_id] = []
        chat_histories[req.user_id].extend(
            [
                f"User: Morning briefing requested ({req.mood} mode)",
                f"Twin (Newsroom): {briefing[:300]}...",
            ]
        )

        return {
            "briefing": briefing,
            "articles_found": len(raw_articles),
            "tech_stack_detected": tech_stack,
            "queries_used": queries,
        }

    except Exception as e:
        return {
            "briefing": f"Newsroom Error: {str(e)}",
            "articles_found": len(raw_articles),
            "tech_stack_detected": tech_stack,
        }


# NOTE: /repo_files endpoint is defined earlier with full GitHub URL support.


# ─── PERSISTENT CHAT SESSIONS ──────────────────────────────────────────────

chat_sessions_col = db["chat_sessions"]

@app.post("/chat/save")
async def save_chat_session(data: dict):
    """Save or update a chat session for a user."""
    from datetime import datetime
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


@app.get("/chat/sessions")
async def get_chat_sessions(user_id: str):
    """List all chat sessions for a user, newest first — metadata only (no messages)."""
    cursor = chat_sessions_col.find(
        {"user_id": user_id},
        {"_id": 0, "session_id": 1, "title": 1, "updated_at": 1, "message_count": 1}
    ).sort("updated_at", -1).limit(50)
    sessions = await cursor.to_list(length=50)
    return {"sessions": sessions}


@app.get("/chat/load")
async def load_chat_session(user_id: str, session_id: str):
    """Load a specific chat session."""
    doc = await chat_sessions_col.find_one(
        {"user_id": user_id, "session_id": session_id},
        {"_id": 0}
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Session not found")
    return doc


@app.delete("/chat/session/{session_id}")
async def delete_chat_session(session_id: str, user_id: str):
    """Delete a chat session."""
    await chat_sessions_col.delete_one({"user_id": user_id, "session_id": session_id})
    return {"status": "deleted"}


# ─── GOALS & HABITS ────────────────────────────────────────────────────────
goals_col = db["goals"]

@app.post("/goals/add")
async def add_goal(data: dict):
    from datetime import datetime
    user_id  = data.get("user_id")
    goal     = data.get("goal", "").strip()
    category = data.get("category", "General")
    if not user_id or not goal:
        raise HTTPException(status_code=400, detail="user_id and goal required")
    doc = {
        "user_id": user_id, "goal": goal, "category": category,
        "progress": 0, "completed": False,
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
        "notes": []
    }
    result = await goals_col.insert_one(doc)
    return {"status": "added", "id": str(result.inserted_id)}

@app.get("/goals")
async def get_goals(user_id: str):
    from bson import ObjectId
    cursor = goals_col.find({"user_id": user_id}).sort("created_at", -1)
    goals  = await cursor.to_list(length=100)
    for g in goals:
        g["_id"] = str(g["_id"])
    return {"goals": goals}

@app.post("/goals/update")
async def update_goal(data: dict):
    from datetime import datetime
    from bson import ObjectId
    goal_id  = data.get("goal_id")
    progress = data.get("progress")
    completed = data.get("completed")
    note     = data.get("note", "")
    update   = {"updated_at": datetime.utcnow().isoformat()}
    if progress is not None:
        update["progress"] = int(progress)
        if int(progress) >= 100:
            update["completed"] = True
    if completed is not None:
        update["completed"] = completed
    push = {}
    if note:
        push["notes"] = {"text": note, "at": datetime.utcnow().isoformat()}
    op = {"$set": update}
    if push:
        op["$push"] = push
    await goals_col.update_one({"_id": ObjectId(goal_id)}, op)
    return {"status": "updated"}

@app.delete("/goals/{goal_id}")
async def delete_goal(goal_id: str, user_id: str):
    from bson import ObjectId
    await goals_col.delete_one({"_id": ObjectId(goal_id), "user_id": user_id})
    return {"status": "deleted"}


# ─── CALENDAR ──────────────────────────────────────────────────────────────
calendar_col = db["calendar_events"]

@app.post("/calendar/add")
async def add_event(data: dict):
    from datetime import datetime
    user_id = data.get("user_id")
    title   = data.get("title", "").strip()
    date    = data.get("date", "")
    time    = data.get("time", "")
    desc    = data.get("description", "")
    color   = data.get("color", "#38bdf8")
    if not user_id or not title or not date:
        raise HTTPException(status_code=400, detail="user_id, title and date required")
    doc = {
        "user_id": user_id, "title": title, "date": date,
        "time": time, "description": desc, "color": color,
        "created_at": datetime.utcnow().isoformat(),
        "google_event_id": None,
    }
    result = await calendar_col.insert_one(doc)

    # ── Try to add to Google Calendar ────────────────────────────────────────
    google_event_id = None
    google_error    = None
    try:
        google_event_id, google_error = _add_to_google_calendar(title, date, time, desc, user_id)
        print(f"[GCal] Sync result: event_id={google_event_id}, error={google_error}")
    except Exception as ge:
        google_error = str(ge)
        print(f"[GCal] Exception during sync: {ge}")

    if google_event_id:
        await calendar_col.update_one(
            {"_id": result.inserted_id},
            {"$set": {"google_event_id": google_event_id}}
        )

    return {
        "status": "added",
        "id": str(result.inserted_id),
        "google_synced": bool(google_event_id),
        "google_event_id": google_event_id,
        "google_error": google_error,
    }


def _add_to_google_calendar(title: str, date: str, time_str: str,
                             desc: str, user_email: str):
    """
    Push event to Google Calendar using a service-account credentials file
    OR OAuth2 token file.  Returns (event_id, None) on success or (None, error_str).

    Setup (one-time):
      pip install google-api-python-client google-auth google-auth-httplib2

    Option A — OAuth2 (recommended for personal use):
      1. Go to https://console.cloud.google.com → create project
      2. Enable Google Calendar API
      3. Create OAuth 2.0 credentials (Desktop app) → download as
         backend/google_credentials.json
      4. First run: python backend/google_auth_setup.py   (creates token.json)

    Option B — Service Account:
      1. Create service account → download JSON → save as backend/service_account.json
      2. Share your Google Calendar with the service account email

    GOOGLE_CALENDAR_ID in .env (optional, defaults to 'primary'):
      GOOGLE_CALENDAR_ID=primary   OR   your-calendar-id@group.calendar.google.com
    """
    import os as _os
    from datetime import datetime as _dt, timedelta

    CREDS_FILE   = _os.path.join(_os.path.dirname(__file__), "google_credentials.json")
    TOKEN_FILE   = _os.path.join(_os.path.dirname(__file__), "token.json")
    SA_FILE      = _os.path.join(_os.path.dirname(__file__), "service_account.json")
    CALENDAR_ID  = _os.getenv("GOOGLE_CALENDAR_ID", "primary")

    creds = None

    # ── Try OAuth2 token first ─────────────────────────────────────────────
    if _os.path.exists(TOKEN_FILE):
        try:
            from google.oauth2.credentials import Credentials
            from google.auth.transport.requests import Request
            SCOPES = ["https://www.googleapis.com/auth/calendar"]
            creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
            if creds.expired and creds.refresh_token:
                creds.refresh(Request())
                with open(TOKEN_FILE, "w") as tf:
                    tf.write(creds.to_json())
        except Exception as e:
            creds = None
            print(f"[GCal] OAuth token error: {e}")

    # ── Try Service Account ────────────────────────────────────────────────
    if creds is None and _os.path.exists(SA_FILE):
        try:
            from google.oauth2 import service_account
            SCOPES = ["https://www.googleapis.com/auth/calendar"]
            creds = service_account.Credentials.from_service_account_file(
                SA_FILE, scopes=SCOPES)
        except Exception as e:
            creds = None
            print(f"[GCal] Service account error: {e}")

    if creds is None:
        return None, "Google Calendar not configured. Add token.json or service_account.json to backend/."

    # ── Build event payload ────────────────────────────────────────────────
    try:
        from googleapiclient.discovery import build
        service = build("calendar", "v3", credentials=creds)

        # Parse date + time into RFC3339
        if time_str and time_str != "00:00:00":
            try:
                start_dt = _dt.strptime(f"{date} {time_str}", "%Y-%m-%d %H:%M:%S")
            except ValueError:
                start_dt = _dt.strptime(f"{date} {time_str[:5]}", "%Y-%m-%d %H:%M")
            end_dt = start_dt + timedelta(hours=1)
            event_body = {
                "summary":     title,
                "description": desc or "",
                "start": {"dateTime": start_dt.isoformat(), "timeZone": "Asia/Kolkata"},
                "end":   {"dateTime": end_dt.isoformat(),   "timeZone": "Asia/Kolkata"},
            }
        else:
            # All-day event
            event_body = {
                "summary":     title,
                "description": desc or "",
                "start": {"date": date},
                "end":   {"date": date},
            }

        created = service.events().insert(calendarId=CALENDAR_ID, body=event_body).execute()
        print(f"[GCal] ✓ Event created: {created.get('htmlLink')}")
        return created.get("id"), None

    except Exception as e:
        print(f"[GCal] API error: {e}")
        return None, str(e)

@app.get("/calendar/events")
async def get_events(user_id: str, month: str = None):
    cursor = calendar_col.find({"user_id": user_id}).sort("date", 1)
    events = await cursor.to_list(length=500)
    for e in events:
        e["_id"] = str(e["_id"])
    if month:
        events = [e for e in events if e.get("date", "").startswith(month)]
    return {"events": events}

@app.delete("/calendar/event/{event_id}")
async def delete_event(event_id: str, user_id: str):
    from bson import ObjectId
    await calendar_col.delete_one({"_id": ObjectId(event_id), "user_id": user_id})
    return {"status": "deleted"}


# ─── TRANSLATE ─────────────────────────────────────────────────────────────
@app.post("/translate")
async def translate_text(data: dict):
    text        = data.get("text", "")
    target_lang = data.get("target_lang", "English")
    if not text:
        return {"translated": ""}
    prompt = f"""Translate the following text to {target_lang}. 
Return ONLY the translated text, nothing else.

Text: {text}"""
    try:
        result = llm.invoke(prompt)
        return {"translated": result.strip()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))