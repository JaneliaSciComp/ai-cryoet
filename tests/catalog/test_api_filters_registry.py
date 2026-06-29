"""Phase 1 registry-driven filter coverage for ``GET /samples``.

Exercises one representative case per registry kind/table beyond the legacy
sample/acquisition cases in ``test_api_filters.py``:
  * sample-direct text IN (lab_name)
  * 1:1 sub-entity text IN + range (chromatin substrate / linker_length_bp)
  * 1:1 sub-entity via EXISTS for dataset_type (simulation)
  * label 1:N per-row AND (two facets must hold on the SAME label row)
  * acquisition scalar text IN + range on a registry-only field (resolution)
  * cross-facet AND, OR-within-facet
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from catalog import db, orm
from catalog.api.deps import get_session
from catalog.api.main import create_app
from schema.schema import DataSource, DatasetType, LabName, Project


@pytest.fixture
def client(tmp_path):
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

    s = Session()
    try:
        s.add_all([
            orm.SampleORM(sample_id="s_coll", data_source=DataSource.experimental,
                          project=Project.chromatin, lab_name=LabName.collepardo),
            orm.SampleORM(sample_id="s_villa", data_source=DataSource.experimental,
                          project=Project.chromatin, lab_name=LabName.villa),
            orm.SampleORM(sample_id="s_sim", data_source=DataSource.simulation,
                          project=Project.chromatin, lab_name=LabName.rosen),
        ])
        # chromatin sub-entity rows
        s.add_all([
            orm.ChromatinORM(sample_id="s_coll", substrate="mononucleosome",
                             linker_length_bp=30.0),
            orm.ChromatinORM(sample_id="s_villa", substrate="dinucleosome",
                             linker_length_bp=60.0),
            orm.ChromatinORM(sample_id="s_sim", substrate="mononucleosome",
                             linker_length_bp=None),
        ])
        # simulation sub-entity (dataset_type)
        s.add(orm.SimulationORM(sample_id="s_sim", dataset_type=DatasetType.bulk))
        # labels: s_coll has two rows; per-row AND must match on ONE row.
        s.add_all([
            orm.LabelORM(sample_id="s_coll", ordinal=0,
                         conjugation="streptavidin", fluorophore="alexa"),
            orm.LabelORM(sample_id="s_coll", ordinal=1,
                         conjugation="antibody", fluorophore="gfp"),
            # s_villa: the two facets exist but on DIFFERENT rows -> no match.
            orm.LabelORM(sample_id="s_villa", ordinal=0,
                         conjugation="streptavidin", fluorophore="gfp"),
            orm.LabelORM(sample_id="s_villa", ordinal=1,
                         conjugation="antibody", fluorophore="alexa"),
        ])
        # acquisitions with registry-only scalar fields
        s.add_all([
            orm.AcquisitionORM(sample_id="s_coll", acquisition_id="a1",
                               resolution=3.0, energy_filter="BioQuantum"),
            orm.AcquisitionORM(sample_id="s_villa", acquisition_id="a1",
                               resolution=8.0, energy_filter="none"),
        ])
        s.commit()
    finally:
        s.close()
    return TestClient(app)


def _ids(r):
    return {s["sample_id"] for s in r.json()}


def test_sample_direct_lab_name_in(client):
    assert _ids(client.get("/samples", params={"lab_name": "collepardo"})) == {"s_coll"}


def test_lab_name_or_within_facet(client):
    r = client.get("/samples", params=[("lab_name", "collepardo"), ("lab_name", "villa")])
    assert _ids(r) == {"s_coll", "s_villa"}


def test_chromatin_substrate_in(client):
    assert _ids(client.get("/samples", params={"substrate": "dinucleosome"})) == {"s_villa"}


def test_chromatin_range_null_tolerant(client):
    # linker_length_bp >= 50 -> s_villa (60) plus s_sim (NULL passes).
    r = client.get("/samples", params={"linker_length_bp_min": 50})
    assert _ids(r) == {"s_villa", "s_sim"}


def test_dataset_type_via_simulation_exists(client):
    assert _ids(client.get("/samples", params={"dataset_type": "bulk"})) == {"s_sim"}


def test_label_per_row_and(client):
    """conjugation=antibody AND fluorophore=gfp must hold on the SAME label row.

    s_coll has them on ordinal 1 (match); s_villa has them split across rows
    (no match).
    """
    r = client.get("/samples", params={"conjugation": "antibody", "fluorophore": "gfp"})
    assert _ids(r) == {"s_coll"}


def test_acquisition_resolution_range(client):
    assert _ids(client.get("/samples", params={"resolution_max": 5.0})) == {"s_coll"}


def test_cross_facet_and(client):
    # chromatin substrate (sample sub-entity) AND acquisition energy_filter.
    r = client.get(
        "/samples",
        params={"substrate": "mononucleosome", "energy_filter": "BioQuantum"},
    )
    assert _ids(r) == {"s_coll"}
