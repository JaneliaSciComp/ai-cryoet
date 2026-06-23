"""Tests for ``GET /filters/options`` (plan §7.2).

Seeding strategy: build raw ORM rows directly. The route only reads the
columns it lists, so we don't need full SampleRecord fidelity — and direct
ORM seeding lets us pin one sample as soft-deleted and assert its values
are absent from every options list and range bound.
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
    """Several live samples spanning both projects + both data sources, plus
    varied acquisition / tomogram / tilt-series attributes, plus one
    soft-deleted sample carrying unique-only values."""
    app, Session = _make_app(tmp_path)

    s = Session()
    try:
        # ── Live sample 1: chromatin / cryoet, type "cell" ──────────────
        s.add(orm.SampleORM(
            sample_id="live_a",
            data_source=DataSource.experimental,
            project=Project.chromatin,
            type="cell",
        ))
        s.add(orm.AcquisitionORM(
            sample_id="live_a", acquisition_id="acq1",
            microscope="Krios", pixel_size=1.5, voltage=300.0, camera="K3",
        ))
        s.add(orm.PostProcessedTomogramORM(
            sample_id="live_a", acquisition_id="acq1", tomogram_id="t1",
            voxel_size=10.0,
        ))
        s.add(orm.TiltSeriesORM(
            sample_id="live_a", acquisition_id="acq1", tilt_series_id="ts1",
        ))

        # ── Live sample 2: synapse / simulation, type "tissue" ──────────
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
        s.add(orm.PostProcessedTomogramORM(
            sample_id="live_b", acquisition_id="acq1", tomogram_id="t1",
            voxel_size=15.0,
        ))
        s.add(orm.TiltSeriesORM(
            sample_id="live_b", acquisition_id="acq1", tilt_series_id="ts1",
        ))

        # ── Live sample 3: chromatin / cryoet again — duplicates must collapse,
        # but its tomogram has a wider voxel_spacing so the range stretches.
        s.add(orm.SampleORM(
            sample_id="live_c",
            data_source=DataSource.experimental,
            project=Project.chromatin,
            type="cell",  # duplicate of live_a
        ))
        s.add(orm.AcquisitionORM(
            sample_id="live_c", acquisition_id="acq1",
            microscope="Krios",  # duplicate
            pixel_size=1.0,      # new range minimum
            voltage=300.0,       # duplicate
            camera="K3",         # duplicate
        ))
        s.add(orm.PostProcessedTomogramORM(
            sample_id="live_c", acquisition_id="acq1", tomogram_id="t1",
            voxel_size=5.0,  # new range minimum
        ))
        s.add(orm.TiltSeriesORM(
            sample_id="live_c", acquisition_id="acq1", tilt_series_id="ts1",
        ))

        # ── Soft-deleted sample: carries values that would otherwise leak
        # ("Talos" microscope, voltage=120, "GIF" camera, type "deleted_type",
        # voxel_spacing=99 (min) and 999 (max),
        # pixel_size=0.1 (min) and 99.9 (max)).
        s.add(orm.SampleORM(
            sample_id="dead",
            data_source=DataSource.experimental,
            project=Project.synapse,
            type="deleted_type",
            deleted_at=time.time(),
        ))
        s.add(orm.AcquisitionORM(
            sample_id="dead", acquisition_id="acq1",
            microscope="Talos", pixel_size=0.1, voltage=120.0, camera="GIF",
        ))
        s.add(orm.AcquisitionORM(
            sample_id="dead", acquisition_id="acq2",
            microscope="Talos", pixel_size=99.9, voltage=120.0, camera="GIF",
        ))
        s.add(orm.PostProcessedTomogramORM(
            sample_id="dead", acquisition_id="acq1", tomogram_id="t1",
            voxel_size=99.0,
        ))
        s.add(orm.PostProcessedTomogramORM(
            sample_id="dead", acquisition_id="acq2", tomogram_id="t1",
            voxel_size=999.0,
        ))
        s.add(orm.TiltSeriesORM(
            sample_id="dead", acquisition_id="acq1", tilt_series_id="ts1",
        ))
        s.add(orm.TiltSeriesORM(
            sample_id="dead", acquisition_id="acq2", tilt_series_id="ts1",
        ))

        s.commit()
    finally:
        s.close()

    return TestClient(app)


@pytest.fixture
def empty_client(tmp_path):
    """No samples at all — every list empty, every range (None, None)."""
    app, _ = _make_app(tmp_path)
    return TestClient(app)


# ── lists ────────────────────────────────────────────────────────────────


def test_lists_are_sorted_unique_and_exclude_soft_deleted(seeded_client):
    r = seeded_client.get("/filters/options")
    assert r.status_code == 200
    body = r.json()

    # All distinct, sorted ascending — soft-deleted contributions absent.
    assert body["projects"] == ["chromatin", "synapse"]
    assert body["data_sources"] == ["experimental", "simulation"]
    assert body["types"] == ["cell", "tissue"]
    # Soft-deleted "Talos" must NOT appear.
    assert body["microscopes"] == ["Arctica", "Krios"]
    assert body["voltages"] == [200.0, 300.0]
    # Soft-deleted "GIF" must NOT appear.
    assert body["cameras"] == ["Falcon4", "K3"]


def test_soft_deleted_sample_type_absent(seeded_client):
    """Specifically guard that the deleted sample's type doesn't leak."""
    r = seeded_client.get("/filters/options")
    body = r.json()
    assert "deleted_type" not in body["types"]


# ── ranges ───────────────────────────────────────────────────────────────


def test_range_bounds_reflect_live_data(seeded_client):
    r = seeded_client.get("/filters/options")
    body = r.json()

    # pixel_size across live acquisitions: {1.0, 1.5, 2.5}
    assert body["pixel_size"]["min"] == 1.0
    assert body["pixel_size"]["max"] == 2.5

    # voxel_spacing across live tomograms: {5.0, 10.0, 15.0}
    assert body["voxel_size"]["min"] == 5.0
    assert body["voxel_size"]["max"] == 15.0


def test_soft_deleted_does_not_widen_ranges(seeded_client):
    """The soft-deleted sample has extreme outliers (pixel_size=0.1/99.9,
    voxel_spacing=99/999). None of them should bleed in."""
    r = seeded_client.get("/filters/options")
    body = r.json()
    assert body["pixel_size"]["min"] != 0.1
    assert body["pixel_size"]["max"] != 99.9
    assert body["voxel_size"]["min"] != 99.0
    assert body["voxel_size"]["max"] != 999.0


# ── empty database ──────────────────────────────────────────────────────


def test_empty_database_returns_empty_lists_and_null_ranges(empty_client):
    r = empty_client.get("/filters/options")
    assert r.status_code == 200
    body = r.json()
    for key in (
        "projects", "data_sources", "types",
        "microscopes", "voltages", "cameras",
    ):
        assert body[key] == [], f"{key} should be empty"
    for key in ("pixel_size", "voxel_size"):
        assert body[key]["min"] is None
        assert body[key]["max"] is None
