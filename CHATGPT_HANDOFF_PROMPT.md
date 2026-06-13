# Context Handoff: WhatsApp Chatbot for Physiotherapy Clinic

Paste everything below into ChatGPT as a single prompt to continue this project.

---

## ROLE

You are taking over an in-progress project from another AI assistant. The user is **Shubham Kashyap** (shubham.k@rishihood.edu.in). Help him continue building, improving, and deploying a WhatsApp chatbot for his physiotherapy clinic. Be concise and direct — Shubham prefers minimal verbosity.

## PROJECT OVERVIEW

A Twilio-powered WhatsApp chatbot for **MyphysioHealth Physio-Rehab Clinic** (Burari, Delhi). The bot handles greetings, services/pricing info, full appointment booking, clinic timings/location, FAQs, exercise tips, and contact info. Built in Python with Flask + Twilio.

**Current status:** Bot is live and working on Twilio Sandbox via ngrok. Clinic details pulled from Google My Business profile. Pricing is still placeholder. Two test bookings exist.

## TECH STACK

- Python 3.8+
- Flask 3.0.3 (webhook server on port **8080** — changed from 5000 because macOS AirPlay uses 5000)
- Twilio 9.0.5 (`twilio.twiml.messaging_response.MessagingResponse`)
- python-dotenv 1.0.1
- apscheduler 3.10.4 (installed, not yet used)
- ngrok for tunneling local server to public URL
- JSON file for appointment storage (no DB yet)
- In-memory dict for user session state

## CHAT HISTORY SUMMARY (chronological)

**Session 1 — Build WhatsApp chatbot for clinic**
1. Shubham asked for a WhatsApp chatbot for his physiotherapy clinic.
2. He chose **Twilio** and asked for "Both + More" features (info + booking + extras).
3. He shared his Google Maps Business link: https://maps.app.goo.gl/A2f7gcyBa7Ynnep36 — initially the assistant couldn't fetch it, so it built with placeholder clinic data.
4. Assistant created the full project: `app.py`, `config.py`, `requirements.txt`, `.env.example`, `SETUP_GUIDE.md`.
5. Shubham created a Twilio account.
6. Assistant walked him through getting Account SID + Auth Token, writing the `.env` file, and starting the bot.
7. Hit issue: `pip` not found → switched to `pip3`. Folder navigation issue (spaces) → wrap path in quotes.
8. Hit issue: **port 5000 in use** (macOS AirPlay Receiver). Assistant changed Flask port to **8080** in `app.py`.
9. Installed and authenticated ngrok via Homebrew. Got tunnel URL `https://amid-ritalin-unharmed.ngrok-free.dev`.
10. Connected webhook in Twilio sandbox settings → `/webhook` endpoint. **Bot went live and confirmed working.**
11. Assistant then accessed the GMB profile via Chrome and pulled real clinic details. Updated `config.py` with name, phone, address, Google Maps link, timings (Mon–Sat 9 AM–6 PM, Sun closed).
12. Shubham asked where the pricing came from — assistant confirmed it's **placeholder** and needs real values from him.
13. Shubham asked to defer pricing and instead understand how the "Book an Appointment" flow is designed. Assistant explained the full state machine, data storage, and suggested future improvements (DB, reminders, cancel/reschedule, Calendly integration).

**Session 2 — Extend bot to multiple phone numbers**
1. Shubham asked how to make the bot chat with phone numbers other than his.
2. Assistant explained: the code already supports any phone (Twilio passes the `From` field, sessions are keyed by phone). The reason only his number worked is the **Twilio Sandbox opt-in restriction** — each tester must send `join <code>` to the sandbox number once.
3. Outlined two paths: (a) stay on Sandbox and have each user join, or (b) apply for a real WhatsApp Business sender via Twilio + Meta Business verification (1–3 days approval).
4. Flagged that for production: need always-on hosting (Render/Railway/VPS) instead of ngrok, and need to migrate `user_sessions` + `appointments` from in-memory/JSON to a real DB to avoid race conditions.

## CURRENT FILE CONTENTS

### `app.py`

```python
"""
WhatsApp Chatbot for Physiotherapy Clinic
==========================================
A Twilio-powered WhatsApp bot that handles:
- Greeting & main menu navigation
- Service information & pricing
- Appointment booking with date/time selection
- Clinic timings & location
- FAQs
- Exercise tips for common conditions
- Follow-up reminders

Run: python app.py
"""

import os
import json
import re
from datetime import datetime, timedelta
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from dotenv import load_dotenv

from config import CLINIC, SERVICES, TIMINGS, FAQS, APPOINTMENT_SLOTS, SATURDAY_SLOTS, EXERCISE_TIPS

load_dotenv()

app = Flask(__name__)

# In-memory stores (replace with a database for production)
user_sessions = {}       # tracks conversation state per phone number
appointments = {}        # booked appointments: {phone: [{date, time, service, name}]}
BOOKING_FILE = "appointments.json"


def load_appointments():
    global appointments
    if os.path.exists(BOOKING_FILE):
        with open(BOOKING_FILE, "r") as f:
            appointments = json.load(f)


def save_appointments():
    with open(BOOKING_FILE, "w") as f:
        json.dump(appointments, f, indent=2, default=str)


load_appointments()


def get_greeting():
    hour = datetime.now().hour
    if hour < 12:
        return "Good Morning"
    elif hour < 17:
        return "Good Afternoon"
    return "Good Evening"


def get_main_menu():
    return (
        f"🏥 *Welcome to {CLINIC['name']}!*\n"
        f"_{CLINIC['tagline']}_\n\n"
        "How can I help you today? Please reply with a number:\n\n"
        "1️⃣  Our Services & Pricing\n"
        "2️⃣  Book an Appointment\n"
        "3️⃣  Clinic Timings & Location\n"
        "4️⃣  Frequently Asked Questions\n"
        "5️⃣  Exercise Tips\n"
        "6️⃣  Talk to Us (Contact Info)\n"
        "0️⃣  Back to Main Menu\n"
    )


# Conversation states: main_menu, services, faqs, exercises,
# booking_service, booking_name, booking_date, booking_time, booking_confirm

# The bot supports global commands from any state: "0", "menu", "hi", "hello",
# "hey", "start" reset to main menu. "cancel", "quit", "exit" cancel current action.

# Appointment booking flow:
# 1. User sends "2" → booking_service state, shows services
# 2. User picks service → booking_name state
# 3. User types name → booking_date state (next 7 open days, skipping Sundays)
# 4. User picks date → booking_time state (slots filtered by already-booked)
# 5. User picks slot → booking_confirm state (shows summary)
# 6. User says YES → saved to appointments.json + confirmation message

# Slot lists come from APPOINTMENT_SLOTS / SATURDAY_SLOTS in config.py
# Closed days come from TIMINGS in config.py (Sunday is closed)

# Flask routes: "/" (homepage), "/webhook" (POST, Twilio target), "/health" (status)

# Server starts on port from env FLASK_PORT, default 8080
# (Note: changed from 5000 to 8080 because macOS AirPlay uses 5000)
```

*Full app.py is ~440 lines. Key functions:*
- `handle_message(phone, incoming_msg)` — main state machine
- `get_available_dates()` — next 7 open dates
- `get_slots_for_date(chosen_date)` — filters out booked slots
- `get_booking_confirmation(booking)` — formatted confirmation reply
- `get_my_appointments(phone)` — shows user's upcoming bookings (triggered by typing "my appointments")
- `/webhook` route accepts POST from Twilio, returns TwiML MessagingResponse

### `config.py`

```python
CLINIC = {
    "name": "MyphysioHealth Physio-Rehab Clinic",
    "tagline": "Your Trusted Physiotherapy & Rehabilitation Center in Delhi",
    "phone": "+91-8887609630",
    "email": "info@myphysiohealth.com",  # PLACEHOLDER — needs real email
    "website": "https://calendly.com",   # PLACEHOLDER
    "address": "Main Bus Stand, Central, Opp. Aggarwal Sweets, Virendar Nagar, Block B, Sant Nagar, Burari, Delhi, 110084",
    "google_maps_link": "https://maps.app.goo.gl/A2f7gcyBa7Ynnep36",
}

SERVICES = {
    "1": {"name": "Orthopedic Physiotherapy", "duration": "45 mins", "price": "₹800",
          "description": "Treatment for joint pain, fractures, post-surgery rehab, arthritis, and sports injuries."},
    "2": {"name": "Neuro Physiotherapy", "duration": "60 mins", "price": "₹1000",
          "description": "Rehabilitation for stroke, paralysis, Parkinson's, and spinal cord injuries."},
    "3": {"name": "Sports Injury Rehab", "duration": "45 mins", "price": "₹900",
          "description": "Specialized treatment for ACL tears, rotator cuff injuries, muscle strains, and athletic performance recovery."},
    "4": {"name": "Back & Neck Pain Management", "duration": "30 mins", "price": "₹700",
          "description": "Treatment for chronic back pain, cervical spondylosis, sciatica, and disc problems."},
    "5": {"name": "Post-Surgical Rehabilitation", "duration": "45 mins", "price": "₹900",
          "description": "Recovery programs after knee replacement, hip replacement, and other surgeries."},
    "6": {"name": "Dry Needling / Cupping", "duration": "30 mins", "price": "₹600",
          "description": "Trigger point dry needling and cupping therapy for deep muscle pain relief."},
}
# NOTE: All prices and durations above are PLACEHOLDERS — Shubham has NOT yet provided real values.

TIMINGS = {
    "Monday":    {"open": True,  "hours": "9:00 AM - 6:00 PM"},
    "Tuesday":   {"open": True,  "hours": "9:00 AM - 6:00 PM"},
    "Wednesday": {"open": True,  "hours": "9:00 AM - 6:00 PM"},
    "Thursday":  {"open": True,  "hours": "9:00 AM - 6:00 PM"},
    "Friday":    {"open": True,  "hours": "9:00 AM - 6:00 PM"},
    "Saturday":  {"open": True,  "hours": "9:00 AM - 6:00 PM"},
    "Sunday":    {"open": False, "hours": "Closed"},
}

APPOINTMENT_SLOTS = ["09:00","09:45","10:30","11:15","12:00","14:00","14:45","15:30","16:15","17:00","17:45"]
SATURDAY_SLOTS    = ["09:00","09:45","10:30","11:15","12:00","14:00","14:45","15:30","16:15","17:00","17:45"]

FAQS = {
    "1": {"question": "Do I need a doctor's referral?",
          "answer": "No, you can directly book an appointment. Bring any medical reports/prescriptions if available."},
    "2": {"question": "What should I wear to my session?",
          "answer": "Comfortable, loose-fitting clothes. Avoid jeans or tight clothing."},
    "3": {"question": "How many sessions will I need?",
          "answer": "Depends on your condition. Physiotherapist will create a personalized plan after the initial assessment."},
    "4": {"question": "Do you offer home visits?",
          "answer": "Yes, at an additional charge. Call us to schedule."},
    "5": {"question": "What payment methods do you accept?",
          "answer": "Cash, UPI (GPay/PhonePe/Paytm), credit/debit cards, net banking."},
    "6": {"question": "Is physiotherapy painful?",
          "answer": "Most treatments are not painful. You may feel mild discomfort during certain techniques."},
}

EXERCISE_TIPS = {
    "back_pain": {"title": "🏋️ Daily Exercises for Back Pain",
                  "exercises": ["Cat-Cow Stretch", "Knee-to-Chest Stretch", "Bird-Dog", "Pelvic Tilts"]},
    "neck_pain": {"title": "🏋️ Daily Exercises for Neck Pain",
                  "exercises": ["Chin Tucks", "Neck Side Stretch", "Shoulder Shrugs", "Neck Rotations"]},
    "knee_pain": {"title": "🏋️ Daily Exercises for Knee Pain",
                  "exercises": ["Straight Leg Raises", "Wall Sits", "Step-Ups", "Hamstring Curls"]},
}
```

### `requirements.txt`
```
flask==3.0.3
twilio==9.0.5
python-dotenv==1.0.1
apscheduler==3.10.4
```

### `.env.example`
```
TWILIO_ACCOUNT_SID=your_account_sid_here
TWILIO_AUTH_TOKEN=your_auth_token_here
TWILIO_WHATSAPP_NUMBER=whatsapp:+14155238886
FLASK_PORT=5000
FLASK_DEBUG=True
```
(Actual `.env` is populated with Shubham's real Twilio creds — not included here for security.)

### `appointments.json` (current test data)
```json
{
  "+911234567890": [
    {"name": "Shubham Kashyap", "service": "Orthopedic Physiotherapy",
     "date": "2026-04-15", "time": "09:00", "booked_at": "2026-04-14 16:30:59"}
  ],
  "+919717269581": [
    {"name": "Shubham Kashyap", "service": "Orthopedic Physiotherapy",
     "date": "2026-04-15", "time": "10:30", "booked_at": "2026-04-14 18:41:10"}
  ]
}
```

### Project file structure
```
WhatsApp Chat Bot/
├── app.py              # Main bot (Flask + state machine)
├── config.py           # All clinic data (edit this for real info)
├── requirements.txt
├── .env                # Real Twilio creds (DO NOT SHARE)
├── .env.example        # Template
├── appointments.json   # Persistent bookings
└── SETUP_GUIDE.md      # Setup instructions
```

## OPEN ITEMS / WHERE TO PICK UP

1. **Real pricing & service list** — current 6 services and prices in `config.py` are placeholders. Shubham needs to provide real values.
2. **Real email address** — `info@myphysiohealth.com` is a guess.
3. **Production deployment** — currently runs on Shubham's laptop via ngrok. ngrok URL changes on restart, requiring webhook update in Twilio. Need always-on hosting (Render / Railway / VPS).
4. **Production WhatsApp number** — currently using Twilio Sandbox, which requires every user to send `join <code>` first. Move to a verified WhatsApp Business sender via Twilio + Meta Business Manager for unrestricted access.
5. **Database migration** — `user_sessions` (in-memory dict) and `appointments.json` (file) won't scale. Migrate to SQLite or PostgreSQL to avoid race conditions and survive restarts.
6. **Possible feature additions discussed but not built:**
   - Appointment reminders via scheduled WhatsApp messages (apscheduler is already in requirements)
   - Cancel / reschedule existing booking flow inside the bot
   - Calendly integration for real-time slot availability
   - Admin dashboard / weekly digest of bookings

## USER PREFERENCES

- Wants concise, direct responses — minimal explanation.
- On macOS. Uses `python3` and `pip3`. Bot folder at `~/Documents/Claude/Projects/WhatsApp Chat Bot/`.
- Comfortable running terminal commands; needed guidance on paths with spaces (quote them) and the AirPlay-on-port-5000 macOS gotcha.

---

## YOUR TASK

Acknowledge you've absorbed this context, then ask Shubham what he wants to work on next. Suggest the highest-leverage open items first (real pricing, then production deployment + DB migration). Don't repeat back the whole project — just confirm and ask.
