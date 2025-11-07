# project/student_exam_routes.py
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from . import db
from sqlalchemy import text

# Blueprint for exam actions (kept separate from student_ui)
student_exam_bp = Blueprint("student_exam_bp", __name__)

# ==========================
# VIEW EXAMS
# ==========================
@student_exam_bp.route("/student/exams", methods=["GET"])
@login_required
def student_exams():
    """Display list of exams available for the student."""
    query = text("SELECT * FROM exams ORDER BY exam_date")
    exams = db.session.execute(query).fetchall()
    return render_template("schedule_exam.html", exams=exams)


# ==========================
# CANCEL EXAM
# ==========================
@student_exam_bp.route("/student/cancel_exam/<int:exam_id>", methods=["POST"])
@login_required
def cancel_exam(exam_id):
    """Allows a student to cancel an exam registration."""
    try:
        cancel_query = text("""
            UPDATE registrations
            SET status = 'cancelled'
            WHERE exam_id = :exam_id AND student_id = :student_id
        """)
        db.session.execute(cancel_query, {
            "exam_id": exam_id,
            "student_id": current_user.id
        })
        db.session.commit()
        flash("Exam cancelled successfully!", "success")
    except Exception as e:
        db.session.rollback()
        flash("Error cancelling exam. Please try again.", "error")
        print("Cancel Error:", e)
    return redirect(url_for("student_exam_bp.student_appointments"))


# ==========================
# RESCHEDULE EXAM
# ==========================
@student_exam_bp.route("/student/reschedule_exam/<int:exam_id>", methods=["POST"])
@login_required
def reschedule_exam(exam_id):
    """Allows a student to reschedule an exam."""
    new_date = request.form.get("new_date")
    new_time = request.form.get("new_time")

    if not new_date or not new_time:
        flash("Please select both date and time to reschedule.", "error")
        return redirect(url_for("student_exam_bp.student_appointments"))

    try:
        reschedule_query = text("""
            UPDATE registrations
            SET exam_date = :new_date, exam_time = :new_time, status = 'rescheduled'
            WHERE exam_id = :exam_id AND student_id = :student_id
        """)
        db.session.execute(reschedule_query, {
            "exam_id": exam_id,
            "student_id": current_user.id,
            "new_date": new_date,
            "new_time": new_time
        })
        db.session.commit()
        flash("Exam rescheduled successfully!", "success")
    except Exception as e:
        db.session.rollback()
        flash("Error rescheduling exam. Please try again.", "error")
        print("Reschedule Error:", e)

    return redirect(url_for("student_exam_bp.student_appointments"))


# ==========================
# STUDENT APPOINTMENTS
# ==========================
@student_exam_bp.route("/student/appointments", methods=["GET"])
@login_required
def student_appointments():
    """Displays student's scheduled exams."""
    query = text("""
        SELECT e.exam_name, e.exam_date, e.exam_location, r.status, r.exam_id
        FROM registrations r
        JOIN exams e ON e.exam_id = r.exam_id
        WHERE r.student_id = :student_id
    """)
    exams = db.session.execute(query, {"student_id": current_user.id}).fetchall()
    return render_template("appointments.html", exams=exams)

# ==========================
# REGISTRATION CONFIRMATION PAGE   
# ========================== 
@student_exam_routes.route("/student/exams/register", methods=["POST"])
@login_required
def register_exam():
    # Example logic for creating a reservation
    form_data = request.form
    exam_id = form_data.get("exam_id")
    location_id = form_data.get("location_id")
    session_start = form_data.get("session_start")

    new_reservation = Reservation(
        confirmation_number=str(uuid.uuid4())[:8].upper(),
        exam_id=exam_id,
        location_id=location_id,
        session_start=session_start,
        student_id=current_user.id
    )

    db.session.add(new_reservation)
    db.session.commit()

    # Redirect to confirmation page
    return redirect(
        url_for("student_ui.registration_confirmation", reservation_id=new_reservation.id)
    )
