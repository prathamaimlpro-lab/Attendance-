"""Flask extension instances (created once, bound in the app factory)."""
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
