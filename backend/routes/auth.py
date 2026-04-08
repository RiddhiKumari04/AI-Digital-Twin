"""
routes/auth.py — Authentication endpoints:
  POST /register
  GET  /login
  POST /forgot_password/send_otp
  POST /forgot_password/verify_otp
  POST /forgot_password/reset
  POST /login_otp/send
  POST /login_otp/verify
  GET  /auth/google/start
  GET  /auth/google/callback
  POST /profile/save_photo
  GET  /profile/get_photo
"""

import hashlib
import random
import time
import urllib.request
import urllib.parse
import json as _json
import traceback
import logging

import httpx
from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import RedirectResponse

from config import (
    users_collection,
    BREVO_API_KEY, BREVO_SENDER_EMAIL, BREVO_SENDER_NAME,
    RESEND_API_KEY, RESEND_FROM_EMAIL,
    SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD,
    GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REDIRECT_URI, STREAMLIT_URL,
)
from models import UserRegister, ResetPasswordRequest

router = APIRouter()

# ── In-memory OTP stores ──────────────────────────────────────────────────────
_otp_store: dict = {}        # forgot-password OTPs
_login_otp_store: dict = {}  # passwordless login OTPs


# ── Password hashing ──────────────────────────────────────────────────────────

def _hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


# ── Email helpers ─────────────────────────────────────────────────────────────

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
        print(f"[EMAIL/Resend] Error sending to {to_email}: {e}")
        traceback.print_exc()
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
        print(f"[EMAIL/SMTP-TLS] Failed to {to_email} ({e2})")
        traceback.print_exc()
        return False


def _send_otp_email(to_email: str, otp: str, purpose: str = "OTP Verification") -> bool:
    """
    Universal OTP sender — tries Brevo → Resend → SMTP in order.
    If none configured, prints to terminal (dev mode).
    """
    # LOGGING: Print the OTP to console so user can see it in Render logs
    print(f"\n[DEBUG/OTP] Target: {to_email} | Purpose: {purpose} | Code: {otp}\n")

    # Try SMTP first (usually more reliable than test-domain Resend)
    if _send_via_smtp(to_email, otp, purpose):
        return True
    
    # Try Brevo
    if _send_via_brevo(to_email, otp, purpose):
        return True
        
    # Try Resend
    if _send_via_resend(to_email, otp, purpose):
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


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/register")
async def register(user: UserRegister):
    existing = await users_collection.find_one({"email": user.email})
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered.")
    doc = user.dict()
    doc["password"] = _hash_password(doc["password"])
    doc["is_first_login"] = True
    await users_collection.insert_one(doc)
    return {"status": "success"}


@router.get("/login")
async def login(email: str, password: str):
    hashed = _hash_password(password)
    user = await users_collection.find_one({"email": email, "password": hashed})
    if not user:
        # Fallback: old accounts stored plain-text — migrate on successful login
        user = await users_collection.find_one({"email": email, "password": password})
        if user:
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


@router.post("/forgot_password/send_otp")
async def forgot_password_send_otp(email: str, background_tasks: BackgroundTasks):
    """Check email exists, generate OTP, send via email."""
    user = await users_collection.find_one({"email": email})
    if not user:
        raise HTTPException(status_code=404, detail="No account found with this email.")
    otp = str(random.randint(100000, 999999))
    _otp_store[email] = {"otp": otp, "expires": time.time() + 600}
    background_tasks.add_task(_send_otp_email, email, otp, "Password Reset")
    return {"status": "otp_sent", "message": f"OTP sent to {email}"}


@router.post("/forgot_password/verify_otp")
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


@router.post("/forgot_password/reset")
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


# ── Profile photo ─────────────────────────────────────────────────────────────

@router.post("/profile/save_photo")
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


@router.get("/profile/get_photo")
async def get_profile_photo(user_id: str):
    user = await users_collection.find_one({"email": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {"pic_b64": user.get("pic_b64")}


# ── OTP-based passwordless login ──────────────────────────────────────────────

@router.post("/login_otp/send")
async def login_otp_send(email: str, background_tasks: BackgroundTasks):
    """Check account exists, send a 6-digit OTP to email for passwordless login."""
    user = await users_collection.find_one({"email": email})
    if not user:
        raise HTTPException(status_code=404, detail="No account found with this email.")
    otp = str(random.randint(100000, 999999))
    _login_otp_store[email] = {"otp": otp, "expires": time.time() + 600}
    background_tasks.add_task(_send_otp_email, email, otp, "Login Verification")
    return {"status": "otp_sent", "message": f"OTP sent to {email}"}


@router.post("/login_otp/verify")
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
    _login_otp_store.pop(email, None)
    user = await users_collection.find_one({"email": email})
    if not user:
        raise HTTPException(status_code=404, detail="Account not found.")

    is_first_login = user.get("is_first_login", False)
    if is_first_login:
        await users_collection.update_one({"email": email}, {"$set": {"is_first_login": False}})

    return {"status": "success", "name": user["name"], "is_first_login": is_first_login}


# ── Google OAuth ──────────────────────────────────────────────────────────────

@router.get("/auth/google/start")
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


@router.get("/auth/google/callback")
async def google_auth_callback(code: str):
    """Handles callback from Google, exchanges code for token, and fetches profile."""
    if not code:
        raise HTTPException(status_code=400, detail="Missing authorization code.")

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

        profile_url = "https://www.googleapis.com/oauth2/v3/userinfo"
        profile_resp = await client.get(profile_url, headers={"Authorization": f"Bearer {access_token}"})
        if profile_resp.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to fetch profile.")
        profile = profile_resp.json()

    email = profile.get("email")
    name  = profile.get("name")

    if not email:
        raise HTTPException(status_code=400, detail="No email provided by Google.")

    user = await users_collection.find_one({"email": email})
    if not user:
        await users_collection.insert_one({
            "email": email,
            "name": name or email,
            "password": _hash_password(f"google_oauth_{random.randint(0, 999999)}")
        })

    final_params = {
        "_act": "google_login",
        "_email": email,
        "_name": name or email
    }
    redirect_url = f"{STREAMLIT_URL}/?{urllib.parse.urlencode(final_params)}"
    return RedirectResponse(url=redirect_url)
