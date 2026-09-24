"""Admin routes: student management (Phase 3)."""
from flask import flash, redirect, render_template, request, url_for
from sqlalchemy import or_

from app.admin import admin_bp
from app.auth.decorators import admin_required  # CONTRACT (C2): Phase 2 RBAC
from app.extensions import db
from app.models import Class, Enrollment, Student, User

from .services import (
    MAX_BULK_IDS, PER_PAGE, audit_event, bulk_enroll, bulk_set_status,
    bulk_unenroll, create_student, enroll_student, reset_student_password,
    set_account_status, unenroll_student, update_student,
)
from .validators import ValidationError, clean


def _get_student_or_404(student_id):
    return Student.query.filter_by(id=student_id).first_or_404()


def _enrollment_names(student_ids):
    """{student_id: [class names]} in a single query (avoids N+1)."""
    if not student_ids:
        return {}
    rows = (
        db.session.query(Enrollment.student_id, Class.name)
        .join(Class, Enrollment.class_id == Class.id)
        .filter(Enrollment.student_id.in_(student_ids), Enrollment.status == "active")
        .all()
    )
    result = {}
    for student_id, class_name in rows:
        result.setdefault(student_id, []).append(class_name)
    return result


@admin_bp.route("/students")
@admin_required
def students_list():
    q = clean(request.args.get("q", ""))
    status = request.args.get("status", "")
    if status not in ("active", "disabled"):
        status = ""
    class_id = request.args.get("class_id", type=int)
    page = max(request.args.get("page", 1, type=int) or 1, 1)

    query = (db.session.query(Student, User.username, User.status)
             .join(User, Student.user_id == User.id))
    if q:
        like = "%" + q + "%"
        query = query.filter(or_(
            Student.full_name.ilike(like),
            Student.student_code.ilike(like),
            Student.email.ilike(like),
            User.username.ilike(like),
        ))
    if status:
        query = query.filter(User.status == status)
    if class_id:
        query = (query.join(Enrollment, Enrollment.student_id == Student.id)
                 .filter(Enrollment.class_id == class_id, Enrollment.status == "active"))

    pagination = (query.order_by(Student.full_name.asc())
                  .paginate(page=page, per_page=PER_PAGE, error_out=False))
    enrollment_names = _enrollment_names([s.id for s, _, _ in pagination.items])
    classes = Class.query.filter_by(status="active").order_by(Class.name).all()
    filters = {"q": q or None, "status": status or None, "class_id": class_id or None}

    return render_template(
        "admin/students/list.html",
        pagination=pagination, enrollment_names=enrollment_names, classes=classes,
        q=q, status=status, class_id=class_id, filters=filters,
    )


@admin_bp.route("/students/new", methods=["GET", "POST"])
@admin_required
def student_new():
    if request.method == "POST":
        form = request.form
        try:
            student = create_student(form)
        except ValidationError as exc:
            flash(str(exc), "error")
            return render_template("admin/students/form.html", form=form, mode="create", student=None)
        flash("Student %s created." % student.full_name, "success")
        return redirect(url_for(".student_detail", student_id=student.id))
    return render_template("admin/students/form.html", form={}, mode="create", student=None)


@admin_bp.route("/students/<int:student_id>")
@admin_required
def student_detail(student_id):
    student = _get_student_or_404(student_id)
    user = User.query.get(student.user_id)

    enrolled_rows = (
        db.session.query(Enrollment.id, Class.id, Class.name, Class.status, Enrollment.enrolled_at)
        .join(Class, Enrollment.class_id == Class.id)
        .filter(Enrollment.student_id == student.id, Enrollment.status == "active")
        .order_by(Class.name).all()
    )
    enrollments = [
        {"enrollment_id": r[0], "class_id": r[1], "class_name": r[2],
         "class_status": r[3], "enrolled_at": str(r[4])[:10] if r[4] else None}
        for r in enrolled_rows
    ]
    enrolled_class_ids = [r[1] for r in enrolled_rows]

    cq = Class.query.filter_by(status="active")
    if enrolled_class_ids:
        cq = cq.filter(~Class.id.in_(enrolled_class_ids))
    available_classes = cq.order_by(Class.name).all()

    return render_template(
        "admin/students/detail.html",
        student=student, user=user, username=user.username,
        created_date=str(user.created_at)[:10] if user.created_at else "-",
        enrollments=enrollments, available_classes=available_classes,
    )


@admin_bp.route("/students/<int:student_id>/edit", methods=["GET", "POST"])
@admin_required
def student_edit(student_id):
    student = _get_student_or_404(student_id)
    if request.method == "POST":
        form = request.form
        try:
            changed = update_student(student, form)
        except ValidationError as exc:
            flash(str(exc), "error")
            return render_template("admin/students/form.html", form=form, mode="edit", student=student)
        flash("Student updated." if changed else "No changes to save.", "success")
        return redirect(url_for(".student_detail", student_id=student.id))
    user = User.query.get(student.user_id)
    form = {"full_name": student.full_name, "email": student.email or "",
            "roll_number": student.roll_number or ""}
    return render_template("admin/students/form.html", form=form, mode="edit",
                           student=student, username=user.username)


@admin_bp.route("/students/<int:student_id>/status", methods=["POST"])
@admin_required
def student_set_status(student_id):
    student = _get_student_or_404(student_id)
    try:
        changed = set_account_status(student, request.form.get("status", ""))
        flash("Account status updated." if changed else "Account is already in that status.",
              "success" if changed else "info")
    except ValidationError as exc:
        flash(str(exc), "error")
    return redirect(url_for(".student_detail", student_id=student_id))


@admin_bp.route("/students/<int:student_id>/enroll", methods=["POST"])
@admin_required
def student_enroll(student_id):
    student = _get_student_or_404(student_id)
    cls = Class.query.filter_by(id=request.form.get("class_id", type=int)).first()
    if cls is None:
        flash("Choose a valid class.", "error")
    else:
        try:
            enroll_student(student, cls)
            flash("Enrolled in %s." % cls.name, "success")
        except ValidationError as exc:
            flash(str(exc), "error")
    return redirect(url_for(".student_detail", student_id=student_id))


@admin_bp.route("/students/<int:student_id>/unenroll/<int:enrollment_id>", methods=["POST"])
@admin_required
def student_unenroll(student_id, enrollment_id):
    _get_student_or_404(student_id)
    # Scoped lookup: the enrollment must belong to this student (IDOR-safe).
    enrollment = Enrollment.query.filter_by(id=enrollment_id, student_id=student_id).first_or_404()
    try:
        unenroll_student(enrollment)
        flash("Enrollment removed.", "success")
    except ValidationError as exc:
        flash(str(exc), "error")
    return redirect(url_for(".student_detail", student_id=student_id))


@admin_bp.route("/students/<int:student_id>/reset-password", methods=["GET", "POST"])
@admin_required
def student_reset_password(student_id):
    student = _get_student_or_404(student_id)
    if request.method == "POST":
        temp_password = reset_student_password(student)
        # Rendered directly (not redirected) so the password is shown once
        # and is never stored anywhere in plain text.
        return render_template("admin/students/reset_result.html",
                               student=student, temp_password=temp_password)
    return render_template("admin/students/reset_confirm.html", student=student)


@admin_bp.route("/students/bulk", methods=["POST"])
@admin_required
def students_bulk():
    action = request.form.get("action", "")
    # type=int silently drops tampered non-integer IDs.
    ids = request.form.getlist("student_ids", type=int)[:MAX_BULK_IDS]
    next_url = url_for(".students_list")

    if not ids:
        flash("Select at least one student.", "warning")
        return redirect(next_url)

    students = Student.query.filter(Student.id.in_(ids)).all()

    if action in ("enable", "disable"):
        target = "active" if action == "enable" else "disabled"
        changed = bulk_set_status(students, target)
        flash("%d account(s) updated." % changed, "success")
    elif action in ("enroll", "unenroll"):
        cls = Class.query.filter_by(id=request.form.get("target_class_id", type=int)).first()
        if cls is None:
            flash("Choose a valid target class.", "error")
            return redirect(next_url)
        if action == "enroll":
            done, skipped = bulk_enroll(students, cls)
            msg = "%d student(s) enrolled in %s." % (done, cls.name)
            if skipped:
                msg += " %d skipped." % len(skipped)
            flash(msg, "success" if done else "warning")
        else:
            done = bulk_unenroll(students, cls)
            flash("%d student(s) removed from %s." % (done, cls.name), "success")
    else:
        flash("Unknown bulk action.", "error")
        return redirect(next_url)

    audit_event("BULK_ACTION", None, None, new="action=%s; selected=%d" % (action, len(ids)))
    return redirect(next_url)
