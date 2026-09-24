"""Business logic for Phase 3: students, classes, enrollment, CSV import.

Routes stay thin. Every function validates server-side, uses transactions,
and writes audit events. Passwords are hashed immediately and never stored
or logged in plain text.
"""
import csv
import io
import secrets
from datetime import datetime

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from werkzeug.security import generate_password_hash

# CONTRACT (C3): Phase 2 audit helper. If its location/signature differs,
# fix this one import and the `audit_event` wrapper below.
from app.audit import write_audit
from app.database import transaction
from app.extensions import db
from app.models import Class, Enrollment, Student, User

from .validators import (
    EMAIL_RE, STUDENT_CODE_RE, USERNAME_RE,
    ValidationError, clean, validate_class_code, validate_class_name,
    validate_email, validate_name, validate_password, validate_roll_number,
    validate_student_code, validate_username,
)

PER_PAGE = 20
MAX_BULK_IDS = 100
MAX_IMPORT_ROWS = 1000
MAX_FILE_BYTES = 1 * 1024 * 1024  # 1 MB
REQUIRED_HEADERS = ["student_id", "name", "email", "roll_number", "class"]

# Unambiguous alphabet (no i/l/o/0/1) for readable temporary passwords.
TEMP_PASSWORD_ALPHABET = "abcdefghjkmnpqrstuvwxyzABCDEFGHJKMNPQRSTUVWXYZ23456789"
TEMP_PASSWORD_LENGTH = 10


# --------------------------------------------------------------------------
# Audit
# --------------------------------------------------------------------------
def audit_event(action, entity_type=None, entity_id=None, old=None, new=None, reason=None):
    """Single audit entry point for Phase 3. NEVER pass passwords/secrets."""
    write_audit(action=action, entity_type=entity_type, entity_id=entity_id,
                old_value=old, new_value=new, reason=reason)
    db.session.commit()


def generate_temp_password():
    return "".join(secrets.choice(TEMP_PASSWORD_ALPHABET) for _ in range(TEMP_PASSWORD_LENGTH))


# --------------------------------------------------------------------------
# Uniqueness checks (case-insensitive; DB constraints are the final guard)
# --------------------------------------------------------------------------
def _username_taken(username, exclude_user_id=None):
    q = User.query.filter(func.lower(User.username) == username.lower())
    if exclude_user_id is not None:
        q = q.filter(User.id != exclude_user_id)
    return db.session.query(q.exists()).scalar()


def _student_code_taken(code, exclude_student_id=None):
    q = Student.query.filter(func.lower(Student.student_code) == code.lower())
    if exclude_student_id is not None:
        q = q.filter(Student.id != exclude_student_id)
    return db.session.query(q.exists()).scalar()


def _email_taken(email, exclude_student_id=None):
    q = Student.query.filter(func.lower(Student.email) == email.lower())
    if exclude_student_id is not None:
        q = q.filter(Student.id != exclude_student_id)
    return db.session.query(q.exists()).scalar()


def _class_code_taken(code, exclude_class_id=None):
    q = Class.query.filter(func.lower(Class.class_code) == code.lower())
    if exclude_class_id is not None:
        q = q.filter(Class.id != exclude_class_id)
    return db.session.query(q.exists()).scalar()


# --------------------------------------------------------------------------
# Students
# --------------------------------------------------------------------------
def create_student(form):
    username = validate_username(form.get("username"))
    student_code = validate_student_code(form.get("student_code"))
    full_name = validate_name(form.get("full_name"))
    email = validate_email(form.get("email"))
    roll_number = validate_roll_number(form.get("roll_number"))
    password = validate_password(form.get("password"))

    if _username_taken(username):
        raise ValidationError("That username is already in use.")
    if _student_code_taken(student_code):
        raise ValidationError("That student ID is already in use.")
    if email and _email_taken(email):
        raise ValidationError("That email is already in use.")

    try:
        with transaction():
            user = User(username=username, role="student", status="active")
            user.password_hash = generate_password_hash(password)
            db.session.add(user)
            db.session.flush()
            student = Student(
                user_id=user.id,
                student_code=student_code,
                full_name=full_name,
                email=email,
                roll_number=roll_number,
            )
            db.session.add(student)
            db.session.flush()
    except IntegrityError:
        raise ValidationError("Duplicate student (username, student ID, or email already exists).")

    audit_event("STUDENT_CREATED", "student", student.id,
                new="username=%s; student_code=%s" % (username, student_code))
    return student


def update_student(student, form):
    full_name = validate_name(form.get("full_name"))
    email = validate_email(form.get("email"))
    roll_number = validate_roll_number(form.get("roll_number"))

    if email and _email_taken(email, exclude_student_id=student.id):
        raise ValidationError("That email is already in use.")

    changes = []
    if student.full_name != full_name:
        changes.append("full_name: '%s' -> '%s'" % (student.full_name, full_name))
    if (student.email or None) != email:
        changes.append("email: '%s' -> '%s'" % (student.email or "", email or ""))
    if (student.roll_number or None) != roll_number:
        changes.append("roll_number: '%s' -> '%s'" % (student.roll_number or "", roll_number or ""))

    if not changes:
        return False

    with transaction():
        student.full_name = full_name
        student.email = email
        student.roll_number = roll_number
        student.updated_at = datetime.utcnow()

    audit_event("STUDENT_UPDATED", "student", student.id, new="; ".join(changes))
    return True


def set_account_status(student, new_status):
    if new_status not in ("active", "disabled"):
        raise ValidationError("Invalid account status.")
    user = User.query.get(student.user_id)
    if user is None:
        raise ValidationError("Student account record is missing.")
    if user.status == new_status:
        return False
    old_status = user.status
    with transaction():
        user.status = new_status
        user.updated_at = datetime.utcnow()
    action = "STUDENT_DISABLED" if new_status == "disabled" else "STUDENT_RESTORED"
    audit_event(action, "student", student.id, old=old_status, new=new_status)
    return True


def reset_student_password(student):
    temp_password = generate_temp_password()
    with transaction():
        user = User.query.get(student.user_id)
        user.password_hash = generate_password_hash(temp_password)
        user.updated_at = datetime.utcnow()
    # Never log the password itself.
    audit_event("PASSWORD_RESET", "student", student.id, new="[redacted]")
    return temp_password


# --------------------------------------------------------------------------
# Classes
# --------------------------------------------------------------------------
def create_class(form):
    name = validate_class_name(form.get("name"))
    code = validate_class_code(form.get("class_code"))
    if _class_code_taken(code):
        raise ValidationError("That class code is already in use.")
    try:
        with transaction():
            cls = Class(name=name, class_code=code, status="active")
            db.session.add(cls)
            db.session.flush()
    except IntegrityError:
        raise ValidationError("Duplicate class code.")
    audit_event("CLASS_CREATED", "class", cls.id, new="name=%s; code=%s" % (name, code))
    return cls


def update_class(cls, form):
    name = validate_class_name(form.get("name"))
    if cls.name == name:
        return False
    old_name = cls.name
    with transaction():
        cls.name = name
        cls.updated_at = datetime.utcnow()
    audit_event("CLASS_UPDATED", "class", cls.id,
                old="name=%s" % old_name, new="name=%s" % name)
    return True


def set_class_status(cls, new_status):
    if new_status not in ("active", "archived"):
        raise ValidationError("Invalid class status.")
    if cls.status == new_status:
        return False
    old_status = cls.status
    with transaction():
        cls.status = new_status
        cls.updated_at = datetime.utcnow()
    action = "CLASS_ARCHIVED" if new_status == "archived" else "CLASS_RESTORED"
    audit_event(action, "class", cls.id, old=old_status, new=new_status)
    return True


# --------------------------------------------------------------------------
# Enrollment
# --------------------------------------------------------------------------
def enroll_student(student, cls):
    if cls.status != "active":
        raise ValidationError("Cannot enroll students in an archived class.")
    existing = Enrollment.query.filter_by(student_id=student.id, class_id=cls.id).first()
    if existing is not None:
        if existing.status == "active":
            raise ValidationError("%s is already enrolled in %s." % (student.full_name, cls.name))
        # Reactivate the soft-removed row (UNIQUE(student_id, class_id) is preserved).
        with transaction():
            existing.status = "active"
            existing.enrolled_at = datetime.utcnow()
        audit_event("STUDENT_ENROLLED", "enrollment", existing.id,
                    new="student=%s; class=%s; re-enrolled" % (student.student_code, cls.class_code))
        return existing
    try:
        with transaction():
            enrollment = Enrollment(student_id=student.id, class_id=cls.id,
                                    status="active", enrolled_at=datetime.utcnow())
            db.session.add(enrollment)
            db.session.flush()
    except IntegrityError:
        raise ValidationError("Duplicate enrollment.")
    audit_event("STUDENT_ENROLLED", "enrollment", enrollment.id,
                new="student=%s; class=%s" % (student.student_code, cls.class_code))
    return enrollment


def unenroll_student(enrollment):
    if enrollment.status != "active":
        raise ValidationError("That enrollment is not active.")
    student = Student.query.get(enrollment.student_id)
    cls = Class.query.get(enrollment.class_id)
    with transaction():
        enrollment.status = "removed"
    audit_event("STUDENT_UNENROLLED", "enrollment", enrollment.id,
                old="student=%s; class=%s" % (
                    student.student_code if student else "?",
                    cls.class_code if cls else "?"))
    return enrollment


# --------------------------------------------------------------------------
# Bulk actions
# --------------------------------------------------------------------------
def bulk_set_status(students, new_status):
    changed = 0
    for student in students:
        try:
            if set_account_status(student, new_status):
                changed += 1
        except ValidationError:
            continue
    return changed


def bulk_enroll(students, cls):
    done, skipped = 0, []
    for student in students:
        try:
            enroll_student(student, cls)
            done += 1
        except ValidationError as exc:
            skipped.append("%s: %s" % (student.student_code, exc))
    return done, skipped


def bulk_unenroll(students, cls):
    done = 0
    for student in students:
        enrollment = Enrollment.query.filter_by(
            student_id=student.id, class_id=cls.id, status="active").first()
        if enrollment is None:
            continue
        unenroll_student(enrollment)
        done += 1
    return done


# --------------------------------------------------------------------------
# CSV import (file is processed in memory only — never written to disk)
# --------------------------------------------------------------------------
def read_csv_file(file_storage):
    """Structurally validate the upload. Returns (rows, fatal_error)."""
    data = file_storage.read()
    if not data:
        return None, "The file is empty."
    if len(data) > MAX_FILE_BYTES:
        return None, "File is too large (maximum 1 MB)."
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        return None, "The file must be UTF-8 encoded."

    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        return None, "The file has no header row."
    headers = [(h or "").strip().lower() for h in reader.fieldnames]
    missing = [h for h in REQUIRED_HEADERS if h not in headers]
    if missing:
        return None, "Missing required columns: " + ", ".join(missing) + "."

    rows = []
    for line, raw in enumerate(reader, start=2):
        row = {}
        for key, value in raw.items():
            if key is None:
                continue  # extra values beyond the header count
            row[key.strip().lower()] = (value or "").strip()
        row["_line"] = line
        rows.append(row)

    if not rows:
        return None, "The file contains no data rows."
    if len(rows) > MAX_IMPORT_ROWS:
        return None, "Too many rows (maximum %d)." % MAX_IMPORT_ROWS
    return rows, None


def import_students(rows):
    """Validate rows, then create all valid students atomically.

    Invalid rows and duplicates are reported but do not block valid rows.
    Temporary passwords are generated per student and returned ONCE.
    """
    report = {
        "total": len(rows), "created": 0, "duplicates": 0, "invalid": 0,
        "skipped": 0, "issues": [], "credentials": [], "fatal": None,
    }

    existing_codes = {r[0].lower() for r in Student.query.with_entities(Student.student_code)}
    existing_emails = {r[0].lower() for r in
                       Student.query.with_entities(Student.email).filter(Student.email.isnot(None))}
    existing_usernames = {r[0].lower() for r in User.query.with_entities(User.username)}
    active_classes = {c.class_code.lower(): c for c in Class.query.filter_by(status="active")}

    seen_codes, seen_emails, seen_usernames = set(), set(), set()
    pending = []

    for row in rows:
        line = row["_line"]
        code = clean(row.get("student_id"))
        name = clean(row.get("name"))
        email = clean(row.get("email")).lower()
        roll = clean(row.get("roll_number"))
        class_code = clean(row.get("class"))
        username = clean(row.get("username")).lower() or code.lower()

        format_errors = []
        if not STUDENT_CODE_RE.match(code):
            format_errors.append("invalid student_id")
        if not name or len(name) > 100:
            format_errors.append("missing/invalid name")
        if email and (len(email) > 254 or not EMAIL_RE.match(email)):
            format_errors.append("invalid email")
        if roll and len(roll) > 30:
            format_errors.append("roll_number too long")
        if not USERNAME_RE.match(username):
            format_errors.append("invalid username")

        target_class = None
        if class_code:
            target_class = active_classes.get(class_code.lower())
            if target_class is None:
                format_errors.append("unknown or archived class '%s'" % class_code)

        if format_errors:
            report["invalid"] += 1
            report["issues"].append({"line": line, "student_id": code,
                                     "status": "invalid", "reasons": format_errors})
            continue

        dup_reasons = []
        if code.lower() in existing_codes or code.lower() in seen_codes:
            dup_reasons.append("duplicate student_id")
        if email and (email in existing_emails or email in seen_emails):
            dup_reasons.append("duplicate email")
        if username in existing_usernames or username in seen_usernames:
            dup_reasons.append("duplicate username")
        if dup_reasons:
            report["duplicates"] += 1
            report["issues"].append({"line": line, "student_id": code,
                                     "status": "duplicate", "reasons": dup_reasons})
            continue

        seen_codes.add(code.lower())
        if email:
            seen_emails.add(email)
        seen_usernames.add(username)
        pending.append({
            "student_code": code, "full_name": name, "email": email or None,
            "roll_number": roll or None, "username": username,
            "class": target_class, "password": generate_temp_password(),
        })

    try:
        with transaction():
            for item in pending:
                user = User(username=item["username"], role="student", status="active")
                user.password_hash = generate_password_hash(item["password"])
                db.session.add(user)
                db.session.flush()
                student = Student(user_id=user.id, student_code=item["student_code"],
                                  full_name=item["full_name"], email=item["email"],
                                  roll_number=item["roll_number"])
                db.session.add(student)
                db.session.flush()
                if item["class"] is not None:
                    db.session.add(Enrollment(
                        student_id=student.id, class_id=item["class"].id,
                        status="active", enrolled_at=datetime.utcnow()))
                report["credentials"].append({
                    "student_code": item["student_code"],
                    "username": item["username"],
                    "temp_password": item["password"],
                })
        report["created"] = len(pending)
    except IntegrityError:
        report["fatal"] = "The import failed while writing to the database. All changes were rolled back."
        return report

    report["skipped"] = report["duplicates"] + report["invalid"]
    audit_event("CSV_IMPORT_COMPLETED", "import", None,
                new="total=%d; created=%d; duplicates=%d; invalid=%d" % (
                    report["total"], report["created"], report["duplicates"], report["invalid"]))
    return report
