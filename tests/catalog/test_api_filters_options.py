"""Tests for ``GET /filters/options`` (registry-driven, Phase 2).

Response shape is now generic: ``{categorical: {key: [str]}, ranges: {key:
{min, max}}}`` keyed by the field registry's ``key``. Seeding builds raw ORM
rows directly; one sample is pinned soft-deleted to assert its values never
leak into options or range bounds.
"""
from __future__ import annotations
import time

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from schema.schema import DataSource, Project
from catalog import db, orm
from catalog.api.deps import get_session
from catalog.api.main import create_app


def _make_app(tmp_path):
    engine = db.make_engine(f"sqlite:///{tmp_path / 'test.db'}")
    db.init_schema(engine)
    Session = sessionmaker(bind=engine, future=True, expire_on_commit=False)

    app = create_app()
    app.state.engine = engine

    def override_get_session():
        s = Session()
        try:
            yield s
        finally:
            s.close()

    app.dependency_overrides[get_session] = override_get_session
    return app, Session


@pytest.fixture
def seeded_client(tmp_path):
    """Live samples spanning both projects + sources with chromatin substrate,
    acquisition pixel_size range, plus one soft-deleted sample carrying
    unique-only values."""
    app, Session = _make_app(tmp_path)

    s = Session()
    try:
        # ── Live sample 1: chromatin / experimental ─────────────────────
        s.add(orm.SampleORM(
            sample_id="live_a",
            data_source=DataSource.experimental,
            project=Project.chromatin,
            type="cell",
        ))
        s.add(orm.ChromatinORM(sample_id="live_a", substrate="mono"))
        s.add(orm.AcquisitionORM(
            sample_id="live_a", acquisition_id="acq1",
            microscope="Krios", pixel_size=1.5, voltage=300.0, camera="K3",
        ))

        # ── Live sample 2: synapse / simulation ─────────────────────────
        s.add(orm.SampleORM(
            sample_id="live_b",
            data_source=DataSource.simulation,
            project=Project.synapse,
            type="tissue",
        ))
        s.add(orm.AcquisitionORM(
            sample_id="live_b", acquisition_id="acq1",
            microscope="Arctica", pixel_size=2.5, voltage=200.0,
            camera="Falcon4",
        ))

        # ── Live sample 3: chromatin again, wider substrate + pixel_size ─
        s.add(orm.SampleORM(
            sample_id="live_c",
            data_source=DataSource.experimental,
            project=Project.chromatin,
            type="cell",
        ))
        s.add(orm.ChromatinORM(sample_id="live_c", substrate="tri"))
        s.add(orm.AcquisitionORM(
            sample_id="live_c", acquisition_id="acq1",
            microscope="Krios", pixel_size=1.0, voltage=300.0, camera="K3",
        ))

        # ── Soft-deleted sample: values that must never leak ────────────
        s.add(orm.SampleORM(
            sample_id="dead",
            data_source=DataSource.experimental,
            project=Project.synapse,
            type="deleted_type",
            deleted_at=time.time(),
        ))
        s.add(orm.ChromatinORM(sample_id="dead", substrate="DELETED_SUBSTRATE"))
        s.add(orm.AcquisitionORM(
            sample_id="dead", acquisition_id="acq1",
            microscope="Talos", pixel_size=0.1, voltage=120.0, camera="GIF",
        ))
        s.add(orm.AcquisitionORM(
            sample_id="dead", acquisition_id="acq2",
            microscope="Talos", pixel_size=99.9, voltage=120.0, camera="GIF",
        ))

        s.commit()
    finally:
        s.close()

    return TestClient(app)


@pytest.fixture
def empty_client(tmp_path):
    """No samples at all — categorical lists empty, ranges (None, None)."""
    app, _ = _make_app(tmp_path)
    return TestClient(app)


# ── shape ──────────────────────────────────────────────────────────────────


def test_response_shape(seeded_client):
    body = seeded_client.get("/filters/options").json()
    assert isinstance(body["categorical"], dict)
    assert isinstance(body["ranges"], dict)
    # text fields land in categorical, range fields in ranges, keyed by key.
    assert "substrate" in body["categorical"]
    assert "lab_name" in body["categorical"]
    assert "pixel_size" in body["ranges"]
    # existence/boolean fields produce no options.
    assert "has_raw_tomogram" not in body["categorical"]
    assert "phase_plate" not in body["categorical"]


# ── categorical ──────────────────────────────────────────────────────────


def test_categorical_values_sorted_unique_and_scoped(seeded_client):
    cat = seeded_client.get("/filters/options").json()["categorical"]
    # chromatin substrate, joined through samples — deleted value absent.
    assert cat["substrate"] == ["mono", "tri"]
    assert "DELETED_SUBSTRATE" not in cat["substrate"]
    # sample-direct enums come through .value, deleted contributions absent.
    assert cat["project"] == ["chromatin", "synapse"]
    assert cat["data_source"] == ["experimental", "simulation"]
    assert cat["type"] == ["cell", "tissue"]
    assert "deleted_type" not in cat["type"]
    # acquisition-side, joined through samples — "Talos"/"GIF" absent.
    assert cat["microscope"] == ["Arctica", "Krios"]
    assert cat["camera"] == ["Falcon4", "K3"]


# ── ranges ───────────────────────────────────────────────────────────────


def test_range_bounds_reflect_live_data_and_exclude_deleted(seeded_client):
    ranges = seeded_client.get("/filters/options").json()["ranges"]
    # pixel_size across live acquisitions: {1.0, 1.5, 2.5}; deleted 0.1/99.9 out.
    assert ranges["pixel_size"]["min"] == 1.0
    assert ranges["pixel_size"]["max"] == 2.5


# ── empty database ──────────────────────────────────────────────────────


def test_empty_database(empty_client):
    body = empty_client.get("/filters/options").json()
    assert body["categorical"]["substrate"] == []
    assert body["categorical"]["microscope"] == []
    assert body["ranges"]["pixel_size"]["min"] is None
    assert body["ranges"]["pixel_size"]["max"] is None
