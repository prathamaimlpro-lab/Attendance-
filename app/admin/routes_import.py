"""Admin routes: CSV bulk import (Phase 3).

Uploaded files are read in memory only — never written to disk — so path
traversal is impossible. Content is parsed by the csv module (never executed)
and stored only through the ORM (parameterized — no SQL injection).
"""
from flask import Response, flash, render_template, request
from werkzeug.utils import secure_filename

from app.admin import admin_bp
from app.auth.decorators import admin_required  # CONTRACT (C2)

from .services import import_students, read_csv_file

TEMPLATE_CSV = (
    "student_id,name,email,roll_number,class\n"
    "24IT001,Example Student,example@college.example,1,IT-A\n"
)


@admin_bp.route("/students/import")
@admin_required
def import_form():
    return render_template("admin/students/import.html", fatal=None)


@admin_bp.route("/students/import", methods=["POST"])
@admin_required
def import_submit():
    file = request.files.get("csv_file")
    if file is None or not file.filename:
        flash("Choose a CSV file to import.", "error")
        return render_template("admin/students/import.html", fatal=None)

    filename = secure_filename(file.filename)
    if not filename.lower().endswith(".csv"):
        return render_template("admin/students/import.html",
                               fatal="Only .csv files are accepted.")

    rows, fatal = read_csv_file(file)
    if fatal:
        return render_template("admin/students/import.html", fatal=fatal)

    report = import_students(rows)
    return render_template("admin/students/import_results.html", report=report, filename=filename)


@admin_bp.route("/students/import/template")
@admin_required
def import_template():
    return Response(
        TEMPLATE_CSV,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=student_import_template.csv"},
    )
