"""
Google Sheets lead/event logging for MyphysioHealth bot.

- Reuses the SAME service account as gcal.py (gcal-credentials.json) — you just
  enable the Google Sheets API and share the target sheet with the service
  account email (Editor).
- On every confirmed booking we append one row to the sheet.
- All failures are caught so a Sheets outage NEVER blocks a WhatsApp booking
  (same best-effort contract as gcal.py).

Setup checklist (do once):
  1. Enable the Google Sheets API in the same GCP project as Calendar.
  2. Create a Google Sheet (e.g. "MyphysioHealth Leads").
  3. Share that sheet with the service account email (the client_email in
     gcal-credentials.json) and give it "Editor" access.
  4. Copy the spreadsheet ID from its URL:
     https://docs.google.com/spreadsheets/d/<THIS_PART>/edit
     and paste it into .env as GOOGLE_SHEET_ID.
  5. (Optional) Set GOOGLE_SHEET_TAB if your tab isn't named "Sheet1".

The header row is written automatically the first time a row is appended to an
empty sheet.
"""

import json
import os
from datetime import datetime

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

ONLINE_SERVICE_NAME = "Online Physiotherapy Consultation"

# Sheets API needs its own scope. Service account is shared with the sheet.
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

CREDENTIALS_FILE = os.getenv("GOOGLE_CREDENTIALS_FILE", "gcal-credentials.json")
SHEET_ID = os.getenv("GOOGLE_SHEET_ID", "")
# Target tab. You can specify EITHER:
#   GOOGLE_SHEET_TAB  -> the tab's name (e.g. "Sheet1", "Leads")
#   GOOGLE_SHEET_GID  -> the gid from the sheet URL (...#gid=638574709)
# GID wins if both are set; we resolve it to the tab name at runtime.
SHEET_TAB = os.getenv("GOOGLE_SHEET_TAB", "Sheet1")
SHEET_GID = os.getenv("GOOGLE_SHEET_GID", "").strip()
DEFAULT_SOURCE = os.getenv("LEAD_SOURCE", "WhatsApp bot")
DEFAULT_STATUS = os.getenv("LEAD_DEFAULT_STATUS", "New")

HEADER = [
    "Booked At",
    "Name",
    "Phone",
    "Service",
    "Date",
    "Time",
    "Mode",
    "Status",
    "Source",
    "Calendar Link",
    "Meet Link",
]


def _get_service():
    """Build a Google Sheets API client. Returns None if not configured.

    Reads credentials from either GOOGLE_CREDENTIALS_JSON env var (paste raw
    JSON) or GOOGLE_CREDENTIALS_FILE on disk. JSON env var wins if both set.
    """
    if not SHEET_ID:
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
    return build("sheets", "v4", credentials=creds, cache_discovery=False)


def _resolve_tab(service):
    """Return the target tab name.

    If GOOGLE_SHEET_GID is set, look up the matching tab title; otherwise fall
    back to GOOGLE_SHEET_TAB. Returns SHEET_TAB if the gid can't be resolved.
    """
    if not SHEET_GID:
        return SHEET_TAB
    try:
        meta = service.spreadsheets().get(spreadsheetId=SHEET_ID).execute()
        for sh in meta.get("sheets", []):
            props = sh.get("properties", {})
            if str(props.get("sheetId")) == SHEET_GID:
                return props.get("title", SHEET_TAB)
        print(f"[sheets] gid {SHEET_GID} not found; using '{SHEET_TAB}'.")
    except HttpError as e:
        print(f"[sheets] Could not resolve gid ({e.resp.status}); using '{SHEET_TAB}'.")
    return SHEET_TAB


def _ensure_header(service, tab):
    """Write the header row if the first row of the tab is empty."""
    try:
        resp = (
            service.spreadsheets()
            .values()
            .get(spreadsheetId=SHEET_ID, range=f"{tab}!A1:K1")
            .execute()
        )
        if resp.get("values"):
            return  # header (or some data) already present
        service.spreadsheets().values().update(
            spreadsheetId=SHEET_ID,
            range=f"{tab}!A1",
            valueInputOption="USER_ENTERED",
            body={"values": [HEADER]},
        ).execute()
        print("[sheets] Header row written.")
    except HttpError as e:
        # Non-fatal: appending still works without a header.
        print(f"[sheets] Could not verify/write header ({e.resp.status}).")


def append_lead(booking, patient_phone=""):
    """
    Append one lead row for a confirmed booking.

    booking dict keys: name, service, date (YYYY-MM-DD), time (HH:MM),
    booked_at (optional), event_link (optional), meet_link (optional).

    Returns True on success, False on any failure (never raises).
    """
    try:
        service = _get_service()
        if service is None:
            print("[sheets] Skipped: GOOGLE_SHEET_ID or credentials not configured.")
            return False

        tab = _resolve_tab(service)
        _ensure_header(service, tab)

        is_online = booking.get("service") == ONLINE_SERVICE_NAME
        booked_at = booking.get("booked_at") or datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        row = [
            booked_at,
            booking.get("name", ""),
            patient_phone,
            booking.get("service", ""),
            booking.get("date", ""),
            booking.get("time", ""),
            "Online" if is_online else "Offline",
            DEFAULT_STATUS,
            DEFAULT_SOURCE,
            booking.get("event_link", ""),
            booking.get("meet_link", ""),
        ]

        service.spreadsheets().values().append(
            spreadsheetId=SHEET_ID,
            range=f"{tab}!A:K",
            valueInputOption="USER_ENTERED",
            insertDataOption="INSERT_ROWS",
            body={"values": [row]},
        ).execute()

        print(f"[sheets] Lead appended for {booking.get('name', '?')}.")
        return True

    except HttpError as e:
        print(f"[sheets] Google API error: {e}")
        return False
    except Exception as e:
        print(f"[sheets] Failed to append lead: {e}")
        return False
