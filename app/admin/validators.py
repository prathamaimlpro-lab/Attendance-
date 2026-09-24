"""Server-side field validation for Phase 3 admin forms (no client trust)."""
import re

USERNAME_RE = re.compile(r"^[a-z0-9_]{3,32}$")
STUDENT_CODE_RE = re.compile(r"^[A-Za-z0-9\-]{3,20}$")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

MIN_PASSWORD_LEN = 8
MAX_PASSWORD_LEN = 64
MAX_NAME_LEN = 100
MAX_EMAIL_LEN = 254
MAX_ROLL_LEN = 30


class ValidationError(Exception):
    """Raised when input fails server-side validation."""


def clean(value):
    return (value or "").strip()


def validate_username(username):
    username = clean(username).lower()
    if not USERNAME_RE.match(username):
        raise ValidationError("Username must be 3-32 characters: lowercase letters, numbers, underscores.")
    return username


def validate_student_code(code):
    code = clean(code)
    if not STUDENT_CODE_RE.match(code):
        raise ValidationError("Student ID must be 3-20 characters: letters, numbers, hyphens.")
    return code


def validate_name(name):
    name = clean(name)
    if not name or len(name) > MAX_NAME_LEN:
        raise ValidationError("Full name is required (max 100 characters).")
    return name


def validate_email(email, required=False):
    email = clean(email).lower()
    if not email:
        if required:
            raise ValidationError("Email is required.")
        return None
    if len(email) > MAX_EMAIL_LEN or not EMAIL_RE.match(email):
        raise ValidationError("Enter a valid email address.")
    return email


def validate_roll_number(roll):
    roll = clean(roll)
    if len(roll) > MAX_ROLL_LEN:
        raise ValidationError("Roll number must be at most %d characters." % MAX_ROLL_LEN)
    return roll or None


def validate_password(password):
    if not password or not (MIN_PASSWORD_LEN <= len(password) <= MAX_PASSWORD_LEN):
        raise ValidationError("Password must be %d-%d characters." % (MIN_PASSWORD_LEN, MAX_PASSWORD_LEN))
    return password


def validate_class_name(name):
    name = clean(name)
    if not name or len(name) > 60:
        raise ValidationError("Class name is required (max 60 characters).")
    return name


def validate_class_code(code):
    code = clean(code)
    if not re.match(r"^[A-Za-z0-9\-]{2,20}$", code):
        raise ValidationError("Class code must be 2-20 characters: letters, numbers, hyphens.")
    return code
