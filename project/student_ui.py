# project/student_ui.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from sqlalchemy import text
from project import db
import random


student_ui = Blueprint("student_ui", __name__)

@student_ui.route('/student_dashboard')
@login_required
def student_dashboard():
    return render_template("student_dashboard.html")

@student_ui.route("/student/exams", methods=["GET"])
@login_required
def student_exams():
    rows = db.session.execute(text("""
        SELECT
            e.id AS exam_id,
            e.exam_type AS course,
            e.exam_date AS date,
            e.exam_time AS time,                -- if you added this column; otherwise use NULL
            l.name AS location,
            e.capacity,
            IFNULL(SUM(CASE WHEN r.status = 'Active' THEN 1 ELSE 0 END), 0) AS booked_count,
            GREATEST(e.capacity - IFNULL(SUM(CASE WHEN r.status = 'Active' THEN 1 ELSE 0 END), 0), 0) AS remaining
        FROM Exams e
        LEFT JOIN Locations l    ON l.id = e.location_id                           
        LEFT JOIN Registrations r ON r.exam_id = e.id
        WHERE e.exam_date >= CURDATE()
        GROUP BY e.id, e.exam_type, e.exam_date, e.exam_time, l.name, e.capacity
        ORDER BY e.exam_date, e.exam_time, e.exam_type
    """)).mappings().all()

    exams = [dict(r) for r in rows]

    return render_template("schedule_exam.html", exams=exams)


@student_ui.route("/student/appointments", methods=["GET"])
@login_required
def student_appointments():
    q      = (request.args.get("q") or "").strip()
    start  = (request.args.get("start") or "").strip()  # YYYY-MM-DD
    end    = (request.args.get("end") or "").strip()    # YYYY-MM-DD

    sql = """
        SELECT
            r.id                     AS reg_id,
            r.registration_id        AS confirmation_code,
            r.status                 AS status,
            e.id                     AS exam_id,
            e.exam_type              AS exam_type,
            e.exam_date              AS exam_date,
            e.exam_time              AS exam_time,
            c.course_code            AS course_code,
            l.name                   AS location
        FROM Registrations r
        JOIN Exams       e ON e.id  = r.exam_id
        JOIN Courses     c ON c.id  = e.course_id
        LEFT JOIN Locations l ON l.id = e.location_id
        WHERE r.user_id = :sid
          /* optional filters */
          {name_filter}
          {start_filter}
          {end_filter}
        ORDER BY e.exam_date DESC, e.exam_time DESC, c.course_code
    """

    name_filter = ""
    start_filter = ""
    end_filter = ""
    params = {"sid": current_user.id}

    if q:
        name_filter = "AND (c.course_code LIKE :like OR e.exam_type LIKE :like)"
        params["like"] = f"%{q}%"

    if start:
        start_filter = "AND e.exam_date >= :start"
        params["start"] = start

    if end:
        end_filter = "AND e.exam_date <= :end"
        params["end"] = end

    sql = sql.format(
        name_filter=name_filter,
        start_filter=start_filter,
        end_filter=end_filter
    )

    rows = db.session.execute(text(sql), params).mappings().all()
    bookings = [dict(r) for r in rows]

    # Split upcoming vs past (handy for headings in the template)
    upcoming = [b for b in bookings if str(b["exam_date"]) >= str(db.session.execute(text("SELECT CURDATE()")).scalar())]
    past     = [b for b in bookings if str(b["exam_date"]) <  str(db.session.execute(text("SELECT CURDATE()")).scalar())]

    return render_template("appointments.html",
                           bookings=bookings,
                           upcoming=upcoming,
                           past=past,
                           q=q, start=start, end=end)


# ==========================================================
#  ELLY UPDATE 11-5-2025
# --------------------------
# Validation / helper fns
# --------------------------
def has_reached_limit(student_id: int) -> bool:
    q = text("""
        SELECT COUNT(*) AS cnt
        FROM Registrations
        WHERE user_id = :sid
          AND status = 'Active'
    """)
    cnt = db.session.execute(q, {"sid": student_id}).scalar() or 0
    return cnt >= 3

def already_registered(student_id: int, exam_id: int) -> bool:
    q = text("""
        SELECT 1
        FROM Registrations
        WHERE user_id = :sid
          AND exam_id = :eid
          AND status = 'Active'
        LIMIT 1
    """)
    row = db.session.execute(q, {"sid": student_id, "eid": exam_id}).first()
    return row is not None

def exam_availability_snapshot():
    """Return list of dicts: {exam_id, capacity, booked_count, remaining}"""
    rows = db.session.execute(text("""
        SELECT
            e.id AS exam_id,
            e.capacity,
            IFNULL(SUM(CASE WHEN r.status='Active' THEN 1 ELSE 0 END), 0) AS booked_count,
            GREATEST(e.capacity - IFNULL(SUM(CASE WHEN r.status='Active' THEN 1 ELSE 0 END), 0), 0) AS remaining
        FROM Exams e
        LEFT JOIN Registrations r ON r.exam_id = e.id
        GROUP BY e.id, e.capacity
        ORDER BY e.id
    """)).mappings().all()
    return [dict(r) for r in rows]


@student_ui.route("/student/register_exam", methods=["POST"])
@login_required
def register_exam():   ##  confirm
    payload = request.get_json(silent=True) if request.is_json else request.form
    exam_id = payload.get("exam_id")

    try:
        exam_id = int(exam_id)
    except (TypeError, ValueError):
        msg = "Missing or invalid exam_id."
        return (jsonify({"ok": False, "error": msg}), 400) if request.is_json else (
            flash(msg, "error") or redirect(url_for("student_ui.student_appointments"))
        )

    sid = int(current_user.id)

    # fast-fails (rechecked in txn)
    if has_reached_limit(sid):
        msg = "You already have 3 active registrations."
        return (jsonify({"ok": False, "error": msg}), 400) if request.is_json else (
            flash(msg, "error") or redirect(url_for("student_ui.student_appointments"))
        )
    if already_registered(sid, exam_id):
        msg = "You are already registered for this exam."
        return (jsonify({"ok": False, "error": msg}), 400) if request.is_json else (
            flash(msg, "error") or redirect(url_for("student_ui.student_appointments"))
        )

    try:
        with db.session.begin():
            # lock target exam
            exam = db.session.execute(text("""
                SELECT id, capacity
                FROM Exams
                WHERE id = :eid
                FOR UPDATE
            """), {"eid": exam_id}).first()
            if not exam:
                msg = "Exam not found."
                return (jsonify({"ok": False, "error": msg}), 404) if request.is_json else (
                    flash(msg, "error") or redirect(url_for("student_ui.student_appointments"))
                )

            # re-check limits inside txn
            if has_reached_limit(sid):
                msg = "You already have 3 active registrations."
                return (jsonify({"ok": False, "error": msg}), 400) if request.is_json else (
                    flash(msg, "error") or redirect(url_for("student_ui.student_appointments"))
                )
            if already_registered(sid, exam_id):
                msg = "You are already registered for this exam."
                return (jsonify({"ok": False, "error": msg}), 400) if request.is_json else (
                    flash(msg, "error") or redirect(url_for("student_ui.student_appointments"))
                )

            # capacity guard using live count of Active regs (row-locked)
            active = db.session.execute(text("""
                SELECT COUNT(*) FROM Registrations
                WHERE exam_id = :eid AND status = 'Active'
                FOR UPDATE
            """), {"eid": exam_id}).scalar() or 0

            if int(active) >= int(exam.capacity):
                msg = "This session is full."
                return (jsonify({"ok": False, "error": msg}), 409) if request.is_json else (
                    flash(msg, "error") or redirect(url_for("student_ui.student_appointments"))
                )

            # insert registration with CSN code
            # suffix = (exam_id + random.randint(100, 999)) % 1000
            # confirmation_code = f"CSN{suffix:03d}"

            db.session.execute(text("""
                INSERT INTO Registrations
                    (registration_id, exam_id, user_id, registration_date, status)
                VALUES
                    (NULL, :eid, :sid, NOW(), 'Active')
            """), {"eid": exam_id, "sid": sid})

            new_id = db.session.execute(text("SELECT LAST_INSERT_ID()")).scalar()
            confirmation_code = db.session.execute(text("""
                SELECT registration_id
                FROM Registrations
                WHERE id = :rid
            """), {"rid": new_id}).scalar()

        # JSON → include Location header
        if request.is_json:
            resp = jsonify({"ok": True, "exam_id": exam_id, "confirmation_code": confirmation_code})
            resp.status_code = 201
            resp.headers["Location"] = url_for("student_ui.confirm_page", code=confirmation_code)
            return resp

        # HTML → redirect straight to confirmation page
        return redirect(url_for("student_ui.confirm_page", code=confirmation_code))

    except Exception as e:
        db.session.rollback()
        print("Register Error:", e)
        err = "Registration failed. Please try again."
        return (jsonify({"ok": False, "error": err}), 500) if request.is_json else (
            flash(err, "error") or redirect(url_for("student_ui.student_appointments"))
        )

    

@student_ui.route("/student/cancel_exam/<int:exam_id>", methods=["POST"])
@login_required
def cancel_exam(exam_id):
    try:
        with db.session.begin():
            cancel_q = text("""
                UPDATE Registrations
                SET status = 'Canceled'
                WHERE exam_id = :eid AND user_id = :sid
                  AND status = 'Active'
            """)
            changed = db.session.execute(cancel_q, {
                "eid": exam_id,
                "sid": current_user.id
            }).rowcount
        if request.is_json:
            return jsonify({"ok": True, "changed": changed}), 200
        flash("Exam cancelled successfully!", "success")
    except Exception as e:
        db.session.rollback()
        print("Cancel Error:", e)
        if request.is_json:
            return jsonify({"ok": False, "error": "Error cancelling exam."}), 500
        flash("Error cancelling exam. Please try again.", "error")
    return redirect(url_for("student_ui.student_appointments"))

@student_ui.route("/student/confirm/<code>", methods=["GET"])
@login_required
def confirm_page(code):
    row = db.session.execute(text("""
        SELECT r.registration_id AS confirmation_code,
               e.id AS exam_id,
               e.exam_type AS exam_title,
               e.exam_date AS exam_date,
               e.exam_time AS exam_time,
               CONCAT('Loc #', e.location_id) AS exam_location
        FROM Registrations r
        JOIN Exams e ON e.id = r.exam_id
        WHERE r.user_id = :sid AND r.registration_id = :code
    """), {"sid": current_user.id, "code": code}).first()
    if not row:
        flash("Confirmation not found.", "error")
        return redirect(url_for("student_ui.student_appointments"))
    return render_template("confirm.html", info=row)

@student_ui.route("/student/reschedule", methods=["POST"])
@login_required
def reschedule_exam():
    payload = request.get_json(silent=True) if request.is_json else request.form
    reg_id      = payload.get("registration_id")
    new_exam_id = payload.get("exam_id")

    try:
        reg_id = int(reg_id); new_exam_id = int(new_exam_id)
    except (TypeError, ValueError):
        msg = "Invalid registration or exam id."
        return (jsonify({"ok": False, "error": msg}), 400) if request.is_json else (
            flash(msg, "error") or redirect(url_for("student_ui.student_appointments"))
        )

    try:
        with db.session.begin():
            reg = db.session.execute(text("""
                SELECT id, exam_id
                FROM Registrations
                WHERE id = :rid AND user_id = :sid AND status = 'Active'
                FOR UPDATE
            """), {"rid": reg_id, "sid": current_user.id}).first()
            if not reg:
                msg = "Active registration not found."
                return (jsonify({"ok": False, "error": msg}), 404) if request.is_json else (
                    flash(msg, "error") or redirect(url_for("student_ui.student_appointments"))
                )

            old_exam_id = int(reg.exam_id)
            if old_exam_id == new_exam_id:
                if request.is_json:
                    return jsonify({"ok": True, "message": "No change."}), 200
                flash("No change to session.", "info")
                return redirect(url_for("student_ui.student_appointments"))

            # lock both exams in stable order
            first_id, second_id = sorted([old_exam_id, new_exam_id])
            exams = db.session.execute(text("""
                SELECT id, capacity
                FROM Exams
                WHERE id IN (:a, :b)
                FOR UPDATE
            """), {"a": first_id, "b": second_id}).fetchall()
            have = {int(x.id): int(x.capacity) for x in exams}
            if new_exam_id not in have or old_exam_id not in have:
                msg = "Exam session not found."
                return (jsonify({"ok": False, "error": msg}), 404) if request.is_json else (
                    flash(msg, "error") or redirect(url_for("student_ui.student_appointments"))
                )

            # capacity guard on target
            active = db.session.execute(text("""
                SELECT COUNT(*) FROM Registrations
                WHERE exam_id = :eid AND status = 'Active'
                FOR UPDATE
            """), {"eid": new_exam_id}).scalar() or 0
            if int(active) >= have[new_exam_id]:
                msg = "Target session is full."
                return (jsonify({"ok": False, "error": msg}), 409) if request.is_json else (
                    flash(msg, "error") or redirect(url_for("student_ui.student_appointments"))
                )

            # move the registration
            db.session.execute(text("""
                UPDATE Registrations
                SET exam_id = :new_eid
                WHERE id = :rid
            """), {"new_eid": new_exam_id, "rid": reg_id})

        if request.is_json:
            return jsonify({"ok": True}), 200
        flash("Rescheduled successfully.", "success")
        return redirect(url_for("student_ui.student_appointments"))

    except Exception as e:
        db.session.rollback()
        print("Reschedule Error:", e)
        msg = "Reschedule failed. Please try again."
        return (jsonify({"ok": False, "error": msg}), 500) if request.is_json else (
            flash(msg, "error") or redirect(url_for("student_ui.student_appointments"))
        )


@student_ui.route("/api/exams/availability", methods=["GET"])
@login_required
def api_exam_availability():
    rows = db.session.execute(text("""
        SELECT
            e.id AS exam_id,
            GREATEST(
                e.capacity - IFNULL(SUM(CASE WHEN r.status='Active' THEN 1 ELSE 0 END), 0),
                0
            ) AS remaining
        FROM Exams e
        LEFT JOIN Registrations r ON r.exam_id = e.id
        WHERE e.exam_date >= CURDATE()
        GROUP BY e.id, e.capacity
    """)).mappings().all()
    return jsonify({"ok": True, "exams": [dict(r) for r in rows]})

@student_ui.route("/student/register_review/<int:exam_id>", methods=["GET"])
@login_required
def register_review(exam_id):
    exam = db.session.execute(text("""
        SELECT e.id AS exam_id, e.exam_type, e.exam_date, e.exam_time,
               l.name AS location, c.course_code, c.course_name
        FROM Exams e
        JOIN Courses c   ON c.id = e.course_id
        LEFT JOIN Locations l ON l.id = e.location_id
        WHERE e.id = :eid
    """), {"eid": exam_id}).mappings().first()

    if not exam:
        flash("Exam not found.", "error")
        return redirect(url_for("student_ui.student_exams"))

    return render_template("register_review.html", exam=exam)


# ==========================================================
# TEMPORARY DEMO / PREVIEW ROUTE
# This route is ONLY for letting Melissa test the prefilled
# student info panel BEFORE the registration form is finished.
#
# When the teammate creates the real registration page, they
# will simply include:
#
#     {% include 'partials/student_prefill_form.html' %}
#
# inside the actual registration form.
# ==========================================================
@student_ui.route("/student/prefill-test", methods=["GET"])
@login_required
def student_prefill_test():
    return render_template("partials/student_prefill_form.html")
