"""
Clinic Configuration - UPDATE THESE WITH YOUR ACTUAL DETAILS
=============================================================
Replace all placeholder values below with your real clinic information.
"""

CLINIC = {
    "name": "MyphysioHealth Physio-Rehab Clinic",
    "tagline": "Your Trusted Physiotherapy & Rehabilitation Center in Delhi",
    "phone": "+91-9958400438",
    "email": "myphysioclinic01@gmail.com",
    "website": "",  # No separate website confirmed; Google Business Profile is used for ads/location
    "address": "Main Bus Stand, Opp. Aggarwal Sweets, Virendar Nagar, Block B, Sant Nagar, Burari, Delhi, 110084",
    "google_maps_link": "https://maps.app.goo.gl/dEdAqwfVi1kYu3tB9",
}

# Services offered. Pricing is intentionally assessment-based until final clinic rates are confirmed.
SERVICES = {
    "1": {
        "name": "Orthopedic Physiotherapy",
        "duration": "30-45 mins",
        "price": "Fee shared after assessment",
        "description": "Treatment for joint pain, fractures, arthritis, frozen shoulder, knee pain, and mobility issues."
    },
    "2": {
        "name": "Neuro Physiotherapy",
        "duration": "45-60 mins",
        "price": "Fee shared after assessment",
        "description": "Rehabilitation for stroke, paralysis, Parkinson's, spinal cord injury, balance issues, and nerve-related conditions."
    },
    "3": {
        "name": "Pediatric Physiotherapy",
        "duration": "45-60 mins",
        "price": "Fee shared after assessment",
        "description": "Therapy support for cerebral palsy, delayed milestones, posture issues, walking difficulties, and pediatric rehab needs."
    },
    "4": {
        "name": "Sports Injury Rehabilitation",
        "duration": "30-45 mins",
        "price": "Fee shared after assessment",
        "description": "Rehab for ligament injuries, ACL recovery, sprains, muscle strains, shoulder injuries, and return-to-sport recovery."
    },
    "5": {
        "name": "Back & Neck Pain Management",
        "duration": "30-45 mins",
        "price": "Fee shared after assessment",
        "description": "Treatment for cervical pain, lower back pain, sciatica, disc issues, posture problems, and chronic stiffness."
    },
    "6": {
        "name": "Post-Surgical Rehabilitation",
        "duration": "45-60 mins",
        "price": "Fee shared after assessment",
        "description": "Recovery programs after knee replacement, hip replacement, fracture surgery, spine surgery, and other procedures."
    },
    "7": {
        "name": "Chronic Pain Management",
        "duration": "30-45 mins",
        "price": "Fee shared after assessment",
        "description": "Personalized physiotherapy for long-term pain, recurring stiffness, muscular pain, and lifestyle-related pain conditions."
    },
    "8": {
        "name": "Dry Needling / Cupping Therapy",
        "duration": "30 mins",
        "price": "Fee shared after assessment",
        "description": "Advanced pain-relief techniques for muscle tightness, trigger points, stiffness, and sports recovery."
    },
    "9": {
        "name": "Online Physiotherapy Consultation",
        "duration": "30 mins",
        "price": "Fee shared after assessment",
        "description": "Video consultation for exercise guidance, pain management, posture correction, and follow-up rehab support."
    },
}
# Weekly schedule (True = open, False = closed)
TIMINGS = {
    "Monday":    {"open": True, "hours": "9:00 AM - 7:00 PM (Lunch: 1:00 - 2:00 PM)"},
    "Tuesday":   {"open": True, "hours": "9:00 AM - 7:00 PM (Lunch: 1:00 - 2:00 PM)"},
    "Wednesday": {"open": True, "hours": "9:00 AM - 7:00 PM (Lunch: 1:00 - 2:00 PM)"},
    "Thursday":  {"open": True, "hours": "9:00 AM - 7:00 PM (Lunch: 1:00 - 2:00 PM)"},
    "Friday":    {"open": True, "hours": "9:00 AM - 7:00 PM (Lunch: 1:00 - 2:00 PM)"},
    "Saturday":  {"open": True, "hours": "9:00 AM - 7:00 PM (Lunch: 1:00 - 2:00 PM)"},
    "Sunday":    {"open": False, "hours": "Closed"},
}

# Available appointment slots (24hr, 30-min sessions). Lunch break 13:00–14:00.
APPOINTMENT_SLOTS = [
    "09:00", "09:30",
    "10:00", "10:30", "11:00", "11:30", "12:00", "12:30",
    "14:00", "14:30", "15:00", "15:30", "16:00", "16:30",
    "17:00", "17:30", "18:00", "18:30",
]

# Saturday uses the same schedule
SATURDAY_SLOTS = [
    "09:00", "09:30",
    "10:00", "10:30", "11:00", "11:30", "12:00", "12:30",
    "14:00", "14:30", "15:00", "15:30", "16:00", "16:30",
    "17:00", "17:30", "18:00", "18:30",
]

# FAQs
FAQS = {
    "1": {
        "question": "Do I need a doctor's referral?",
        "answer": "No, you can directly book an appointment with us. However, if you have any medical reports or prescriptions, please bring them along.",
    },
    "2": {
        "question": "What should I wear to my session?",
        "answer": "Please wear comfortable, loose-fitting clothes that allow easy movement. Avoid jeans or tight clothing.",
    },
    "3": {
        "question": "How many sessions will I need?",
        "answer": "It depends on your condition. After the initial assessment, your physiotherapist will create a personalized treatment plan with an estimated number of sessions.",
    },
    "4": {
        "question": "Do you offer home visits?",
        "answer": "Yes! We offer home visit physiotherapy sessions at an additional charge. Please call us to schedule a home visit.",
    },
    "5": {
        "question": "What payment methods do you accept?",
        "answer": "We accept cash, UPI (GPay/PhonePe/Paytm), credit/debit cards, and net banking.",
    },
    "6": {
        "question": "Is physiotherapy painful?",
        "answer": "Most treatments are not painful. You may feel mild discomfort during certain techniques, but your therapist will always work within your comfort level.",
    },
}

# Exercise tips for common conditions (sent as follow-up messages)
EXERCISE_TIPS = {
    "back_pain": {
        "title": "🏋️ Daily Exercises for Back Pain",
        "exercises": [
            "1. *Cat-Cow Stretch* - 10 reps, 2 sets\n   Get on all fours, arch your back up (cat), then dip it down (cow).",
            "2. *Knee-to-Chest Stretch* - Hold 20 sec each side\n   Lie on your back, pull one knee to your chest gently.",
            "3. *Bird-Dog Exercise* - 10 reps each side\n   On all fours, extend opposite arm and leg simultaneously.",
            "4. *Pelvic Tilts* - 15 reps, 2 sets\n   Lie on back with knees bent, flatten your back against the floor.",
        ],
    },
    "neck_pain": {
        "title": "🏋️ Daily Exercises for Neck Pain",
        "exercises": [
            "1. *Chin Tucks* - 10 reps, 3 sets\n   Pull your chin straight back (make a double chin), hold 5 seconds.",
            "2. *Neck Side Stretch* - Hold 20 sec each side\n   Tilt ear toward shoulder, use hand for gentle pressure.",
            "3. *Shoulder Shrugs* - 15 reps, 2 sets\n   Raise shoulders toward ears, hold 3 sec, release.",
            "4. *Neck Rotations* - 10 reps each direction\n   Slowly turn head left to right, keeping shoulders still.",
        ],
    },
    "knee_pain": {
        "title": "🏋️ Daily Exercises for Knee Pain",
        "exercises": [
            "1. *Straight Leg Raises* - 10 reps each leg, 3 sets\n   Lie on back, keep one leg bent, raise the other slowly.",
            "2. *Wall Sits* - Hold 15-30 seconds, 3 sets\n   Lean against wall, slide down until knees are at 90°.",
            "3. *Step-Ups* - 10 reps each leg\n   Step up onto a low stair, then step down slowly.",
            "4. *Hamstring Curls* - 10 reps each leg, 2 sets\n   Stand holding a chair, curl one heel toward your buttock.",
        ],
    },
}
