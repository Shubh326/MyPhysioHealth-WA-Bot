# WhatsApp Chatbot - Setup Guide

## Prerequisites
- Python 3.8+
- A Twilio account (free trial works)
- ngrok (for exposing your local server)

## Step 1: Install Dependencies

```bash
cd ~/Documents/Claude/Projects/"WhatsApp Chat Bot"
pip3 install -r requirements.txt
```

## Step 2: Set Up Twilio

1. Go to [Twilio Console](https://console.twilio.com) and create a free account
2. Navigate to **Messaging > Try it out > Send a WhatsApp message**
3. Follow the instructions to join the Twilio Sandbox:
   - Send the provided code (e.g., `join <your-code>`) to **+1 415 523 8886** on WhatsApp
4. Copy your **Account SID** and **Auth Token** from the Twilio dashboard

## Step 3: Configure Environment

1. Copy the example env file:
   ```bash
   cp .env.example .env
   ```
2. Edit `.env` and paste your Twilio credentials:
   ```
   TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   TWILIO_AUTH_TOKEN=your_auth_token_here
   TWILIO_WHATSAPP_NUMBER=whatsapp:+14155238886
   FLASK_PORT=8080
   FLASK_DEBUG=True
   ```

## Step 4: Update Clinic Details

Open `config.py` and replace all placeholder data with your real clinic info:
- Clinic name, address, phone, email
- Services and pricing
- Working hours
- FAQs

## Step 5: Run the Bot

```bash
python3 app.py
```

You should see:
```
🏥 MyphysioHealth Physio-Rehab Clinic WhatsApp Bot
🚀 Server starting on port 8080...
📱 Webhook URL: http://localhost:8080/webhook
```

## Step 6: Expose with ngrok

In a new terminal:
```bash
ngrok http 8080
```

Copy the HTTPS URL (e.g., `https://abc123.ngrok.io`)

## Step 7: Connect Twilio to Your Bot

1. Go to Twilio Console > Messaging > Settings > WhatsApp Sandbox Settings
2. Set the **"When a message comes in"** webhook URL to:
   ```
   https://abc123.ngrok.io/webhook
   ```
3. Method: **POST**
4. Save

## Step 8: Test It!

Send "Hi" to the Twilio sandbox number on WhatsApp. You should see the main menu!

## Going to Production

### A. Deploy to Render

1. Push this project to a private GitHub repo. `.gitignore` already excludes `.env`, `gcal-credentials.json`, and `appointments.json`.
2. Sign up at https://render.com and connect the GitHub repo.
3. Render will detect `render.yaml` and offer "Apply" — accept it. This creates a Web Service on the Starter plan ($7/mo) with a 1 GB persistent disk mounted at `/var/data`.
4. In the Render service → **Environment** tab, add these env vars (values from your local `.env`):
   - `TWILIO_ACCOUNT_SID`
   - `TWILIO_AUTH_TOKEN`
   - `TWILIO_WHATSAPP_NUMBER`  (leave at sandbox value for now)
   - `GOOGLE_CALENDAR_ID`
   - `GOOGLE_CREDENTIALS_JSON`  (open `gcal-credentials.json` in TextEdit, copy ALL contents, paste as the value)
   - `DOCTOR_EMAIL`
   - `CLINIC_MEET_LINK`
5. Wait for the build → you get a permanent URL like `https://myphysio-whatsapp-bot.onrender.com`.
6. Confirm `https://<your-url>/health` returns `{"status": "running", ...}`.

### B. Get a dedicated WhatsApp Business sender

1. Put a fresh SIM in any phone. If the regular WhatsApp app is installed on that number, delete the account inside WhatsApp first (Settings → Account → Delete my account) — once Twilio registers it, the regular app cannot work on that number.
2. Set up **Meta Business Manager** at https://business.facebook.com — fill clinic name, address, GSTIN if any.
3. In Twilio Console → Messaging → **Senders** → WhatsApp → **Register a WhatsApp sender**:
   - Phone number: the dedicated SIM.
   - Display name: `MyphysioHealth Physio-Rehab Clinic`.
   - Category: Health.
4. Verify the OTP that Twilio sends to that number.
5. Wait for Meta approval (1–7 days). Status is visible in Twilio dashboard.
6. Once approved, Twilio gives you `whatsapp:+91XXXXXXXXXX`. Update `TWILIO_WHATSAPP_NUMBER` in Render env vars.
7. In Twilio Console → your sender → set **Webhook for incoming messages** to `https://<your-render-url>/webhook` (POST). Save.

### C. Cutover

1. Send a real WhatsApp message to the new number → confirm the bot replies.
2. Update the clinic's Google Business Profile, Google Ads, website, and printed material with the new WhatsApp number.
3. Set up a daily backup of `appointments.json` (download via Render shell or migrate to Postgres later).

## File Structure

```
WhatsApp Chat Bot/
├── app.py              # Main bot application
├── config.py           # Clinic details & configuration (EDIT THIS)
├── requirements.txt    # Python dependencies
├── .env.example        # Environment variable template
├── .env                # Your actual credentials (DO NOT SHARE)
├── appointments.json   # Auto-generated appointment storage
└── SETUP_GUIDE.md      # This file
```
