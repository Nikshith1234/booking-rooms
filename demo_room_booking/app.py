import random
import os
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session, flash
from pymongo import MongoClient
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "demo_secret_key_2024")

# Fixed credentials
USERNAME = "bookingbot"
PASSWORD = "password123"

# Available rooms
ROOMS = ["101", "102", "201", "202", "204", "305"]

# ── MongoDB Connection ──────────────────────────────────────────────────────────
MONGO_URI = os.getenv("MONGO_URI")
client = MongoClient(MONGO_URI)
db = client["room_booking"]
bookings_col = db["bookings"]
# ───────────────────────────────────────────────────────────────────────────────


def generate_booking_id():
    number = random.randint(1000, 9999)
    return f"RB-{number}"


def check_overlap(room_number, date, start_time, end_time):
    """Check if there is an overlapping booking for the same room and date."""
    existing = bookings_col.find({"room_number": room_number, "date": date})
    for booking in existing:
        existing_start = booking["start_time"]
        existing_end = booking["end_time"]
        # Overlap: new starts before existing ends AND new ends after existing starts
        if start_time < existing_end and end_time > existing_start:
            return True
    return False


@app.route("/")
def index():
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        if username == USERNAME and password == PASSWORD:
            session["logged_in"] = True
            session["username"] = username
            return redirect(url_for("dashboard"))
        else:
            flash("Invalid username or password. Please try again.")
    return render_template("login.html")


@app.route("/dashboard")
def dashboard():
    if not session.get("logged_in"):
        return redirect(url_for("login"))
    return render_template("dashboard.html", rooms=ROOMS)


@app.route("/booking", methods=["GET", "POST"])
def booking():
    if not session.get("logged_in"):
        return redirect(url_for("login"))

    if request.method == "POST":
        room_number = request.form.get("room_number", "")
        date = request.form.get("date", "")
        start_time = request.form.get("start_time", "")
        end_time = request.form.get("end_time", "")
        num_people = request.form.get("num_people", "")

        # Basic validation
        if not all([room_number, date, start_time, end_time, num_people]):
            flash("All fields are required.")
            return render_template("booking.html", rooms=ROOMS)

        if start_time >= end_time:
            flash("End time must be after start time.")
            return render_template("booking.html", rooms=ROOMS)

        # Check for overlapping bookings
        if check_overlap(room_number, date, start_time, end_time):
            flash(
                f"Room {room_number} is already booked for the selected time slot. "
                "Please choose a different time."
            )
            return render_template("booking.html", rooms=ROOMS)

        # Generate booking ID and save to MongoDB
        booking_id = generate_booking_id()
        created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        bookings_col.insert_one({
            "room_number": room_number,
            "date": date,
            "start_time": start_time,
            "end_time": end_time,
            "num_people": int(num_people),
            "booking_id": booking_id,
            "created_at": created_at,
        })

        return redirect(url_for("confirmation",
                                booking_id=booking_id,
                                room_number=room_number,
                                date=date,
                                start_time=start_time,
                                end_time=end_time,
                                num_people=num_people))

    return render_template("booking.html", rooms=ROOMS)


@app.route("/confirmation")
def confirmation():
    if not session.get("logged_in"):
        return redirect(url_for("login"))

    booking_id = request.args.get("booking_id", "")
    room_number = request.args.get("room_number", "")
    date = request.args.get("date", "")
    start_time = request.args.get("start_time", "")
    end_time = request.args.get("end_time", "")
    num_people = request.args.get("num_people", "")

    return render_template("confirmation.html",
                           booking_id=booking_id,
                           room_number=room_number,
                           date=date,
                           start_time=start_time,
                           end_time=end_time,
                           num_people=num_people)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
