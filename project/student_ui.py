import os
from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user
from sqlalchemy import text
from datetime import date, timedelta
from project import db

student_ui = Blueprint("student_ui", __name__)

print("📁 student_ui.py loaded from:", os.path.abspath(__file__))
print("🚀 student_ui blueprint registered as 'student_ui'")


# ==========================================================
# TIME SLOT HELPER (IDs 1–9 → 08:00–17:00)
# ==========================================================
def get_timeslot_label(timeslot_id):
    """
    Map a timeslot_id (1..9) to a (start, end) time string.
    1 -> 08:00–09:00, 2 -> 09:00–10:00, ..., 9 -> 16:00–17:00
    """
    try:
        tid = int(timeslot_id)
    except (TypeError, ValueError):
        return None, None

    # 1 => 8, 2 => 9, ...
    hour = 8 + (tid - 1)
    if hour < 8 or hour > 16:
        return None, None

    start = f"{hour:02d}:00"
    end = f"{hour + 1:02d}:00"
    return start, end


# ==========================================================
# DASHBOARD
# ==========================================================
@student_ui.route("/dashboard")
@login_required
def student_dashboard():
    return render_template("student_dashboard.html")


# ==========================================================
# EXAM SCHEDULING (STEP 1: FORM + REVIEW PAGE)
# ==========================================================
@student_ui.route("/exams", methods=["GET", "POST"])
@login_required
def student_exams():
    print("🔥 student_exams() route hit")

    # 1) Locations
    locations = db.session.execute(text("""
        SELECT id, name
        FROM locations
        ORDER BY name
    """)).mappings().all()

    # 2) Exams (with capacity and seats used)
    raw = db.session.execute(text("""
        SELECT 
            e.id   AS exam_id,
            e.exam_type,
            e.exam_date,
            u.name AS professor_name,
            e.capacity,
            (
                SELECT COUNT(*)
                FROM registrations r
                WHERE r.exam_id = e.id
                  AND r.status = 'Active'
            ) AS used_seats
        FROM exams e
        JOIN professors p ON e.professor_id = p.id
        JOIN users u ON p.user_id = u.id
        ORDER BY e.exam_date ASC, u.name ASC
    """)).mappings().all()

    exams = [
        {
            "exam_id":       r["exam_id"],
            "exam_type":     r["exam_type"],
            "exam_date":     r["exam_date"].strftime("%Y-%m-%d"),
            "professor_name": r["professor_name"],
            "capacity":      r["capacity"],
            "used_seats":    r["used_seats"],
            "remaining":     r["capacity"] - r["used_seats"]
        }
        for r in raw
        if r["capacity"] - r["used_seats"] > 0
    ]

    # 3) Time slots (in-memory)
    timeslots = [
        {"id": i, "start_time": f"{h:02d}:00", "end_time": f"{h+1:02d}:00"}
        for i, h in enumerate(range(8, 17), start=1)
    ]

    # 4) Distinct exam dates for the calendar
    exam_dates = sorted({e["exam_date"] for e in exams})

    # ------------------------------------------------------
    # POST: Validate + go to review_before_confirm.html
    # ------------------------------------------------------
    if request.method == "POST":
        exam_id = request.form.get("exam_id")
        loc_id  = request.form.get("location_id")
        time_id = request.form.get("timeslot_id")

        # Basic validation
        if not (exam_id and loc_id and time_id):
            flash("Please complete all fields.", "error")
            return redirect(url_for("student_ui.student_exams"))

        # 1) Limit: max 3 active registrations
        active_count = db.session.execute(text("""
            SELECT COUNT(*)
            FROM registrations
            WHERE user_id = :u
              AND status = 'Active'
        """), {"u": current_user.id}).scalar()

        if active_count >= 3:
            flash("You cannot have more than 3 active appointments.", "error")
            return redirect(url_for("student_ui.student_exams"))

        # 2) Duplicate: same exam_id already active for this user
        duplicate = db.session.execute(text("""
            SELECT 1
            FROM registrations r
            WHERE r.user_id = :u
              AND r.status = 'Active'
              AND r.exam_id = :eid
        """), {"u": current_user.id, "eid": exam_id}).scalar()

        if duplicate:
            flash("You already registered for this exam.", "error")
            return redirect(url_for("student_ui.student_exams"))

        # 3) Load exam info for review page
        exam_info = db.session.execute(text("""
            SELECT 
                e.exam_type AS exam_title,
                e.exam_date,
                u.name      AS professor_name,
                l.name      AS location
            FROM exams e
            JOIN professors p ON e.professor_id = p.id
            JOIN users u      ON p.user_id = u.id
            LEFT JOIN locations l ON l.id = :loc
            WHERE e.id = :eid
        """), {"eid": exam_id, "loc": loc_id}).mappings().first()

        if not exam_info:
            flash("Could not load exam details.", "error")
            return redirect(url_for("student_ui.student_exams"))

        start_time, end_time = get_timeslot_label(time_id)

        info = {
            "exam_title":       exam_info["exam_title"],
            "exam_date":        exam_info["exam_date"],
            "professor_name":   exam_info["professor_name"],
            "location":         exam_info["location"],
            "start_time":       start_time,
            "end_time":         end_time,
            "selected_exam":    exam_id,
            "selected_loc":     loc_id,
            "selected_timeslot": time_id,
        }

        # Show the "Please confirm this info" page
        return render_template("review_before_confirm.html", info=info)

    # GET: Show the scheduling form
    return render_template(
        "schedule_exam.html",
        exams=exams,
        locations=locations,
        timeslots=timeslots,
        exam_dates=exam_dates,
        min_date=date.today().strftime("%Y-%m-%d"),
        max_date=(date.today() + timedelta(days=180)).strftime("%Y-%m-%d"),
    )


# ==========================================================
# STEP 2 – FINAL CONFIRM (INSERT + SUCCESS PAGE)
# ==========================================================
@student_ui.route("/confirm-final", methods=["POST"])
@login_required
def confirm_final():
    exam_id = request.form.get("exam_id")
    loc_id  = request.form.get("location_id")
    time_id = request.form.get("timeslot_id")

    if not (exam_id and loc_id and time_id):
        flash("Invalid confirmation data.", "error")
        return redirect(url_for("student_ui.student_exams"))

    # 1) Insert the registration
    db.session.execute(text("""
        INSERT INTO registrations
            (user_id, exam_id, timeslot_id, location_id, registration_date, status)
        VALUES
            (:u, :e, :t, :l, NOW(), 'Active')
    """), {
        "u": current_user.id,
        "e": exam_id,
        "t": time_id,
        "l": loc_id
    })
    db.session.commit()

    # 2) Get the most recent registration for this user (the one we just inserted)
    reg = db.session.execute(text("""
        SELECT
            r.id,
            r.registration_id,
            r.timeslot_id,
            e.exam_type AS exam_title,
            e.exam_date,
            u.name      AS professor_name,
            l.name      AS location
        FROM registrations r
        JOIN exams e      ON e.id = r.exam_id
        JOIN professors p ON e.professor_id = p.id
        JOIN users u      ON p.user_id = u.id
        JOIN locations l  ON l.id = r.location_id
        WHERE r.user_id = :u
        ORDER BY r.id DESC
        LIMIT 1
    """), {"u": current_user.id}).mappings().first()

    if not reg:
        flash("Registration saved, but could not load confirmation details.", "warning")
        return redirect(url_for("student_ui.student_dashboard"))

    # 3) Ensure we have a registration_id in format CSN###
    reg_id = reg["registration_id"]
    if not reg_id:  # if null or empty, generate
        reg_id = f"CSN{reg['id']:03d}"
        db.session.execute(text("""
            UPDATE registrations
            SET registration_id = :rid
            WHERE id = :id
        """), {"rid": reg_id, "id": reg["id"]})
        db.session.commit()

    # 4) Convert timeslot to human readable
    start_time, end_time = get_timeslot_label(reg["timeslot_id"])

    info = {
        "confirmation_code": reg_id,
        "exam_title":        reg["exam_title"],
        "exam_date":         reg["exam_date"],
        "professor_name":    reg["professor_name"],
        "location":          reg["location"],
        "start_time":        start_time,
        "end_time":          end_time,
    }

    # Final success page with confirmation code + details
    return render_template("confirm_success.html", info=info)


# ==========================================================
# MY APPOINTMENTS
# ==========================================================
@student_ui.route("/appointments")
@login_required
def student_appointments():
    try:
        rows = db.session.execute(text("""
            SELECT
                r.id            AS reg_id,
                r.registration_id AS confirmation_code,
                r.timeslot_id,
                e.exam_type,
                e.exam_date,
                l.name          AS location,
                r.status
            FROM registrations r
            JOIN exams e      ON e.id = r.exam_id
            LEFT JOIN locations l ON l.id = r.location_id
            WHERE r.user_id = :sid
            ORDER BY e.exam_date DESC
        """), {"sid": current_user.id}).mappings().all()

        # Attach readable time ranges
        for r in rows:
            if r["timeslot_id"]:
                start, end = get_timeslot_label(r["timeslot_id"])
                r["start_time"] = start
                r["end_time"] = end
            else:
                r["start_time"] = None
                r["end_time"] = None

        today = date.today()
        upcoming = [r for r in rows if r["exam_date"] >= today]
        past     = [r for r in rows if r["exam_date"] < today]

        return render_template("appointments.html", upcoming=upcoming, past=past)

    except Exception as e:
        print("❌ Error loading appointments:", e)
        return render_template("appointments.html", upcoming=[], past=[])
