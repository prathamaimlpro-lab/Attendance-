"""Application configuration.

Secrets come from environment variables (loaded from `.env` by python-dotenv).
Nothing sensitive is hard-coded here.
"""
import os

from dotenv import load_dotenv

# Project root (parent of the `app/` package).
BASE_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))

# Load `.env` from the project root. Does NOT override already-set env vars.
load_dotenv(os.path.join(BASE_DIR, ".env"))


class Config:
    # --- Core ---
    SECRET_KEY = os.environ.get("SECRET_KEY")
    DEBUG = False
    TESTING = False

    # --- Database ---
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        "sqlite:///" + os.path.join(BASE_DIR, "instance", "app.db"),
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
    }

    # --- Secure session-cookie defaults ---
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False
    # Cookies are only sent over HTTPS. Production must run behind TLS.
    SESSION_COOKIE_SECURE = True


class TestingConfig(Config):
    TESTING = True
    DEBUG = True
    # The test fixture points DATABASE_URL at a temp file before import.


config_by_name = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
}
