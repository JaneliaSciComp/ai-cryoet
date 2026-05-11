"""Alembic-specific tests covering autogen drift, upgrade/downgrade, and
pre-MVP DB upgrade integrity.

These tests live in the ``catalog`` env (alembic is part of
``feature.catalog.dependencies``); the bare ``test`` env can't import
alembic, so the whole module is skipped there.
"""

from __future__ import annotations

import pytest

pytest.importorskip("alembic")
pytest.importorskip("sqlalchemy")

from pathlib import Path  # noqa: E402

from alembic import command  # noqa: E402
from alembic.autogenerate import compare_metadata  # noqa: E402
from alembic.runtime.migration import MigrationContext  # noqa: E402
from sqlalchemy import inspect, text  # noqa: E402

from cryoet_catalog import db  # noqa: E402
from cryoet_catalog.orm import Base  # noqa: E402


def _engine_at(tmp_path: Path, name: str = "cat.db"):
    return db.make_engine(f"sqlite:///{tmp_path / name}")


# ---------------------------------------------------------------------------
# 1. autogenerate-empty-at-head
# ---------------------------------------------------------------------------


def test_autogenerate_empty_at_head(tmp_path):
    """Running autogenerate against a head-state DB must produce no ops.

    Catches forgotten revisions when the ORM is changed without a new
    revision file.
    """
    engine = _engine_at(tmp_path)
    cfg = db._alembic_cfg(engine)
    command.upgrade(cfg, "head")

    with engine.connect() as conn:
        ctx = MigrationContext.configure(
            conn,
            opts={"compare_type": True, "render_as_batch": True},
        )
        diff = compare_metadata(ctx, Base.metadata)

    assert diff == [], (
        f"ORM has drifted from head revision; pending autogenerate diff: {diff!r}"
    )


# ---------------------------------------------------------------------------
# 2. upgrade/downgrade roundtrip
# ---------------------------------------------------------------------------


def test_upgrade_downgrade_roundtrip(tmp_path):
    """Empty SQLite → upgrade head → downgrade -1 → upgrade head must work."""
    engine = _engine_at(tmp_path)
    cfg = db._alembic_cfg(engine)

    command.upgrade(cfg, "head")
    head_tables = set(inspect(engine).get_table_names())
    assert "tilt_series" in head_tables  # 0002 added this

    command.downgrade(cfg, "-1")
    after_down_tables = set(inspect(engine).get_table_names())
    assert "tilt_series" not in after_down_tables
    # 0001 baseline tables still present (sanity check, not exhaustive).
    assert "samples" in after_down_tables
    assert "acquisitions" in after_down_tables

    command.upgrade(cfg, "head")
    assert "tilt_series" in set(inspect(engine).get_table_names())


# ---------------------------------------------------------------------------
# 3. pre-MVP DB upgrade preserves rows
# ---------------------------------------------------------------------------


def test_pre_mvp_upgrade_preserves_rows(tmp_path):
    """Seed an SQLite at 0001 with rows in each pre-existing table, upgrade
    head, assert per-table row counts are preserved.

    Catches `render_as_batch` data loss on the 0002 ALTER paths.
    """
    engine = _engine_at(tmp_path)
    cfg = db._alembic_cfg(engine)

    # Stamp at 0001 baseline only — no 0002 columns yet.
    command.upgrade(cfg, "0001")

    seeds = {
        "samples": [
            {
                "sample_id": "s1",
                "data_source": "cryoet",
                "project": "chromatin",
                "type": None,
                "cell_type": None,
                "description": None,
                "deleted_at": None,
            }
        ],
        "scans": [
            {
                "scan_run_id": "run-1",
                "started_at": 1.0,
                "ended_at": 2.0,
                "root": "/tmp/x",
                "status": "completed",
                "samples_upserted": 1,
                "samples_skipped": 0,
                "samples_failed": 0,
            }
        ],
        "acquisitions": [
            {
                "sample_id": "s1",
                "acquisition_id": "a1",
                "resolution": None,
                "tilt_spacing": None,
                "defocus_range": None,
                "energy_filter": None,
                "phase_plate": None,
                "microscope": "Krios",
                "pixel_size": 1.0,
                "dose_per_tilt": None,
                "total_dose": None,
                "tilt_min": -60.0,
                "tilt_max": 60.0,
                "tilt_axis": 84.0,
                "defocus_per_image": None,
                "date_collected": None,
                "voltage": 300.0,
                "energy_filter_slit_width": None,
                "frame_count": None,
                "camera": "K3",
            }
        ],
        "tomograms": [
            {
                "sample_id": "s1",
                "acquisition_id": "a1",
                "tomogram_id": "t1",
                "pipeline": None,
                "software": None,
                "voxel_bin": None,
                "derived_from": "[]",
                "is_raw": True,
                "image_size_x": 4096,
                "image_size_y": 4096,
                "image_size_z": 200,
                "mrc_path": "/tmp/x/t1.mrc",
                "zarr_path": None,
                "zarr_axes": None,
                "zarr_scale": None,
                "voxel_spacing_angstrom": 4.4,
                "voxel_spacing_angstrom_implied": None,
            }
        ],
        "annotations": [
            {
                "sample_id": "s1",
                "acquisition_id": "a1",
                "annotation_id": "ann1",
                "type": "membrane",
                "target_tomogram": "t1",
                "files": "[]",
            }
        ],
        "chromatin": [
            {
                "sample_id": "s1",
                "substrate": None,
                "linker_length_bp": None,
                "linker_pattern": None,
                "linker_distribution": None,
                "buffer": None,
                "ptm": None,
                "histone_variants": None,
                "transcription_factors": None,
                "nucleosome_count": None,
                "dna_length_bp": None,
                "nucleosome_uM": None,
                "sequence_identity": None,
                "nucleosome_footprint": None,
                "linker_length_fraction": None,
            }
        ],
        "extras": [
            {
                "entity_type": "sample",
                "entity_pk_json": '["s1"]',
                "key": "kx",
                "sample_id": "s1",
                "value_json": '"vx"',
            }
        ],
        "scan_state": [
            {
                "path": "/tmp/x/sample.toml",
                "sample_id": "s1",
                "mtime": 1.0,
                "last_scanned": 2.0,
                "content_hash": None,
            }
        ],
        "scan_warnings": [
            {
                "id": 1,
                "sample_id": "s1",
                "category": "test",
                "location": "/tmp/x",
                "message": "hi",
                "detected_at": 1.0,
                "scan_run_id": "run-1",
            }
        ],
        "catalog_meta": [
            {"id": 1, "data_root": "/tmp/x", "updated_at": 1.0},
        ],
    }

    # Insert rows. We use raw SQL via SA so we don't depend on the post-MVP
    # ORM (which has columns 0001 doesn't have yet).
    with engine.begin() as conn:
        for table, rows in seeds.items():
            for row in rows:
                cols = ", ".join(row.keys())
                placeholders = ", ".join(f":{k}" for k in row.keys())
                conn.execute(
                    text(f"INSERT INTO {table} ({cols}) VALUES ({placeholders})"),
                    row,
                )

    # Snapshot per-table row counts.
    pre_counts = {}
    with engine.connect() as conn:
        for table in seeds:
            pre_counts[table] = conn.execute(
                text(f"SELECT COUNT(*) FROM {table}")
            ).scalar_one()

    # Apply 0002.
    command.upgrade(cfg, "head")

    post_counts = {}
    with engine.connect() as conn:
        for table in seeds:
            post_counts[table] = conn.execute(
                text(f"SELECT COUNT(*) FROM {table}")
            ).scalar_one()

    assert pre_counts == post_counts, (
        f"row counts changed across upgrade: pre={pre_counts}, post={post_counts}"
    )

    # New columns are present and NULL on legacy rows.
    insp = inspect(engine)
    tomo_cols = {c["name"] for c in insp.get_columns("tomograms")}
    assert "size_bytes" in tomo_cols
    acq_cols = {c["name"] for c in insp.get_columns("acquisitions")}
    assert "path" in acq_cols
    assert "tilt_series" in set(insp.get_table_names())

    with engine.connect() as conn:
        sb = conn.execute(text("SELECT size_bytes FROM tomograms")).scalar_one()
        ap = conn.execute(text("SELECT path FROM acquisitions")).scalar_one()
    assert sb is None
    assert ap is None


# ---------------------------------------------------------------------------
# 4. DDL-drift sanity: create_all == upgrade head
# ---------------------------------------------------------------------------


def test_create_all_matches_upgrade_head(tmp_path):
    """``Base.metadata.create_all`` must produce the same table set as
    ``alembic upgrade head`` from empty.

    If this fails, someone added/removed an ORM table without a matching
    revision (or vice versa). ``create_all`` is no longer the lifecycle
    entry point — this test is the safety net keeping the two paths in sync.
    """
    engine_create = _engine_at(tmp_path, "create.db")
    Base.metadata.create_all(engine_create)
    create_tables = set(inspect(engine_create).get_table_names())

    engine_upgrade = _engine_at(tmp_path, "upgrade.db")
    cfg = db._alembic_cfg(engine_upgrade)
    command.upgrade(cfg, "head")
    upgrade_tables = set(inspect(engine_upgrade).get_table_names()) - {
        "alembic_version"
    }

    assert create_tables == upgrade_tables, (
        f"create_all vs. upgrade head differ: "
        f"only-in-create_all={create_tables - upgrade_tables}, "
        f"only-in-upgrade-head={upgrade_tables - create_tables}"
    )
