# TwinX — Deployment Guide

This document covers every step needed to go from local dev to a live
production deployment on **Render** (backend) + **Streamlit Cloud** (frontend).

---

## 1. Pre-flight: set up environment variables

Copy `.env.example` to `backend/.env` and fill in every value:

```bash
cp .env.example backend/.env
nano backend/.env     # or open in your editor
```

Minimum required values:

| Variable | Where to get it |
|---|---|
| `MONGO_URI` | MongoDB Atlas → Connect → Drivers |
| `GEMINI_API_KEY` | https://aistudio.google.com/app/apikey |
| `BREVO_API_KEY` + `BREVO_SENDER_EMAIL` | https://app.brevo.com → API Keys |
| `GOOGLE_CLIENT_ID` + `GOOGLE_CLIENT_SECRET` | Google Cloud Console → OAuth 2.0 |
| `JWT_SECRET` | `python -c "import secrets; print(secrets.token_hex(64))"` |

---

## 2. Deploy the backend to Render

1. Push the `backend/` folder to a GitHub repo (or the root of a mono-repo).
2. In Render → **New Web Service** → connect your repo.
3. Set **Root Directory** to `backend` (if using mono-repo).
4. Set **Build Command**: `pip install -r requirements.txt`
5. Set **Start Command**: *(Render reads the Procfile automatically)*
   ```
   gunicorn main:app --workers 2 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:$PORT --timeout 120
   ```
6. Add **Environment Variables** in the Render dashboard — paste every key
   from your `backend/.env`.
7. Important extras:
   - `ALLOWED_ORIGINS` = `https://your-app.streamlit.app`
   - `STREAMLIT_URL`   = `https://your-app.streamlit.app`
   - `GOOGLE_REDIRECT_URI` = `https://your-backend.onrender.com/auth/google/callback`
   - `ENABLE_CODE_EXECUTION` = **leave unset** (disabled by default for security)

> **ChromaDB note**: The free Render tier uses an ephemeral filesystem.
> Your vector data will be lost on every restart unless you either:
> - Add a **persistent disk** (Render paid feature, mount at `/backend/twin_db`), or
> - Set `CHROMA_HOST` / `CHROMA_TOKEN` to use a managed Chroma Cloud instance.

8. Click **Deploy**. Note the URL (e.g. `https://twinx-backend.onrender.com`).

---

## 3. Deploy the frontend to Streamlit Cloud

1. Push the `frontend/` folder to GitHub.
2. Go to https://share.streamlit.io → **New app** → connect repo.
3. Set **Main file path** to `frontend/app.py`.
4. Click **Advanced settings → Secrets** and paste:
   ```toml
   BACKEND_URL = "https://twinx-backend.onrender.com"
   ```
5. Click **Deploy**.

---

## 4. Update Google OAuth redirect URI

In Google Cloud Console → APIs & Services → Credentials → your OAuth client:

- Add `https://twinx-backend.onrender.com/auth/google/callback` to
  **Authorised redirect URIs**.

---

## 5. Security checklist

- [ ] `ALLOWED_ORIGINS` is set to your Streamlit Cloud URL only (not `*`)
- [ ] `ENABLE_CODE_EXECUTION` is **not** set (or set to `false`)
- [ ] `backend/.env` and `backend/token.json` are in `.gitignore`
- [ ] `JWT_SECRET` is at least 64 random characters
- [ ] MongoDB Atlas IP allowlist includes Render's outbound IPs (or `0.0.0.0/0`
  temporarily with a strong password)
- [ ] Test scripts (`test_ai.py`, `test_keys.py`, `google_auth_setup.py`) are
  excluded from the production build (they're in `.gitignore`)

---

## 6. Local development (no changes required)

```bash
# Terminal 1 — backend
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# Terminal 2 — frontend
cd frontend
streamlit run app.py
# BACKEND_URL defaults to http://127.0.0.1:8000 when the env var is not set
```