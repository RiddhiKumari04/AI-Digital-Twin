"""
routes/calendar.py — Calendar & Google Calendar sync endpoints:
  POST   /calendar/add
  GET    /calendar/events
  DELETE /calendar/event/{event_id}
"""

import os
from datetime import datetime, timedelta

from bson import ObjectId
from fastapi import APIRouter, HTTPException

from config import calendar_col

router = APIRouter()


# ── Google Calendar sync helper ───────────────────────────────────────────────

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
    CREDS_FILE  = os.path.join(os.path.dirname(__file__), "..", "google_credentials.json")
    TOKEN_FILE  = os.path.join(os.path.dirname(__file__), "..", "token.json")
    SA_FILE     = os.path.join(os.path.dirname(__file__), "..", "service_account.json")
    CALENDAR_ID = os.getenv("GOOGLE_CALENDAR_ID", "primary")

    creds = None

    # ── Try OAuth2 token first ─────────────────────────────────────────────
    if os.path.exists(TOKEN_FILE):
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
    if creds is None and os.path.exists(SA_FILE):
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

        if time_str and time_str != "00:00:00":
            try:
                start_dt = datetime.strptime(f"{date} {time_str}", "%Y-%m-%d %H:%M:%S")
            except ValueError:
                start_dt = datetime.strptime(f"{date} {time_str[:5]}", "%Y-%m-%d %H:%M")
            end_dt = start_dt + timedelta(hours=1)
            event_body = {
                "summary":     title,
                "description": desc or "",
                "start": {"dateTime": start_dt.isoformat(), "timeZone": "Asia/Kolkata"},
                "end":   {"dateTime": end_dt.isoformat(),   "timeZone": "Asia/Kolkata"},
            }
        else:
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


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/calendar/add")
async def add_event(data: dict):
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


@router.get("/calendar/events")
async def get_events(user_id: str, month: str = None):
    cursor = calendar_col.find({"user_id": user_id}).sort("date", 1)
    events = await cursor.to_list(length=500)
    for e in events:
        e["_id"] = str(e["_id"])
    if month:
        events = [e for e in events if e.get("date", "").startswith(month)]
    return {"events": events}


@router.delete("/calendar/event/{event_id}")
async def delete_event(event_id: str, user_id: str):
    await calendar_col.delete_one({"_id": ObjectId(event_id), "user_id": user_id})
    return {"status": "deleted"}
