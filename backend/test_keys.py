import os
import requests
import json
from dotenv import load_dotenv

load_dotenv(override=True)

GEMINI_KEY      = os.getenv("GEMINI_API_KEY")
OPENROUTER_KEY  = os.getenv("OPENROUTER_API_KEY")
GROQ_KEY        = os.getenv("GROQ_API_KEY")
HUGGINGFACE_KEY = os.getenv("HUGGINGFACE_API_KEY")
TOGETHER_KEY    = os.getenv("TOGETHER_API_KEY")

PROMPT = "Hi, say only 'OK' if you can read this."

def test_gemini():
    try:
        import google.generativeai as genai
        genai.configure(api_key=GEMINI_KEY)
        model = genai.GenerativeModel("gemini-flash-latest")
        res = model.generate_content(PROMPT)
        return "✓ Working" if res.text.strip() else "✗ Empty response"
    except Exception as e:
        return f"✗ Error: {e}"

def test_openrouter():
    try:
        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {"Authorization": f"Bearer {OPENROUTER_KEY}", "Content-Type": "application/json"}
        payload = {"model": "openrouter/auto", "messages": [{"role": "user", "content": PROMPT}]}
        resp = requests.post(url, headers=headers, json=payload, timeout=10)
        if resp.status_code == 200:
            return "✓ Working"
        return f"✗ Error {resp.status_code}: {resp.text[:100]}"
    except Exception as e:
        return f"✗ Error: {e}"

def test_groq():
    try:
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {"Authorization": f"Bearer {GROQ_KEY}", "Content-Type": "application/json"}
        payload = {"model": "llama-3.1-8b-instant", "messages": [{"role": "user", "content": PROMPT}]}
        resp = requests.post(url, headers=headers, json=payload, timeout=10)
        if resp.status_code == 200:
            return "✓ Working"
        return f"✗ Error {resp.status_code}: {resp.text[:100]}"
    except Exception as e:
        return f"✗ Error: {e}"

def test_huggingface():
    try:
        url = "https://api-inference.huggingface.co/models/mistralai/Mistral-7B-Instruct-v0.3/v1/chat/completions"
        headers = {"Authorization": f"Bearer {HUGGINGFACE_KEY}", "Content-Type": "application/json"}
        payload = {"messages": [{"role": "user", "content": PROMPT}], "max_tokens": 10}
        resp = requests.post(url, headers=headers, json=payload, timeout=10)
        if resp.status_code == 200:
            return "✓ Working"
        return f"✗ Error {resp.status_code}: {resp.text[:100]}"
    except Exception as e:
        return f"✗ Error: {e}"

def test_together():
    try:
        url = "https://api.together.xyz/v1/chat/completions"
        headers = {"Authorization": f"Bearer {TOGETHER_KEY}", "Content-Type": "application/json"}
        payload = {"model": "meta-llama/Llama-3-8b-chat-hf", "messages": [{"role": "user", "content": PROMPT}]}
        resp = requests.post(url, headers=headers, json=payload, timeout=10)
        if resp.status_code == 200:
            return "✓ Working"
        return f"✗ Error {resp.status_code}: {resp.text[:100]}"
    except Exception as e:
        return f"✗ Error: {e}"

if __name__ == "__main__":
    print(f"Testing Gemini: {test_gemini()}")
    print(f"Testing OpenRouter: {test_openrouter()}")
    print(f"Testing Groq: {test_groq()}")
    print(f"Testing Hugging Face: {test_huggingface()}")
    print(f"Testing Together AI: {test_together()}")
