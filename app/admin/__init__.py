"""Admin blueprint — student & class management (Phase 3).

Every route requires an authenticated admin (`admin_required`, applied per
route). A global `before_app_request` guard additionally rejects disabled
accounts so they lose access immediately, even with a live session cookie.
"""
from flask import Blueprint, flash, redirect

from flask_login import current_user, logout_user

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")

MAX_CONTENT_LENGTH = 2 * 1024 * 1024  # 2 MB upload cap (defense in depth)


@admin_bp.before_app_request
def reject_disabled_accounts():
    """Server-side: a disabled account is rejected on every request."""
    if current_user.is_authenticated and getattr(current_user, "status", "active") == "disabled":
        logout_user()
        flash("Your account has been disabled. Contact an administrator.", "error")
        return redirect("/login")


@admin_bp.record_once
def _set_upload_limit(state):
    state.app.config.setdefault("MAX_CONTENT_LENGTH", MAX_CONTENT_LENGTH)


# Import route modules so their views register on the blueprint.
from . import routes_students, routes_classes, routes_import  # noqa: E402,F401
