import os
from flask import Blueprint, render_template, request, flash
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
@student_ui.route('/dashboard')
@login_required
def student_dashboard():
    return render_template("student_dashboard.html")


# ==========================================================
# EXAM SCHEDULING PAGE
# ==========================================================
@student_ui.route("/exams", methods=["GET", "POST"])
@login_required
def student_exams():
    print("🔥 student_exams() route hit")

    try:
        # 1) LOCATIONS
        locations = db.session.execute(text("""
            SELECT id, name
            FROM locations
            ORDER BY name
        """)).mappings().all()

        # 2) EXAMS (faculty only)
        raw = db.session.execute(text("""
            SELECT 
                e.id AS exam_id,
                e.exam_type,
                e.exam_date,
                u.name AS professor_name,
                e.capacity,
                (
                    SELECT COUNT(*) 
                    FROM registrations r 
                    WHERE r.exam_id = e.id AND r.status = 'Active'
                ) AS used_seats
            FROM exams e
            JOIN professors p ON e.professor_id = p.id
            JOIN users u ON p.user_id = u.id
            WHERE e.capacity > (
                SELECT COUNT(*)
                FROM registrations r
                WHERE r.exam_id = e.id AND r.status = 'Active'
            )
            ORDER BY e.exam_date ASC, u.name ASC
        """)).mappings().all()


        exams = [
            {
                "exam_id": r["exam_id"],
                "exam_type": r["exam_type"],
                "exam_date": r["exam_date"].strftime("%Y-%m-%d"),
                "professor_name": r["professor_name"],
                "capacity": r["capacity"],
                "used_seats": r["used_seats"],
                "remaining": r["capacity"] - r["used_seats"]
            }
            for r in raw
            if r["capacity"] - r["used_seats"] > 0   # ⭐ hides full exams
        ]


        # 3) TIME SLOTS (8–5)
        timeslots = [
            {"id": i, "start_time": f"{h:02d}:00", "end_time": f"{h+1:02d}:00"}
            for i, h in enumerate(range(8, 17), start=1)
        ]

        # 4) DISTINCT exam dates
        exam_dates = sorted({e["exam_date"] for e in exams})

        # 5) FORM SUBMISSION
        if request.method == "POST":
            exam_id = request.form.get("exam_id")
            loc_id = request.form.get("location_id")
            time_id = request.form.get("timeslot_id")

            if not exam_id or not loc_id or not time_id:
                flash("Please complete all fields.", "error")
            else:
                # limit: 3 active
                count = db.session.execute(text("""
                    SELECT COUNT(*)
                    FROM registrations
                    WHERE user_id = :u AND status = 'Active'
                """), {"u": current_user.id}).scalar()

                if count >= 3:
                    flash("You cannot have more than 3 active registrations.", "error")
                else:
                    # prevent duplicates (same type/date/professor)
                    dup = db.session.execute(text("""
                        SELECT 1
                        FROM registrations r
                        JOIN exams e ON r.exam_id = e.id
                        WHERE r.user_id = :u
                          AND r.status = 'Active'
                          AND e.exam_type = (SELECT exam_type FROM exams WHERE id = :eid)
                          AND e.exam_date = (SELECT exam_date FROM exams WHERE id = :eid)
                          AND e.professor_id = (SELECT professor_id FROM exams WHERE id = :eid)
                    """), {"u": current_user.id, "eid": exam_id}).scalar()

                    if dup:
                        flash("You already registered for this exam.", "error")
                    else:
                        db.session.execute(text("""
                            INSERT INTO registrations
                            (user_id, exam_id, timeslot_id, location_id, registration_date, status)
                            VALUES (:u, :e, :t, :l, NOW(), 'Active')
                        """), {
                            "u": current_user.id,
                            "e": exam_id,
                            "t": time_id,
                            "l": loc_id
                        })
                        db.session.commit()
                        flash("Exam successfully registered!", "success")
        # ============================
        # DEBUG — VERIFY RAW VALUES
        # ============================
        print("🔥 EXAMS LIST:", exams)
        print("🔥 FINAL exam_dates SENT TO TEMPLATE:", exam_dates)
        return render_template(
            "schedule_exam.html",
            exams=exams,
            locations=locations,
            timeslots=timeslots,
            exam_dates=exam_dates,
            min_date=date.today().strftime("%Y-%m-%d"),
            max_date=(date.today() + timedelta(days=180)).strftime("%Y-%m-%d")
        )

    except Exception as e:
        print("❌ Error:", e)
        flash("Error loading exam page.", "error")
        return render_template(
            "schedule_exam.html",
            exams=[],
            locations=[],
            timeslots=[],
            exam_dates=[]
        )

# ==========================================================
#  MY APPOINTMENTS
# ==========================================================
@student_ui.route("/appointments")
@login_required
def student_appointments():
    try:
        rows = db.session.execute(text("""
            SELECT
                r.id AS reg_id,
                r.registration_id AS confirmation_code,
                e.exam_type,
                e.exam_date,
                e.exam_time,
                l.name AS location,
                r.status
            FROM registrations r
            JOIN exams e ON e.id = r.exam_id
            LEFT JOIN locations l ON l.id = e.location_id
            WHERE r.user_id = :sid
            ORDER BY e.exam_date DESC
        """), {"sid": current_user.id}).mappings().all()

        today = date.today()
        upcoming = [r for r in rows if r["exam_date"] >= today]
        past     = [r for r in rows if r["exam_date"] < today]

        print("👉 Registered: student_appointments route")

        return render_template("appointments.html", upcoming=upcoming, past=past)

    except Exception as e:
        print("❌ Error loading appointments:", e)
        return render_template("appointments.html", upcoming=[], past=[])
