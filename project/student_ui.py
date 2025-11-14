import os
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from sqlalchemy import text
from datetime import date, timedelta
from project import db
print("📁 student_ui.py loaded from:", os.path.abspath(__file__))


student_ui = Blueprint("student_ui", __name__)
print("🚀 student_ui.py LOADED!")


# ==========================================================
# DASHBOARD
# ==========================================================
@student_ui.route('/student_dashboard')
@login_required
def student_dashboard():
    return render_template("student_dashboard.html")


# ==========================================================
# EXAM SCHEDULING PAGE
# ==========================================================
@student_ui.route("/student/exams", methods=["GET", "POST"])
@login_required
def student_exams():
    print("🔥 student_exams() route hit")

    try:
        # -------------------------------------------------------
        # LOAD LOCATIONS (correct MySQL table name: locations)
        # -------------------------------------------------------
        locations = db.session.execute(text("""
            SELECT id, name
            FROM locations
            ORDER BY name
        """)).mappings().all()

        # -------------------------------------------------------
        # LOAD EXAMS (correct table name: exams)
        # -------------------------------------------------------
        exams = db.session.execute(text("""
            SELECT
                e.id AS exam_id,
                e.exam_type,
                e.exam_date,
                e.exam_date AS formatted_date,
                COALESCE(u.name, 'Unknown') AS professor_name
            FROM exams e
            LEFT JOIN users u ON e.professor_id = u.id
            ORDER BY e.exam_date ASC, professor_name ASC
        """)).mappings().all()

        # -------------------------------------------------------
        # TIME SLOTS (you manually define them – no DB needed)
        # -------------------------------------------------------
        timeslots = [
            {"id": i, "start_time": f"{hour:02d}:00", "end_time": f"{hour+1:02d}:00"}
            for i, hour in enumerate(range(8, 17), start=1)
        ]

        # -------------------------------------------------------
        # DATE LIMITS (today through +180 days)
        # -------------------------------------------------------
        today = date.today()
        min_date = today.strftime("%Y-%m-%d")
        max_date = (today + timedelta(days=180)).strftime("%Y-%m-%d")

        # List of dates that have exams
        exam_dates = [str(e.exam_date) for e in exams] if exams else []

        # -------------------------------------------------------
        # HANDLE FORM SUBMISSION (student registering for exam)
        # -------------------------------------------------------
        if request.method == "POST":
            exam_id = request.form.get("exam_id")
            location_id = request.form.get("location_id")
            timeslot_id = request.form.get("timeslot_id")
            exam_date_val = request.form.get("exam_date")

            # Limit: max 3 active registrations per student
            booked_count = db.session.execute(text("""
                SELECT COUNT(*)
                FROM registrations
                WHERE user_id = :sid AND status = 'Active'
            """), {"sid": current_user.id}).scalar() or 0

            if booked_count >= 3:
                flash("You have reached the maximum of 3 active exam registrations.", "error")
            else:
                # Prevent duplicate exam type for same user
                duplicate = db.session.execute(text("""
                    SELECT 1
                    FROM registrations r
                    JOIN exams e ON r.exam_id = e.id
                    WHERE r.user_id = :sid
                      AND r.status = 'Active'
                      AND e.exam_type = (SELECT exam_type FROM exams WHERE id = :eid)
                    LIMIT 1
                """), {"sid": current_user.id, "eid": exam_id}).scalar()

                if duplicate:
                    flash("You are already registered for this exam type.", "error")
                else:
                    # INSERT REGISTRATION (correct table name: registrations)
                    db.session.execute(text("""
                        INSERT INTO registrations (user_id, exam_id, timeslot_id, location_id, registration_date, status)
                        VALUES (:sid, :eid, :tid, :lid, NOW(), 'Active')
                    """), {
                        "sid": current_user.id,
                        "eid": exam_id,
                        "tid": timeslot_id,
                        "lid": location_id,
                    })
                    db.session.commit()

                    flash("Exam successfully registered!", "success")

        # -------------------------------------------------------
        # DEBUG PRINTS
        # -------------------------------------------------------
        print("🟣 DEBUG: Locations:", [l.name for l in locations])
        print("🟣 DEBUG: Exams:", [e.exam_type for e in exams])
        print("🟣 DEBUG: Timeslots:", [t["start_time"] for t in timeslots])

        # -------------------------------------------------------
        # RENDER TEMPLATE WITH DATA
        # -------------------------------------------------------
        return render_template(
            "schedule_exam.html",
            exams=exams,
            locations=locations,
            timeslots=timeslots,
            min_date=min_date,
            max_date=max_date,
            exam_dates=exam_dates
        )

    except Exception as e:
        print("❌ Error loading exam page:", e)

        return render_template(
            "schedule_exam.html",
            exams=[],
            locations=[],
            timeslots=[],
            min_date=None,
            max_date=None,
            exam_dates=[]
        )

# ==========================================================
#  MY APPOINTMENTS (CURRENT & PAST)
# ==========================================================
@student_ui.route("/student/appointments", methods=["GET"])
@login_required
def student_appointments():
    try:
        rows = db.session.execute(text("""
            SELECT
                r.id AS reg_id,
                r.registration_id AS confirmation_code,
                e.exam_type AS exam_type,
                e.exam_date AS exam_date,
                e.exam_time AS exam_time,
                e.id AS exam_id,
                l.name AS location,
                r.status AS status
            FROM Registrations r
            JOIN Exams e ON e.id = r.exam_id
            LEFT JOIN Locations l ON e.location_id = l.id
            WHERE r.user_id = :sid
            ORDER BY e.exam_date DESC, e.exam_time DESC
        """), {"sid": current_user.id}).mappings().all()

        today = db.session.execute(text("SELECT CURDATE()")).scalar()
        upcoming = [b for b in rows if str(b["exam_date"]) >= str(today)]
        past     = [b for b in rows if str(b["exam_date"]) <  str(today)]

        return render_template("appointments.html", upcoming=upcoming, past=past)

    except Exception as e:
        print("Error loading appointments:", e)
        flash("Error loading appointments.", "error")
        return render_template("appointments.html", upcoming=[], past=[])

@student_ui.route("/student/test")
def student_test():
    print("✅ Test route hit!")
    return "Student UI blueprint works!"
