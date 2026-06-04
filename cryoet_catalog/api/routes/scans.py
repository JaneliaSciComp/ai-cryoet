"""GET /scans, /scans/latest, /scans/latest/warnings, /scans/latest/samples,
/scans/{scan_run_id}."""
from __future__ import annotations
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from cryoet_catalog import orm
from cryoet_catalog.api.deps import get_session
from cryoet_catalog.api.schemas import ScanOut, ScanSampleOut, SampleWarningsGroup

router = APIRouter()


def _enum_val(v):
    """Coerce a possibly-enum value to its string value."""
    return v.value if hasattr(v, "value") else v


def _latest_completed_scan_id(session: Session) -> str | None:
    """scan_run_id of the most recent completed scan, or None if there is none."""
    return session.execute(
        select(orm.ScansORM.scan_run_id)
        .where(orm.ScansORM.status == "completed")
        .order_by(orm.ScansORM.ended_at.desc())
        .limit(1)
    ).scalar_one_or_none()


def _to_out(row: orm.ScansORM) -> ScanOut:
    return ScanOut(
        scan_run_id=row.scan_run_id,
        started_at=row.started_at, ended_at=row.ended_at,
        root=row.root, status=row.status,
        samples_upserted=row.samples_upserted,
        samples_skipped=row.samples_skipped,
        samples_failed=row.samples_failed,
    )


@router.get("", response_model=list[ScanOut])
def list_scans(session: Session = Depends(get_session)):
    rows = session.execute(
        select(orm.ScansORM).order_by(orm.ScansORM.started_at.desc())
    ).scalars().all()
    return [_to_out(r) for r in rows]


@router.get("/latest", response_model=ScanOut)
def get_latest_completed(session: Session = Depends(get_session)):
    row = session.execute(
        select(orm.ScansORM)
        .where(orm.ScansORM.status == "completed")
        .order_by(orm.ScansORM.ended_at.desc())
        .limit(1)
    ).scalars().first()
    if row is None:
        raise HTTPException(status_code=404, detail="no completed scan")
    return _to_out(row)


@router.get("/latest/warnings", response_model=list[SampleWarningsGroup])
def get_latest_scan_warnings(session: Session = Depends(get_session)):
    """Warnings from the latest completed scan, grouped by sample.

    Returns an empty list when no completed scan exists yet (mirrors the
    per-sample ``/samples/{id}/warnings`` empty-on-no-scan behavior).
    """
    latest = _latest_completed_scan_id(session)
    if latest is None:
        return []

    rows = session.execute(
        select(orm.ScanWarningsORM.sample_id, orm.ScanWarningsORM.message)
        .where(orm.ScanWarningsORM.scan_run_id == latest)
        .order_by(orm.ScanWarningsORM.sample_id, orm.ScanWarningsORM.id)
    ).all()

    grouped: dict[str, list[str]] = {}
    for sample_id, message in rows:
        grouped.setdefault(sample_id, []).append(message)
    return [
        SampleWarningsGroup(sample_id=sid, warnings=msgs)
        for sid, msgs in grouped.items()
    ]


@router.get("/latest/samples", response_model=list[ScanSampleOut])
def get_latest_scan_samples(
    outcome: Literal["upserted", "skipped", "failed"] = Query(...),
    session: Session = Depends(get_session),
):
    """Samples with the given outcome in the latest completed scan.

    Sample metadata (data_source/project/type) is joined from ``samples`` when
    the row still exists; failed samples that were never persisted come back
    with null metadata and an error ``detail``. Empty list when no completed
    scan exists.
    """
    latest = _latest_completed_scan_id(session)
    if latest is None:
        return []

    # Per-sample warning count for the same scan, so the table can show it.
    warn_count_sq = (
        select(
            orm.ScanWarningsORM.sample_id.label("sample_id"),
            func.count().label("wc"),
        )
        .where(orm.ScanWarningsORM.scan_run_id == latest)
        .group_by(orm.ScanWarningsORM.sample_id)
        .subquery()
    )

    rows = session.execute(
        select(
            orm.ScanSamplesORM.sample_id,
            orm.ScanSamplesORM.detail,
            orm.SampleORM.data_source,
            orm.SampleORM.project,
            orm.SampleORM.type,
            func.coalesce(warn_count_sq.c.wc, 0),
        )
        .outerjoin(
            orm.SampleORM,
            orm.SampleORM.sample_id == orm.ScanSamplesORM.sample_id,
        )
        .outerjoin(
            warn_count_sq,
            warn_count_sq.c.sample_id == orm.ScanSamplesORM.sample_id,
        )
        .where(orm.ScanSamplesORM.scan_run_id == latest)
        .where(orm.ScanSamplesORM.outcome == outcome)
        .order_by(orm.ScanSamplesORM.sample_id)
    ).all()

    return [
        ScanSampleOut(
            sample_id=r[0],
            detail=r[1],
            data_source=_enum_val(r[2]),
            project=_enum_val(r[3]),
            type=r[4],
            warning_count=r[5],
        )
        for r in rows
    ]


# NOTE: must be declared after ``/latest`` — FastAPI matches routes in
# registration order, and a bare ``/{scan_run_id}`` would otherwise swallow
# the literal ``/latest`` path.
@router.get("/{scan_run_id}", response_model=ScanOut)
def get_scan(scan_run_id: str, session: Session = Depends(get_session)):
    row = session.get(orm.ScansORM, scan_run_id)
    if row is None:
        raise HTTPException(status_code=404, detail="scan not found")
    return _to_out(row)
