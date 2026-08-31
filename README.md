# MyPhysioHealth WhatsApp Booking Bot

A WhatsApp chatbot for **MyPhysioHealth Physio-Rehab Clinic** that lets patients book physiotherapy appointments, browse services, get answers to common questions, and receive exercise tips — all through WhatsApp. Confirmed bookings are automatically added to Google Calendar and (optionally) logged to a Google Sheet.

Built with Python + Flask and Twilio's WhatsApp API.

## Features

- **Appointment booking** — patients pick a service, date, and time from live 30-minute slots (9:00 AM – 7:00 PM IST, Mon–Sat, with a 1:00–2:00 PM lunch break).
- **Google Calendar sync** — each confirmed booking creates a calendar event in the clinic's timezone (Asia/Kolkata).
- **Google Sheets lead logging** *(optional)* — every booking can be appended as a row for tracking.
- **Services & pricing** — patients can browse available treatments.
- **FAQs** — instant answers to common questions (referrals, what to wear, payment methods, etc.).
- **Exercise tips** — follow-up self-care guidance for common conditions.

## Tech Stack

- **Python 3.8+** / **Flask** — web server and webhook handler
- **Twilio WhatsApp API** — messaging
- **Google Calendar & Sheets API** — booking sync and lead logging
- **Gunicorn** — production WSGI server
- **Render** — hosting (auto-deploys on push to `main`)

## Project Structure

```
├── app.py              # Main bot logic and webhook handler
├── gcal.py             # Google Calendar event creation
├── sheets.py           # Google Sheets lead logging
├── config.py           # Clinic details, hours, slots, services, FAQs
├── render.yaml         # Render deployment config
├── requirements.txt    # Python dependencies
├── .env.example        # Environment variable template
└── SETUP_GUIDE.md      # Full step-by-step setup & deployment guide
```

## Quick Start

```bash
# 1. Install dependencies
pip3 install -r requirements.txt

# 2. Create your environment file
cp .env.example .env      # then fill in your Twilio + Google credentials

# 3. Run locally
python3 app.py
```

Expose your local server with `ngrok http 8080` and point your Twilio WhatsApp Sandbox webhook at `https://<your-ngrok-url>/webhook`.

For full setup — Twilio sandbox, Google Calendar service account, production deployment to Render, and registering a dedicated WhatsApp Business number — see **[SETUP_GUIDE.md](SETUP_GUIDE.md)**.

## Configuration

Clinic-specific details (name, address, hours, services, pricing, FAQs, appointment slots) live in **`config.py`**. Credentials and environment-specific values are supplied via environment variables — see `.env.example` for the full list.

## Security

No secrets are committed to this repository. Credential files (`.env`, `gcal-credentials.json`) and local data (`appointments.json`) are excluded via `.gitignore`. All API keys and tokens are read from environment variables at runtime.

## License

This project is provided as-is for the MyPhysioHealth clinic. Feel free to adapt it for your own use.
