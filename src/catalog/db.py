"""SQLAlchemy engine + session helpers for the CryoET catalog.

``init_schema(engine)`` bootstraps the schema via
``Base.metadata.create_all`` plus an idempotent legacy-table drop (the
scan-data-model rebuild dropped the old ``scans``/``scan_warnings``/
``scan_run_warnings``/``scan_samples`` tables). Alembic is intentionally
NOT used: the scaffold under ``catalog/migrations/`` is dormant, and schema
changes ship as ORM edits plus an in-``init_schema`` migration step, not as
Alembic revisions.
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import Engine, create_engine, event, text
from sqlalchemy.orm import Session, sessionmaker

DEFAULT_DB_URL = "sqlite:///catalog.db"

# Legacy scan tables removed by the scan-data-model rebuild. Dropped (if
# present) before ``create_all`` so an existing DB cleanly sheds them.
_LEGACY_SCAN_TABLES = (
    "scans",
    "scan_warnings",
    "scan_run_warnings",
    "scan_samples",
)


def make_engine(url: str = DEFAULT_DB_URL) -> Engine:
    """Create a SQLAlchemy engine. Accepts any URL — sqlite:// or postgresql://."""
    engine = create_engine(url, future=True)
    if engine.dialect.name == "sqlite":
        # WAL + a busy timeout are cheap insurance for the scanner's
        # per-sample write transactions (and the run-end log bulk insert);
        # set on every connection. SQLite only — Postgres ignores these.
        @event.listens_for(engine, "connect")
        def _set_sqlite_pragmas(dbapi_conn, _record):  # noqa: ANN001
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA busy_timeout=5000")
            cursor.close()

    return engine


def init_schema(engine: Engine) -> None:
    """Bootstrap the schema on ``engine``: drop legacy scan tables, then
    ``create_all`` the current ORM tables.

    No Alembic, no migration history (the ``catalog/migrations/`` scaffold is
    dormant). Schema changes ship as ORM edits plus the idempotent legacy-table
    drop below. Safe to run repeatedly: the drops use ``IF EXISTS`` and
    ``create_all`` is a no-op for tables that already exist. ``scan_state`` is
    deliberately kept (the cutover re-scans with ``--force`` rather than
    dropping the per-file ledger).
    """
    # Local import keeps this module light when only ``make_engine`` /
    # ``session_scope`` are needed (e.g. by callers that don't bootstrap
    # the schema themselves).
    from catalog.orm import Base

    # Idempotent migration step: drop the legacy scan tables before
    # create_all. One ``DROP TABLE IF EXISTS`` per table is the portable
    # shape (works on both SQLite and Postgres).
    with engine.begin() as conn:
        for table in _LEGACY_SCAN_TABLES:
            conn.execute(text(f"DROP TABLE IF EXISTS {table}"))

    Base.metadata.create_all(engine)


@contextmanager
def session_scope(engine: Engine) -> Iterator[Session]:
    """Yield a session inside a transaction.

    Commits on clean exit, rolls back on exception, and always closes.
    """
    SessionFactory = sessionmaker(bind=engine, future=True, expire_on_commit=False)
    session = SessionFactory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
