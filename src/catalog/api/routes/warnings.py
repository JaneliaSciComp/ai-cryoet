"""GET /samples/{sample_id}/warnings."""
from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from catalog import orm
from catalog.api.deps import get_session
from catalog.api.schemas import WarningOut

router = APIRouter()


@router.get("/{sample_id}/warnings", response_model=list[WarningOut])
def get_sample_warnings(sample_id: str, session: Session = Depends(get_session)):
    """Outstanding issues for this sample (current state).

    Reads the entity-keyed ``issues`` table directly (resolved_at IS NULL)
    rather than the latest completed scan, so a sample skipped in the latest
    scan still surfaces its still-outstanding issues. Maps each issue to the
    legacy ``WarningOut`` shape used by the per-sample detail block.
    """
    sample = session.get(orm.SampleORM, sample_id)
    if sample is None or sample.deleted_at is not None:
        raise HTTPException(status_code=404, detail="sample not found")

    rows = session.execute(
        select(orm.IssueORM)
        .where(orm.IssueORM.sample_id == sample_id)
        .where(orm.IssueORM.resolved_at.is_(None))
        .order_by(orm.IssueORM.id)
    ).scalars().all()
    return [
        WarningOut(
            id=r.id,
            sample_id=r.sample_id,
            category=r.category,
            location=r.location,
            message=r.message,
            detected_at=r.first_seen_at,
            scan_run_id=r.last_seen_run_id,
        )
        for r in rows
    ]
