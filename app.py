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

# Optional: Google Calendar sync. Imported lazily so a missing/misconfigured
# install never blocks the bot from running.
try:
    from gcal import create_event as gcal_create_event
except Exception as _gcal_err:
    print(f"[gcal] Disabled: {_gcal_err}")
    gcal_create_event = None

app = Flask(__name__)

# ---------------------------------------------------------------------------
# In-memory stores (replace with a database for production)
# ---------------------------------------------------------------------------
user_sessions = {}       # tracks conversation state per phone number
appointments = {}        # booked appointments: {phone: [{date, time, service, name}]}
# In production set APPOINTMENTS_FILE to a path on the persistent disk
# (e.g. /var/data/appointments.json on Render) so bookings survive restarts.
BOOKING_FILE = os.getenv("APPOINTMENTS_FILE", "appointments.json")


def load_appointments():
    """Load appointments from JSON file if it exists."""
    global appointments
    if os.path.exists(BOOKING_FILE):
        with open(BOOKING_FILE, "r") as f:
            appointments = json.load(f)


def save_appointments():
    """Persist appointments to a JSON file."""
    parent = os.path.dirname(BOOKING_FILE)
    if parent and not os.path.exists(parent):
        os.makedirs(parent, exist_ok=True)
    with open(BOOKING_FILE, "w") as f:
        json.dump(appointments, f, indent=2, default=str)


load_appointments()

# ---------------------------------------------------------------------------
# Message builders
# ---------------------------------------------------------------------------

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
        "1️⃣  Our Services\n"
        "2️⃣  Book an Appointment\n"
        "3️⃣  Clinic Timings & Location\n"
        "4️⃣  Frequently Asked Questions\n"
        "5️⃣  Exercise Tips\n"
        "6️⃣  Talk to Us (Contact Info)\n"
        "0️⃣  Back to Main Menu\n"
    )


def get_services_menu():
    msg = "💆 *Our Services:*\n\n"
    for key, svc in SERVICES.items():
        msg += f"*{key}.* {svc['name']}\n"
    msg += "\n_Reply with a service number for full details, or *0* for main menu._"
    return msg


def get_timings():
    msg = f"🕐 *{CLINIC['name']} - Working Hours:*\n\n"
    for day, info in TIMINGS.items():
        status = info["hours"] if info["open"] else "❌ Closed"
        msg += f"*{day}:* {status}\n"
    msg += (
        f"\n📍 *Address:*\n{CLINIC['address']}\n\n"
        f"📌 *Google Maps:*\n{CLINIC['google_maps_link']}"
    )
    return msg


def get_faqs_menu():
    msg = "❓ *Frequently Asked Questions:*\n\n"
    for key, faq in FAQS.items():
        msg += f"*{key}.* {faq['question']}\n"
    msg += "\n_Reply with a question number, or *0* for main menu._"
    return msg


def get_exercise_menu():
    msg = (
        "🏋️ *Exercise Tips - Choose Your Condition:*\n\n"
        "1️⃣  Back Pain\n"
        "2️⃣  Neck Pain\n"
        "3️⃣  Knee Pain\n\n"
        "_Reply with a number, or *0* for main menu._"
    )
    return msg


def get_exercise_tips(condition_key):
    tips = EXERCISE_TIPS.get(condition_key)
    if not tips:
        return "Sorry, I don't have exercises for that condition yet. Please consult your physiotherapist."
    msg = f"{tips['title']}\n\n"
    for ex in tips["exercises"]:
        msg += f"{ex}\n\n"
    msg += (
        "⚠️ *Important:* Stop any exercise if you feel sharp pain. "
        "These are general guidelines — your therapist may customize them for you.\n\n"
        "_Reply *0* for main menu._"
    )
    return msg


def get_contact_info():
    msg = (
        f"📞 *Contact {CLINIC['name']}:*\n\n"
        f"📱 Phone: {CLINIC['phone']}\n"
    )

    if CLINIC.get("email"):
        msg += f"📧 Email: {CLINIC['email']}\n"

    if CLINIC.get("website"):
        msg += f"🌐 Website: {CLINIC['website']}\n"

    msg += (
        f"📍 Address: {CLINIC['address']}\n\n"
        f"📌 Google Maps: {CLINIC['google_maps_link']}\n\n"
        "Feel free to call or visit us during working hours!\n\n"
        "_Reply *0* for main menu._"
    )
    return msg


# ---------------------------------------------------------------------------
# Appointment booking helpers
# ---------------------------------------------------------------------------

# Minimum lead time before a slot — patients can't book a slot that's already
# starting in less than this window.
BOOKING_LEAD_TIME = timedelta(minutes=30)


def _today_has_remaining_slots(today_date):
    """True if today still has at least one bookable slot (after lead-time buffer)."""
    all_slots = (
        SATURDAY_SLOTS[:] if today_date.strftime("%A") == "Saturday"
        else APPOINTMENT_SLOTS[:]
    )
    now = datetime.now()
    for s in all_slots:
        slot_dt = datetime.strptime(
            f"{today_date.strftime('%Y-%m-%d')} {s}", "%Y-%m-%d %H:%M"
        )
        if slot_dt - now > BOOKING_LEAD_TIME:
            return True
    return False


def get_available_dates():
    """Return the next 7 available (open) dates, including today if slots remain."""
    dates = []
    today = datetime.now().date()
    for i in range(0, 15):  # look ahead from today to find 7 open ones
        d = today + timedelta(days=i)
        day_name = d.strftime("%A")
        if not TIMINGS.get(day_name, {}).get("open", False):
            continue
        # Skip today if no slots remain after the lead-time buffer
        if i == 0 and not _today_has_remaining_slots(d):
            continue
        dates.append(d)
        if len(dates) == 7:
            break
    return dates


def format_date_options(dates):
    today = datetime.now().date()
    msg = "📅 *Choose a Date:*\n\n"
    for i, d in enumerate(dates, 1):
        day_name = d.strftime("%A")
        label = "Today" if d == today else day_name
        msg += f"*{i}.* {d.strftime('%d %b %Y')} ({label})\n"
    msg += "\n_Reply with the date number, or *0* to cancel._"
    return msg


def get_slots_for_date(chosen_date):
    """Return available time slots for a given date, excluding already booked
    and already-past slots."""
    day_name = chosen_date.strftime("%A")
    if day_name == "Saturday":
        all_slots = SATURDAY_SLOTS[:]
    else:
        all_slots = APPOINTMENT_SLOTS[:]

    # If today, drop slots that are already starting (or within lead time)
    if chosen_date == datetime.now().date():
        now = datetime.now()
        all_slots = [
            s for s in all_slots
            if datetime.strptime(
                f"{chosen_date.strftime('%Y-%m-%d')} {s}", "%Y-%m-%d %H:%M"
            ) - now > BOOKING_LEAD_TIME
        ]

    # Remove already booked slots for that date
    date_str = chosen_date.strftime("%Y-%m-%d")
    for phone, bookings in appointments.items():
        for b in bookings:
            if b["date"] == date_str and b["time"] in all_slots:
                all_slots.remove(b["time"])

    return all_slots


def format_slot_options(slots):
    if not slots:
        return "😔 Sorry, no slots are available on this date. Please choose another date.\n\n_Reply *0* for main menu._"
    msg = "⏰ *Available Time Slots:*\n\n"
    for i, slot in enumerate(slots, 1):
        # Convert to 12hr format for display
        t = datetime.strptime(slot, "%H:%M")
        msg += f"*{i}.* {t.strftime('%I:%M %p')}\n"
    msg += "\n_Reply with the slot number, or *0* to cancel._"
    return msg


def format_service_options_for_booking():
    msg = "💆 *Which service would you like to book?*\n\n"
    for key, svc in SERVICES.items():
        msg += f"*{key}.* {svc['name']}\n"
    msg += "\n_Reply with a service number, or *0* to cancel._"
    return msg


def get_booking_confirmation(booking):
    t = datetime.strptime(booking["time"], "%H:%M")
    d = datetime.strptime(booking["date"], "%Y-%m-%d")
    is_online = booking["service"] == "Online Physiotherapy Consultation"
    meet_link = booking.get("meet_link")

    if is_online:
        location_line = "💻 *Mode:* Online (Google Meet)\n"
        if meet_link:
            location_line += f"🔗 *Meet link:* {meet_link}\n"
        else:
            location_line += "🔗 *Meet link:* will be shared before the appointment\n"
        reminder_block = (
            "📌 *Please remember:*\n"
            "• Join 5 minutes early\n"
            "• Use a quiet, well-lit room\n"
            "• Keep any medical reports handy\n"
        )
    else:
        location_line = f"📍 *Location:* {CLINIC['address']}\n"
        reminder_block = (
            "📌 *Please remember:*\n"
            "• Arrive 10 minutes early\n"
            "• Wear comfortable clothing\n"
            "• Bring any medical reports/X-rays\n"
        )

    return (
        "✅ *Appointment Confirmed!*\n\n"
        f"👤 *Name:* {booking['name']}\n"
        f"💆 *Service:* {booking['service']}\n"
        f"📅 *Date:* {d.strftime('%d %b %Y (%A)')}\n"
        f"⏰ *Time:* {t.strftime('%I:%M %p')}\n"
        f"{location_line}\n"
        f"{reminder_block}\n"
        f"To reschedule or cancel, call us at {CLINIC['phone']}\n\n"
        "_Reply *0* for main menu._"
    )


def get_my_appointments(phone):
    """Show upcoming appointments for this user."""
    user_bookings = appointments.get(phone, [])
    today_str = datetime.now().strftime("%Y-%m-%d")
    upcoming = [b for b in user_bookings if b["date"] >= today_str]

    if not upcoming:
        return "📋 You don't have any upcoming appointments.\n\n_Reply *2* to book one, or *0* for main menu._"

    msg = "📋 *Your Upcoming Appointments:*\n\n"
    for i, b in enumerate(upcoming, 1):
        d = datetime.strptime(b["date"], "%Y-%m-%d")
        t = datetime.strptime(b["time"], "%H:%M")
        msg += (
            f"*{i}.* {b['service']}\n"
            f"   📅 {d.strftime('%d %b %Y (%A)')} at {t.strftime('%I:%M %p')}\n\n"
        )
    msg += "_Reply *0* for main menu._"
    return msg


# ---------------------------------------------------------------------------
# Conversation state machine
# ---------------------------------------------------------------------------

def reset_session(phone):
    user_sessions[phone] = {"state": "main_menu", "data": {}}


def handle_message(phone, incoming_msg):
    """Process incoming message and return response text."""
    incoming_msg = incoming_msg.strip()
    msg_lower = incoming_msg.lower()

    # Initialize session if new user
    if phone not in user_sessions:
        reset_session(phone)

    session = user_sessions[phone]
    state = session["state"]

    # Global commands that work from any state
    if msg_lower in ("0", "menu", "hi", "hello", "hey", "start"):
        reset_session(phone)
        greeting = get_greeting()
        return f"{greeting}! 👋\n\n{get_main_menu()}"

    if msg_lower in ("cancel", "quit", "exit"):
        reset_session(phone)
        return "No problem! Your action has been cancelled.\n\n" + get_main_menu()

    # ---- MAIN MENU STATE ----
    if state == "main_menu":
        if incoming_msg == "1":
            session["state"] = "services"
            return get_services_menu()
        elif incoming_msg == "2":
            # If user just viewed a service, skip service selection and go straight to name
            last_key = session["data"].get("last_viewed_service_key")
            if last_key and last_key in SERVICES:
                session["data"]["service"] = SERVICES[last_key]["name"]
                session["data"]["service_key"] = last_key
                session["state"] = "booking_name"
                return (
                    f"💆 Booking *{SERVICES[last_key]['name']}*.\n\n"
                    "👤 Please type your *full name* for the appointment:"
                )
            session["state"] = "booking_service"
            return format_service_options_for_booking()
        elif incoming_msg == "3":
            return get_timings() + "\n\n_Reply *0* for main menu._"
        elif incoming_msg == "4":
            session["state"] = "faqs"
            return get_faqs_menu()
        elif incoming_msg == "5":
            session["state"] = "exercises"
            return get_exercise_menu()
        elif incoming_msg == "6":
            return get_contact_info()
        elif msg_lower in ("my appointments", "appointments", "my booking", "bookings"):
            return get_my_appointments(phone)
        else:
            return (
                "🤔 I didn't understand that. Please reply with a number from the menu.\n\n"
                + get_main_menu()
            )

    # ---- SERVICES STATE ----
    elif state == "services":
        if incoming_msg in SERVICES:
            svc = SERVICES[incoming_msg]
            session["state"] = "main_menu"
            # Remember which service was just viewed so booking can skip re-asking
            session["data"]["last_viewed_service_key"] = incoming_msg
            return (
                f"💆 *{svc['name']}*\n\n"
                f"📝 {svc['description']}\n\n"
                f"⏱ Duration: {svc['duration']}\n"
                f"Fee: {svc['price']}\n\n"
                f"Would you like to book *{svc['name']}*?\n"
                "Reply *2* to book this service, or *0* for main menu."
            )
        else:
            return f"Please reply with a valid service number (1-{len(SERVICES)}), or *0* for main menu."

    # ---- FAQ STATE ----
    elif state == "faqs":
        if incoming_msg in FAQS:
            faq = FAQS[incoming_msg]
            return (
                f"❓ *{faq['question']}*\n\n"
                f"{faq['answer']}\n\n"
                "_Ask another question (1-6), or reply *0* for main menu._"
            )
        else:
            return "Please reply with a valid question number (1-6), or *0* for main menu."

    # ---- EXERCISE STATE ----
    elif state == "exercises":
        exercise_map = {"1": "back_pain", "2": "neck_pain", "3": "knee_pain"}
        if incoming_msg in exercise_map:
            session["state"] = "main_menu"
            return get_exercise_tips(exercise_map[incoming_msg])
        else:
            return "Please reply with 1, 2, or 3 to choose a condition, or *0* for main menu."

    # ---- BOOKING: CHOOSE SERVICE ----
    elif state == "booking_service":
        if incoming_msg in SERVICES:
            session["data"]["service"] = SERVICES[incoming_msg]["name"]
            session["data"]["service_key"] = incoming_msg
            session["state"] = "booking_name"
            return "👤 *Great!* Please type your *full name* for the appointment:"
        else:
            return f"Please reply with a valid service number (1-{len(SERVICES)}), or *0* to cancel."

    # ---- BOOKING: GET NAME ----
    elif state == "booking_name":
        if len(incoming_msg) < 2 or incoming_msg.isdigit():
            return "Please enter a valid name (at least 2 characters):"
        session["data"]["name"] = incoming_msg.title()
        session["state"] = "booking_date"
        dates = get_available_dates()
        session["data"]["available_dates"] = [d.strftime("%Y-%m-%d") for d in dates]
        return format_date_options(dates)

    # ---- BOOKING: CHOOSE DATE ----
    elif state == "booking_date":
        available_dates = session["data"].get("available_dates", [])
        try:
            idx = int(incoming_msg) - 1
            if 0 <= idx < len(available_dates):
                chosen_date_str = available_dates[idx]
                chosen_date = datetime.strptime(chosen_date_str, "%Y-%m-%d").date()
                session["data"]["date"] = chosen_date_str
                slots = get_slots_for_date(chosen_date)
                session["data"]["available_slots"] = slots
                session["state"] = "booking_time"
                return format_slot_options(slots)
            else:
                return f"Please reply with a number between 1 and {len(available_dates)}, or *0* to cancel."
        except ValueError:
            return "Please reply with the date number from the list, or *0* to cancel."

    # ---- BOOKING: CHOOSE TIME ----
    elif state == "booking_time":
        available_slots = session["data"].get("available_slots", [])
        try:
            idx = int(incoming_msg) - 1
            if 0 <= idx < len(available_slots):
                chosen_time = available_slots[idx]
                session["data"]["time"] = chosen_time

                # Build confirmation preview
                booking = {
                    "name": session["data"]["name"],
                    "service": session["data"]["service"],
                    "date": session["data"]["date"],
                    "time": chosen_time,
                }
                t = datetime.strptime(booking["time"], "%H:%M")
                d = datetime.strptime(booking["date"], "%Y-%m-%d")

                session["state"] = "booking_confirm"
                return (
                    "📋 *Please confirm your appointment:*\n\n"
                    f"👤 Name: {booking['name']}\n"
                    f"💆 Service: {booking['service']}\n"
                    f"📅 Date: {d.strftime('%d %b %Y (%A)')}\n"
                    f"⏰ Time: {t.strftime('%I:%M %p')}\n\n"
                    "Reply *YES* to confirm or *NO* to cancel."
                )
            else:
                return f"Please reply with a number between 1 and {len(available_slots)}, or *0* to cancel."
        except ValueError:
            return "Please reply with the slot number from the list, or *0* to cancel."

    # ---- BOOKING: CONFIRM ----
    elif state == "booking_confirm":
        if msg_lower in ("yes", "y", "confirm"):
            booking = {
                "name": session["data"]["name"],
                "service": session["data"]["service"],
                "date": session["data"]["date"],
                "time": session["data"]["time"],
                "booked_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }

            # Push to Google Calendar BEFORE confirming so we can include the
            # Meet link (if any) in the WhatsApp message. Best-effort: never blocks.
            if gcal_create_event is not None:
                try:
                    result = gcal_create_event(booking, patient_phone=phone)
                    if isinstance(result, dict):
                        if result.get("meet_link"):
                            booking["meet_link"] = result["meet_link"]
                        if result.get("event_link"):
                            booking["event_link"] = result["event_link"]
                except Exception as e:
                    print(f"[gcal] sync failed: {e}")

            # Save appointment (with meet_link if it was generated)
            if phone not in appointments:
                appointments[phone] = []
            appointments[phone].append(booking)
            save_appointments()

            reset_session(phone)
            return get_booking_confirmation(booking)

        elif msg_lower in ("no", "n", "cancel"):
            reset_session(phone)
            return "❌ Booking cancelled. No worries!\n\n" + get_main_menu()
        else:
            return "Please reply *YES* to confirm or *NO* to cancel."

    # ---- FALLBACK ----
    else:
        reset_session(phone)
        return "Something went wrong. Let's start over!\n\n" + get_main_menu()


# ---------------------------------------------------------------------------
# Flask routes
# ---------------------------------------------------------------------------

@app.route("/")
def home():
    return (
        f"<h1>{CLINIC['name']} - WhatsApp Chatbot</h1>"
        "<p>Bot is running! Configure your Twilio webhook to point to <code>/webhook</code></p>"
    )


@app.route("/webhook", methods=["POST"])
def webhook():
    """Twilio sends incoming WhatsApp messages here."""
    incoming_msg = request.values.get("Body", "").strip()
    sender = request.values.get("From", "")

    # Clean phone number (remove 'whatsapp:' prefix for storage)
    phone = sender.replace("whatsapp:", "")

    print(f"[{datetime.now().strftime('%H:%M:%S')}] From {phone}: {incoming_msg}")

    # Process message and get response
    response_text = handle_message(phone, incoming_msg)

    # Build Twilio response
    resp = MessagingResponse()
    msg = resp.message()
    msg.body(response_text)

    print(f"[{datetime.now().strftime('%H:%M:%S')}] Reply sent to {phone}")
    return str(resp)


@app.route("/health", methods=["GET"])
def health():
    """Health check endpoint."""
    return {
        "status": "running",
        "clinic": CLINIC["name"],
        "active_sessions": len(user_sessions),
        "total_appointments": sum(len(v) for v in appointments.values()),
    }


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    port = int(os.getenv("FLASK_PORT", 8080))
    debug = os.getenv("FLASK_DEBUG", "True").lower() == "true"
    print(f"\n🏥 {CLINIC['name']} WhatsApp Bot")
    print(f"🚀 Server starting on port {port}...")
    print(f"📱 Webhook URL: http://localhost:{port}/webhook")
    print(f"   (Use ngrok to expose this for Twilio)\n")
    app.run(host="0.0.0.0", port=port, debug=debug)
