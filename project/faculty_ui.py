# project/faculty_ui.py
from flask import Blueprint, render_template, request, flash
from flask_login import login_required
from . import db
from sqlalchemy import text

faculty_ui = Blueprint("faculty_ui", __name__)

# ==========================
# FACULTY DASHBOARD
# ==========================
@faculty_ui.route("/faculty/dashboard", methods=["GET"])
@login_required
def faculty_dashboard():
    """Landing page for faculty after login."""
    return render_template("faculty_dashboard.html")

# ==========================
# PRINT EXAM LOG
# ==========================
@faculty_ui.route("/faculty/print_log", methods=["GET"])
@login_required
def faculty_print_log():
    """Display a list of all exam appointments for faculty viewing or printing."""
    try:
        query = text("""
            SELECT e.exam_name, e.exam_date, e.exam_location,
                   s.first_name, s.last_name, r.status
            FROM registrations r
            JOIN exams e ON e.exam_id = r.exam_id
            JOIN users s ON s.id = r.student_id
            ORDER BY e.exam_date
        """)
        results = db.session.execute(query).fetchall()
    except Exception as e:
        results = []
        flash("Error loading exam log. Please try again.", "error")
        print("Faculty print log error:", e)

    return render_template("faculty_print_log.html", results=results)

# ==========================
# SEARCH APPOINTMENTS
# ==========================
@faculty_ui.route("/faculty/search_appointments", methods=["GET", "POST"])
@login_required
def faculty_search_appointments():
    """Allows faculty to search for student appointments by name, exam, or ID."""
    results = []
    if request.method == "POST":
        search_term = request.form.get("search_term")
        try:
            query = text("""
                SELECT e.exam_name, e.exam_date, e.exam_location,
                       s.first_name, s.last_name, r.status, r.exam_id
                FROM registrations r
                JOIN exams e ON e.exam_id = r.exam_id
                JOIN users s ON s.id = r.student_id
                WHERE s.first_name LIKE :term
                   OR s.last_name LIKE :term
                   OR e.exam_name LIKE :term
                   OR r.exam_id LIKE :term
                ORDER BY e.exam_date
            """)
            results = db.session.execute(query, {"term": f"%{search_term}%"}).fetchall()
        except Exception as e:
            flash("Error searching appointments. Please try again.", "error")
            print("Faculty search error:", e)

    return render_template("faculty_search_appointments.html", results=results)
