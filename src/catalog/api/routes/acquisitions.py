"""Acquisition-level rendering endpoints.

The tilt geometry (the full per-image tilt-angle list) is a property of the
*acquisition* — it is shared by all of the acquisition's tilt series and is
parsed from the MDOC(s) under ``Frames/``. The polar plot therefore lives here
rather than on any one tilt series (it used to be a per-series
``/tilt-series/.../polar.png`` route).
"""
from __future__ import annotations

from functools import lru_cache

from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.orm import Session

from catalog import orm
from catalog.api.deps import get_session

router = APIRouter()


def _lookup_acquisition(
    session: Session, sample_id: str, acquisition_id: str
) -> orm.AcquisitionORM:
    sample = session.get(orm.SampleORM, sample_id)
    if sample is None or sample.deleted_at is not None:
        raise HTTPException(status_code=404, detail="sample not found")
    row = session.get(orm.AcquisitionORM, (sample_id, acquisition_id))
    if row is None:
        raise HTTPException(status_code=404, detail="acquisition not found")
    return row


@lru_cache(maxsize=128)
def _cached_polar_png(
    sample_id: str,
    acquisition_id: str,
    version: int,
    angles_tuple: tuple[float, ...],
) -> bytes:
    """LRU-cache the polar render keyed on the cached angles + render version.

    ``angles_tuple`` is in the key so a re-scan that changes the cached angles
    invalidates the entry.
    """
    from catalog.imaging._polar import render_polar_png

    return render_polar_png(list(angles_tuple))


@router.get("/{sample_id}/{acquisition_id}/polar.png")
async def acquisition_polar(
    sample_id: str,
    acquisition_id: str,
    session: Session = Depends(get_session),
):
    """Semicircular polar plot of the acquisition's cached ``tilt_angles``.

    422 if the acquisition has no cached angles.
    """
    from catalog.imaging._polar import POLAR_RENDER_VERSION

    row = _lookup_acquisition(session, sample_id, acquisition_id)
    angles = row.tilt_angles or []
    if not angles:
        raise HTTPException(status_code=422, detail="no cached tilt angles")

    png_bytes = await run_in_threadpool(
        _cached_polar_png,
        sample_id,
        acquisition_id,
        POLAR_RENDER_VERSION,
        tuple(float(a) for a in angles),
    )
    return Response(
        content=png_bytes,
        media_type="image/png",
        headers={"Cache-Control": "public, max-age=3600"},
    )
