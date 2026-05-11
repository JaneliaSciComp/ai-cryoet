"""End-to-end tests for ``cryoet_catalog.db.init_schema``."""

from __future__ import annotations

import pytest

pytest.importorskip("alembic")
pytest.importorskip("sqlalchemy")

from pathlib import Path  # noqa: E402

from sqlalchemy import inspect, text  # noqa: E402

from cryoet_catalog import db  # noqa: E402


def _engine_at(tmp_path: Path, name: str = "cat.db"):
    return db.make_engine(f"sqlite:///{tmp_path / name}")


def _alembic_version_value(engine) -> str | None:
    insp = inspect(engine)
    if "alembic_version" not in insp.get_table_names():
        return None
    with engine.connect() as conn:
        row = conn.execute(text("SELECT version_num FROM alembic_version")).first()
    return row[0] if row else None


def _head_revision() -> str:
    """Return the head revision id by walking the script directory."""
    from alembic.script import ScriptDirectory

    cfg = db._alembic_cfg(db.make_engine("sqlite:///:memory:"))
    return ScriptDirectory.from_config(cfg).get_current_head()


def test_init_schema_empty_db_upgrades_to_head(tmp_path):
    engine = _engine_at(tmp_path)

    db.init_schema(engine)

    head = _head_revision()
    assert _alembic_version_value(engine) == head

    tables = set(inspect(engine).get_table_names()) - {"alembic_version"}
    # Sanity-check a few representative tables from each migration.
    assert "samples" in tables  # 0001
    assert "acquisitions" in tables  # 0001
    assert "tilt_series" in tables  # 0002


def test_init_schema_already_at_head_is_noop(tmp_path):
    engine = _engine_at(tmp_path)
    db.init_schema(engine)

    pre_version = _alembic_version_value(engine)
    pre_tables = set(inspect(engine).get_table_names())

    # Re-run init_schema; should be a no-op.
    db.init_schema(engine)

    assert _alembic_version_value(engine) == pre_version
    assert set(inspect(engine).get_table_names()) == pre_tables
