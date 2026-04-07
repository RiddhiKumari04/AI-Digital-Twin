"""
ai_providers.py — Multi-provider AI fallback chain.
Priority: Gemini → OpenRouter → Groq → Hugging Face → Together AI
"""

import urllib.request as _ur
import json as _j

import google.generativeai as genai  # pyright: ignore[reportMissingImports]
from langchain_core.prompts import PromptTemplate

from config import (
    GEMINI_KEY, OPENROUTER_KEY, GROQ_KEY, HUGGINGFACE_KEY, TOGETHER_KEY,
    OPENROUTER_MODELS, TOGETHER_MODEL, HUGGINGFACE_MODEL, MODEL_NAME,
)


# ── Low-level provider helpers ────────────────────────────────────────────────

def _openrouter_generate(prompt: str, model: str = "openrouter/auto") -> str:
    """Call OpenRouter API with specified model. Raises on error."""
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
            if not text:
                raise RuntimeError("Empty response from Groq")
            return text
    except Exception as e:
        raise RuntimeError(f"Groq error: {e}")


def _together_generate(prompt: str) -> str:
    """Call Together AI API (OpenAI-compatible). Raises on error."""
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


# ── Public API ────────────────────────────────────────────────────────────────

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
    # ── 1. Try Gemini ──────────────────────────────────────────
    try:
        genai.configure(api_key=GEMINI_KEY)
        gem_model = genai.GenerativeModel("gemini-1.5-flash")
        response = gem_model.generate_content(prompt)
        print("[AI] ✓ Gemini responded")
        return response.text
    except Exception as e:
        print(f"[AI] Gemini failed ({e}), trying OpenRouter...")

    # ── 2. Try OpenRouter ───────────────────────────────────────
    try:
        result = _openrouter_generate(prompt, model="openrouter/auto")
        print("[AI] ✓ OpenRouter responded")
        return result
    except Exception as e:
        print(f"[AI] OpenRouter failed ({e}), trying Groq...")

    # ── 3. Try Groq ────────────────────────────────────────────
    try:
        result = _groq_generate(prompt)
        print("[AI] ✓ Groq responded")
        return result
    except Exception as e:
        print(f"[AI] Groq failed ({e}), trying Hugging Face...")

    # ── 4. Try Hugging Face ────────────────────────────────────
    try:
        result = _huggingface_generate(prompt)
        print("[AI] ✓ Hugging Face responded")
        return result
    except Exception as e:
        print(f"[AI] Hugging Face failed ({e}), trying Together AI...")

    # ── 5. Try Together AI ─────────────────────────────────────
    try:
        result = _together_generate(prompt)
        print("[AI] ✓ Together AI responded")
        return result
    except Exception as e:
        print(f"[AI] Together AI also failed ({e})")
        raise RuntimeError("All 5 AI providers are offline or at capacity. Please try again later.")


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
