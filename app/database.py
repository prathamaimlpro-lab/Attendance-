"""Database foundation layer (Phase 1).

Provides:
  * SQLite pragmas (foreign keys ON, WAL journal mode)
  * A safe transaction context manager
  * An `init-db` CLI command

Actual tables are introduced in Phase 2.
"""
from contextlib import contextmanager

from sqlalchemy import event, text

from .extensions import db


def _apply_sqlite_pragmas(dbapi_connection, connection_record):
    """Run pragmas on every new SQLite connection."""
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.close()


def register_database(app):
    """Attach pragmas and register the init-db CLI command."""
    with app.app_context():
        event.listen(db.engine, "connect", _apply_sqlite_pragmas)

    @app.cli.command("init-db")
    def init_db_command():
        """Create the database file and verify pragmas."""
        report = init_database()
        app.logger.info("Database initialized: %s", report)
        print("Database initialized.")
        print(f"  foreign_keys = {report['foreign_keys']}")
        print(f"  journal_mode = {report['journal_mode']}")

    return app


def init_database():
    """Create the SQLite file and run a self-check. Returns pragma values."""
    db.create_all()  # No models yet in Phase 1; ensures the file exists.
    with db.engine.connect() as conn:
        conn.execute(text("SELECT 1"))  # Force file creation.
        foreign_keys = conn.execute(text("PRAGMA foreign_keys")).scalar()
        journal_mode = conn.execute(text("PRAGMA journal_mode")).scalar()
    return {"foreign_keys": foreign_keys, "journal_mode": journal_mode}


@contextmanager
def transaction():
    """Commit on success, roll back on any error."""
    try:
        yield db.session
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
