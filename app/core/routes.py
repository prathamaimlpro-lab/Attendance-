"""Core routes (Phase 1): home and the design-system showcase."""
from flask import Blueprint, render_template

core_bp = Blueprint("core", __name__)


DESIGN_COLORS = [
    ("primary", "#0066cc"),
    ("primary-focus", "#0071e3"),
    ("primary-on-dark", "#2997ff"),
    ("ink", "#1d1d1f"),
    ("body-muted", "#cccccc"),
    ("ink-muted-80", "#333333"),
    ("ink-muted-48", "#7a7a7a"),
    ("divider-soft", "#f0f0f0"),
    ("hairline", "#e0e0e0"),
    ("canvas", "#ffffff"),
    ("canvas-parchment", "#f5f5f7"),
    ("surface-pearl", "#fafafc"),
    ("surface-tile-1", "#272729"),
    ("surface-tile-2", "#2a2a2c"),
    ("surface-tile-3", "#252527"),
    ("surface-black", "#000000"),
    ("on-primary", "#ffffff"),
    ("on-dark", "#ffffff"),
]


@core_bp.route("/")
def index():
    return render_template("index.html")


@core_bp.route("/dev/design")
def design_system():
    return render_template("design_system.html", colors=DESIGN_COLORS)
