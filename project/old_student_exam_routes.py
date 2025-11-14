# DISABLED on 2025-11-08
# All routes in this file have been replaced by student_ui.py.
# Keeping this for reference only.

# from flask import Blueprint, render_template, request, redirect, url_for, flash
# from flask_login import login_required, current_user
# from sqlalchemy import text
# from . import db
#
# # Blueprint for exam actions (kept separate from student_ui)
# student_exam_bp = Blueprint("student_exam_bp", __name__)
#
# # ==========================================================
# # VIEW AVAILABLE EXAMS
# # ==========================================================
# @student_exam_bp.route("/student/exams", methods=["GET"])
# @login_required
# def student_exams():
#     """
#     Display list of upcoming exam sessions that still have seats.
#     Hidden if full (booked_count >= 20).
#     """
#     query = text("""
#         SELECT 
#             e.id AS exam_id,
#             e.exam_type,
#             e.exam_date,
#             e.exam_time,
#             l.name AS location_name,
#             e.capacity,
#             (SELECT COUNT(*) FROM Registrations r WHERE r.exam_id = e.id AND r.status = 'booked') AS booked_count
#         FROM Exams e
#         LEFT JOIN Locations l ON e.location_id = l.id
#         WHERE e.exam_date >= CURDATE()
#         ORDER BY e.exam_date, e.exam_time
#     """)
#     exams = db.session.execute(query).mappings().all()
#
#     return render_template("schedule_exam.html", exams=exams)
#
#
# # ==========================================================
# # REGISTER FOR EXAM
# # ==========================================================
# @student_exam_bp.route("/student/register_exam/<int:exam_id>", methods=["POST"])
# @login_required
# def register_exam(exam_id):
#     """
#     Register the logged-in student for an available exam session.
#     Enforces booking limits and duplicate restrictions.
#     """
#     try:
#         # Check if exam exists and seats are available
#         exam = db.session.execute(text("""
#             SELECT e.id, e.exam_type,
#                    (SELECT COUNT(*) FROM Registrations r WHERE r.exam_id = e.id AND r.status = 'booked') AS booked_count
#             FROM Exams e
#             WHERE e.id = :exam_id
#         """), {"exam_id": exam_id}).mappings().first()
#
#         if not exam:
#             flash("Exam not found.", "error")
#             return redirect(url_for("student_exam_bp.student_exams"))
#
#         if exam["booked_count"] >= 20:
#             flash("This session is full. Please select another.", "error")
#             return redirect(url_for("student_exam_bp.student_exams"))
#
#         # Check existing reservations
#         active_regs = db.session.execute(text("""
#             SELECT r.id, e.exam_type
#             FROM Registrations r
#             JOIN Exams e ON e.id = r.exam_id
#             WHERE r.user_id = :user_id AND r.status = 'booked'
#         """), {"user_id": current_user.id}).mappings().all()
#
#         # Already registered for this exam type?
#         if any(r["exam_type"] == exam["exam_type"] for r in active_regs):
#             flash(f"You already have a reservation for {exam['exam_type']}.", "error")
#             return redirect(url_for("student_exam_bp.student_exams"))
#
#         # Enforce 3 active reservations max
#         if len(active_regs) >= 3:
#             flash("You have reached the limit of three active exam reservations.", "error")
#             return redirect(url_for("student_exam_bp.student_exams"))
#
#         # Create the booking
#         db.session.execute(text("""
#             INSERT INTO Registrations (user_id, exam_id, status)
#             VALUES (:user_id, :exam_id, 'booked')
#         """), {"user_id": current_user.id, "exam_id": exam_id})
#         db.session.commit()
#
#         flash("Exam registered successfully!", "success")
#
#     except Exception as e:
#         db.session.rollback()
#         print("Register Error:", e)
#         flash("Error registering for exam. Please try again.", "error")
#
#     return redirect(url_for("student_exam_bp.student_appointments"))
#
#
# # ==========================================================
# # CANCEL EXAM
# # ==========================================================
# @student_exam_bp.route("/student/cancel_exam/<int:exam_id>", methods=["POST"])
# @login_required
# def cancel_exam(exam_id):
#     """Cancel a booked exam session."""
#     try:
#         result = db.session.execute(text("""
#             UPDATE Registrations
#             SET status = 'cancelled'
#             WHERE exam_id = :exam_id AND user_id = :user_id AND status = 'booked'
#         """), {"exam_id": exam_id, "user_id": current_user.id})
#         db.session.commit()
#
#         if result.rowcount == 0:
#             flash("No active booking found to cancel.", "warning")
#         else:
#             flash("Exam cancelled successfully!", "success")
#
#     except Exception as e:
#         db.session.rollback()
#         print("Cancel Error:", e)
#         flash("Error cancelling exam. Please try again.", "error")
#
#     return redirect(url_for("student_exam_bp.student_appointments"))
#
#
# # ==========================================================
# # STUDENT APPOINTMENTS
# # ==========================================================
# @student_exam_bp.route("/student/appointments", methods=["GET"])
# @login_required
# def student_appointments():
#     """Display the logged-in student's booked and past exam sessions."""
#     query = text("""
#         SELECT 
#             r.id AS registration_id,
#             e.exam_type,
#             e.exam_date,
#             e.exam_time,
#             l.name AS location_name,
#             r.status
#         FROM Registrations r
#         JOIN Exams e ON e.id = r.exam_id
#         LEFT JOIN Locations l ON l.id = e.location_id
#         WHERE r.user_id = :user_id
#         ORDER BY e.exam_date, e.exam_time
#     """)
#     exams = db.session.execute(query, {"user_id": current_user.id}).mappings().all()
#
#     return render_template("appointments.html", exams=exams)
