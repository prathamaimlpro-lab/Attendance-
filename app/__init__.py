"""Flask application factory (Phase 1 foundation)."""
import os
import secrets

from flask import Flask, render_template

from .config import config_by_name


def create_app(config_name=None):
    if config_name is None:
        config_name = os.environ.get("FLASK_CONFIG", "development")

    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config_by_name[config_name])

    _ensure_instance_folder(app)
    _ensure_secret_key(app, config_name)

    # Extensions
    from .extensions import db
    db.init_app(app)

    # Database foundation (pragmas + CLI)
    from .database import register_database
    register_database(app)

    _register_blueprints(app)
    _register_error_handlers(app)
    _register_security_headers(app)

    return app


def _ensure_instance_folder(app):
    try:
        os.makedirs(app.instance_path, exist_ok=True)
    except OSError:
        pass


def _ensure_secret_key(app, config_name):
    """Refuse to boot production without a key; use a temp key in dev."""
    if not app.config.get("SECRET_KEY"):
        if config_name == "production":
            raise RuntimeError(
                "SECRET_KEY is required in production. Set it in the environment."
            )
        app.config["SECRET_KEY"] = secrets.token_hex(32)
        app.logger.warning(
            "SECRET_KEY not set; generated a temporary key. "
            "Set SECRET_KEY in .env for stable sessions."
        )


def _register_blueprints(app):
    from .core.routes import core_bp
    app.register_blueprint(core_bp)


def _register_error_handlers(app):
    @app.errorhandler(403)
    def forbidden(_e):
        return render_template("errors/403.html"), 403

    @app.errorhandler(404)
    def not_found(_e):
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def server_error(_e):
        return render_template("errors/500.html"), 500


def _register_security_headers(app):
    @app.after_request
    def set_security_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; "
            "object-src 'none'; "
            "base-uri 'self'; "
            "frame-ancestors 'none'"
        )
        return response
