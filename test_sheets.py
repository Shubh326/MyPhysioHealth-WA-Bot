"""
Quick end-to-end test for Google Sheets lead logging.

Run from the project folder:   python3 test_sheets.py

It appends one clearly-marked TEST row to your configured sheet/tab, prints
what it read back, then deletes that test row so the sheet is left clean.
If everything is set up correctly you'll see "SUCCESS" at the end.
"""

from dotenv import load_dotenv
load_dotenv()

import sheets

TEST_NAME = "TEST - please ignore"

booking = {
    "name": TEST_NAME,
    "service": "Online Physiotherapy Consultation",
    "date": "2026-06-20",
    "time": "11:00",
    "booked_at": "2026-06-14 00:00:00",
    "event_link": "https://example.com/test-event",
    "meet_link": "https://meet.google.com/test-link",
}


def main():
    if not sheets.SHEET_ID:
        print("FAIL: GOOGLE_SHEET_ID is not set in .env")
        return

    ok = sheets.append_lead(booking, patient_phone="whatsapp:+910000000000")
    if not ok:
        print("FAIL: append_lead returned False. Check the [sheets] error above.")
        print("Common causes: sheet not shared with the service account (Editor),")
        print("or the Google Sheets API is not enabled in the project.")
        return

    svc = sheets._get_service()
    tab = sheets._resolve_tab(svc)
    print(f"Wrote to tab: {tab}")

    vals = (
        svc.spreadsheets()
        .values()
        .get(spreadsheetId=sheets.SHEET_ID, range=f"{tab}!A1:K200")
        .execute()
        .get("values", [])
    )
    print(f"Rows in sheet now: {len(vals)}")
    if vals:
        print("Header:", vals[0])

    # Find and delete the test row to leave the sheet clean.
    idx = next(
        (i for i, r in enumerate(vals) if len(r) > 1 and r[1] == TEST_NAME), None
    )
    if idx is not None:
        print("Test row written:", vals[idx])
        meta = svc.spreadsheets().get(spreadsheetId=sheets.SHEET_ID).execute()
        sid = next(
            sh["properties"]["sheetId"]
            for sh in meta["sheets"]
            if sh["properties"]["title"] == tab
        )
        svc.spreadsheets().batchUpdate(
            spreadsheetId=sheets.SHEET_ID,
            body={
                "requests": [
                    {
                        "deleteDimension": {
                            "range": {
                                "sheetId": sid,
                                "dimension": "ROWS",
                                "startIndex": idx,
                                "endIndex": idx + 1,
                            }
                        }
                    }
                ]
            },
        ).execute()
        print("Test row deleted — sheet left clean.")

    print("\nSUCCESS: Google Sheets logging is working end-to-end.")


if __name__ == "__main__":
    main()
