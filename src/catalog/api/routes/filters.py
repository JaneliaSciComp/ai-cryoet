"""GET /filters/options — categorical option lists and numeric ranges for the
sample filter drawer. Registry-driven (Phase 2): iterates ``FIELDS`` and runs
one DISTINCT (text) or MIN/MAX (range) per field, scoped to live samples.
"""
from __future__ import annotations
from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from catalog import orm
from catalog.api.deps import get_session
from catalog.api.filter_fields import FIELDS, Field
from catalog.api.schemas import FiltersOptionsOut, RangeOut

router = APIRouter()

# table __tablename__ -> ORM class, for every table the registry references.
_TABLES = {
    "samples": orm.SampleORM,
    "chromatin": orm.ChromatinORM,
    "labels": orm.LabelORM,
    "fiducial": orm.FiducialORM,
    "simulation": orm.SimulationORM,
    "freezing": orm.FreezingORM,
    "milling": orm.MillingORM,
    "acquisitions": orm.AcquisitionORM,
    "tilt_series": orm.TiltSeriesORM,
    "raw_tomograms": orm.RawTomogramORM,
    "post_processed_tomograms": orm.PostProcessedTomogramORM,
    "annotations": orm.AnnotationORM,
}


def _enum_value(v):
    """Coerce a SQLAlchemy Enum value to its string (.value) form."""
    return v.value if hasattr(v, "value") else v


def _scoped(stmt, table: str):
    """Scope a select to live samples. Sample-direct columns need no join;
    every sub-entity / acquisition-side table joins to ``samples`` on
    ``sample_id`` and filters ``samples.deleted_at IS NULL``."""
    if table != "samples":
        model = _TABLES[table]
        stmt = stmt.join(
            orm.SampleORM, orm.SampleORM.sample_id == model.sample_id
        )
    return stmt.where(orm.SampleORM.deleted_at.is_(None))


@router.get("/options", response_model=FiltersOptionsOut)
def get_filter_options(session: Session = Depends(get_session)):
    """Return distinct values + numeric ranges for the sample filter drawer.

    All queries are scoped to live samples (``samples.deleted_at IS NULL``);
    soft-deleted samples never contribute to options or range bounds.
    """
    categorical: dict[str, list[str]] = {}
    ranges: dict[str, RangeOut] = {}

    for f in FIELDS:  # type: Field
        # existence/boolean need no options; existence.column is a predicate id,
        # not a real column, so skip before resolving the attribute.
        if f.kind not in ("text", "range"):
            continue
        col = getattr(_TABLES[f.table], f.column)
        if f.kind == "text":
            rows = session.execute(
                _scoped(select(col), f.table).where(col.is_not(None)).distinct()
            ).scalars().all()
            # ponytail: the JSON facets (linker_pattern, nucleosome_footprint,
            # label_aunp_size_nm) store a list/float; SELECT DISTINCT returns
            # the stored JSON/string form. str() it so options match Phase 1's
            # verbatim IN(...) exactly. Plain enums/strings str() to themselves.
            categorical[f.key] = sorted(str(_enum_value(v)) for v in rows)
        elif f.kind == "range":
            lo, hi = session.execute(
                _scoped(select(func.min(col), func.max(col)), f.table)
                .where(col.is_not(None))
            ).one()
            ranges[f.key] = RangeOut(min=lo, max=hi)
        # existence / boolean: no options.

    return FiltersOptionsOut(categorical=categorical, ranges=ranges)
