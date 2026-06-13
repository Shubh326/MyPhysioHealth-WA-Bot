"""
Google Calendar integration for MyphysioHealth bot.

- Uses a service account (gcal-credentials.json) to create events on a shared
  clinic calendar (GOOGLE_CALENDAR_ID).
- Doctor is added as an attendee (DOCTOR_EMAIL).
- All failures are caught so a Calendar outage NEVER blocks a WhatsApp booking.

Setup checklist (do once):
  1. Enable Google Calendar API in GCP for the project.
  2. Create a service account, download JSON, save as gcal-credentials.json.
  3. Create a Google Calendar (e.g. "MyphysioHealth Bookings") in the clinic
     Gmail account.
  4. Share that calendar with the service account email
     (Make changes to events).
  5. Copy the Calendar ID from calendar Settings -> "Integrate calendar"
     -> paste into .env GOOGLE_CALENDAR_ID.
  6. Optional: share the calendar with the doctor's Gmail so they see all
     bookings in their own Google Calendar view.
"""

import json
import os
import uuid
from datetime import datetime, timedelta

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from config import CLINIC

ONLINE_SERVICE_NAME = "Online Physiotherapy Consultation"

SCOPES = ["https://www.googleapis.com/auth/calendar"]

CREDENTIALS_FILE = os.getenv("GOOGLE_CREDENTIALS_FILE", "gcal-credentials.json")
CALENDAR_ID = os.getenv("GOOGLE_CALENDAR_ID", "")
DOCTOR_EMAIL = os.getenv("DOCTOR_EMAIL", "")
TIMEZONE = os.getenv("CLINIC_TIMEZONE", "Asia/Kolkata")
# Optional permanent Meet link for online consultations. Personal Gmail accounts
# can't auto-create Meet links via API, so the doctor uses a personal meeting
# room URL (e.g. https://meet.google.com/abc-defg-hij) shared in .env.
FALLBACK_MEET_LINK = os.getenv("CLINIC_MEET_LINK", "")

# Default event length in minutes (matches our 30-min slot config)
EVENT_DURATION_MIN = 30


def _get_service():
    """Build a Google Calendar API client. Returns None if not configured.

    Reads credentials from either GOOGLE_CREDENTIALS_JSON env var (paste raw
    JSON) or GOOGLE_CREDENTIALS_FILE on disk. JSON env var wins if both set.
    """
    if not CALENDAR_ID:
        return None
    creds = None
    creds_json = os.getenv("GOOGLE_CREDENTIALS_JSON", "").strip()
    if creds_json:
        info = json.loads(creds_json)
        creds = service_account.Credentials.from_service_account_info(
            info, scopes=SCOPES
        )
    elif os.path.exists(CREDENTIALS_FILE):
        creds = service_account.Credentials.from_service_account_file(
            CREDENTIALS_FILE, scopes=SCOPES
        )
    if creds is None:
        return None
    return build("calendar", "v3", credentials=creds, cache_discovery=False)


def create_event(booking, patient_phone=""):
    """
    Create a Calendar event for a confirmed booking.

    booking dict keys: name, service, date (YYYY-MM-DD), time (HH:MM)

    Returns a dict { "event_link": str, "meet_link": str|None } on success,
    or None on any failure.
    """
    try:
        service = _get_service()
        if service is None:
            print("[gcal] Skipped: GOOGLE_CALENDAR_ID or credentials not configured.")
            return None

        start_dt = datetime.strptime(
            f"{booking['date']} {booking['time']}", "%Y-%m-%d %H:%M"
        )
        end_dt = start_dt + timedelta(minutes=EVENT_DURATION_MIN)

        is_online = booking.get("service") == ONLINE_SERVICE_NAME

        description_lines = [
            f"Patient: {booking['name']}",
            f"Service: {booking['service']}",
        ]
        if patient_phone:
            description_lines.append(f"WhatsApp: {patient_phone}")
        description_lines.append(f"Clinic phone: {CLINIC['phone']}")
        description_lines.append("Booked via WhatsApp bot")
        if is_online:
            description_lines.append("")
            description_lines.append("This is an ONLINE consultation. Join via Google Meet (link in event).")

        event_body = {
            "summary": f"{booking['service']} - {booking['name']}",
            "location": "Google Meet (online)" if is_online else CLINIC["address"],
            "description": "\n".join(description_lines),
            "start": {
                "dateTime": start_dt.isoformat(),
                "timeZone": TIMEZONE,
            },
            "end": {
                "dateTime": end_dt.isoformat(),
                "timeZone": TIMEZONE,
            },
            "reminders": {
                "useDefault": False,
                "overrides": [
                    {"method": "popup", "minutes": 60},
                    {"method": "popup", "minutes": 10},
                ],
            },
        }

        # NOTE: Service accounts cannot invite attendees on a personal Gmail
        # calendar (Google blocks it without Domain-Wide Delegation). The doctor
        # sees bookings via the shared calendar instead.

        # For online consultations, ask Google to attach a Meet link to the event.
        # Personal Gmail accounts may reject this with HTTP 400 — we then retry
        # without it and use FALLBACK_MEET_LINK from .env.
        created = None
        meet_link = None
        if is_online:
            online_body = dict(event_body)
            online_body["conferenceData"] = {
                "createRequest": {
                    "requestId": str(uuid.uuid4()),
                    "conferenceSolutionKey": {"type": "hangoutsMeet"},
                }
            }
            try:
                created = service.events().insert(
                    calendarId=CALENDAR_ID,
                    body=online_body,
                    sendUpdates="none",
                    conferenceDataVersion=1,
                ).execute()
                meet_link = created.get("hangoutLink")
                if not meet_link:
                    for ep in (created.get("conferenceData") or {}).get("entryPoints", []):
                        if ep.get("entryPointType") == "video":
                            meet_link = ep.get("uri")
                            break
            except HttpError as e:
                print(f"[gcal] Meet auto-create failed ({e.resp.status}). Using fallback link.")
                created = None  # fall through to plain insert below

        if created is None:
            # Plain insert (offline service OR Meet auto-create unavailable)
            if is_online and FALLBACK_MEET_LINK:
                event_body["description"] += f"\n\nJoin Meet: {FALLBACK_MEET_LINK}"
            created = service.events().insert(
                calendarId=CALENDAR_ID,
                body=event_body,
                sendUpdates="none",
            ).execute()
            if is_online:
                meet_link = FALLBACK_MEET_LINK or None

        event_link = created.get("htmlLink")
        print(f"[gcal] Event created: {event_link}")
        if is_online:
            print(f"[gcal] Meet link: {meet_link or '(not generated)'}")

        return {"event_link": event_link, "meet_link": meet_link}

    except HttpError as e:
        print(f"[gcal] Google API error: {e}")
        return None
    except Exception as e:
        print(f"[gcal] Failed to create event: {e}")
        return None
