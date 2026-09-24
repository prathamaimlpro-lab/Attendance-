"""Admin routes: class management (Phase 3)."""
from flask import flash, redirect, render_template, request, url_for
from sqlalchemy import func

from app.admin import admin_bp
from app.auth.decorators import admin_required  # CONTRACT (C2)
from app.extensions import db
from app.models import Class, Enrollment, Student, User

from .services import (create_class, enroll_student, set_class_status,
                       unenroll_student, update_class)
from .validators import ValidationError


def _get_class_or_404(class_id):
    return Class.query.filter_by(id=class_id).first_or_404()


@admin_bp.route("/classes")
@admin_required
def classes_list():
    status = request.args.get("status", "active")
    if status not in ("active", "archived"):
        status = "active"
    classes = Class.query.filter_by(status=status).order_by(Class.name).all()
    counts = dict(
        db.session.query(Enrollment.class_id, func.count(Enrollment.id))
        .filter(Enrollment.status == "active")
        .group_by(Enrollment.class_id).all()
    )
    return render_template("admin/classes/list.html", classes=classes, counts=counts, status=status)


@admin_bp.route("/classes/new", methods=["GET", "POST"])
@admin_required
def class_new():
    if request.method == "POST":
        try:
            cls = create_class(request.form)
        except ValidationError as exc:
            flash(str(exc), "error")
            return render_template("admin/classes/form.html", form=request.form, mode="create", cls=None)
        flash("Class %s created." % cls.name, "success")
        return redirect(url_for(".class_detail", class_id=cls.id))
    return render_template("admin/classes/form.html", form={}, mode="create", cls=None)


@admin_bp.route("/classes/<int:class_id>")
@admin_required
def class_detail(class_id):
    cls = _get_class_or_404(class_id)
    roster_rows = (
        db.session.query(Enrollment.id, Student.id, Student.full_name,
                         Student.student_code, Enrollment.enrolled_at)
        .join(Student, Enrollment.student_id == Student.id)
        .filter(Enrollment.class_id == cls.id, Enrollment.status == "active")
        .order_by(Student.full_name).all()
    )
    roster = [
        {"enrollment_id": r[0], "student_id": r[1], "full_name": r[2],
         "student_code": r[3], "enrolled_at": str(r[4])[:10] if r[4] else None}
        for r in roster_rows
    ]

    available = []
    if cls.status == "active":
        enrolled_ids = [row["student_id"] for row in roster]
        aq = (Student.query.join(User, Student.user_id == User.id)
              .filter(User.status == "active"))
        if enrolled_ids:
            aq = aq.filter(~Student.id.in_(enrolled_ids))
        available = aq.order_by(Student.full_name).limit(500).all()

    return render_template("admin/classes/detail.html", cls=cls, roster=roster, available=available)


@admin_bp.route("/classes/<int:class_id>/edit", methods=["GET", "POST"])
@admin_required
def class_edit(class_id):
    cls = _get_class_or_404(class_id)
    if request.method == "POST":
        try:
            changed = update_class(cls, request.form)
        except ValidationError as exc:
            flash(str(exc), "error")
            return render_template("admin/classes/form.html", form=request.form, mode="edit", cls=cls)
        flash("Class updated." if changed else "No changes to save.", "success")
        return redirect(url_for(".class_detail", class_id=cls.id))
    return render_template("admin/classes/form.html", form={"name": cls.name}, mode="edit", cls=cls)


@admin_bp.route("/classes/<int:class_id>/status", methods=["POST"])
@admin_required
def class_set_status(class_id):
    cls = _get_class_or_404(class_id)
    try:
        changed = set_class_status(cls, request.form.get("status", ""))
        flash("Class status updated." if changed else "Class is already in that status.",
              "success" if changed else "info")
    except ValidationError as exc:
        flash(str(exc), "error")
    return redirect(url_for(".class_detail", class_id=cls.id))


@admin_bp.route("/classes/<int:class_id>/enroll", methods=["POST"])
@admin_required
def class_enroll(class_id):
    cls = _get_class_or_404(class_id)
    student = Student.query.filter_by(id=request.form.get("student_id", type=int)).first()
    if student is None:
        flash("Choose a valid student.", "error")
    else:
        try:
            enroll_student(student, cls)
            flash("%s enrolled." % student.full_name, "success")
        except ValidationError as exc:
            flash(str(exc), "error")
    return redirect(url_for(".class_detail", class_id=cls.id))


@admin_bp.route("/classes/<int:class_id>/enrollments/<int:enrollment_id>/remove", methods=["POST"])
@admin_required
def class_remove_enrollment(class_id, enrollment_id):
    cls = _get_class_or_404(class_id)
    # Scoped lookup: enrollment must belong to THIS class (IDOR-safe).
    enrollment = Enrollment.query.filter_by(id=enrollment_id, class_id=cls.id).first_or_404()
    try:
        unenroll_student(enrollment)
        flash("Student removed from class.", "success")
    except ValidationError as exc:
        flash(str(exc), "error")
    return redirect(url_for(".class_detail", class_id=cls.id))
