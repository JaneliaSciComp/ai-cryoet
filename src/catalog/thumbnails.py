"""Pre-generate per-acquisition tilt-series thumbnails into a filesystem cache.

One thumbnail per acquisition — the median/middle tilt-series image (the same
image the detail pages show), rendered from the acquisition's first available
tilt-series source (zarr → ``.st``/``.mrc`` → raw ``Frames/``). The
representative thumbnail for a sample is the first acquisition (by id) that
produced one.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path

from loguru import logger

# Cache thumbnails smaller than the on-demand preview (800px); they only ever
# render in table rows and detail-page heroes.
THUMBNAIL_WIDTH = 512


@dataclass(frozen=True)
class AcqRef:
    """A single acquisition's tilt-series image sources for thumbnailing.

    ``zarr_path``/``st_path`` come from the acquisition's first tilt series
    that has them; ``frames_dir`` is the acquisition's raw ``Frames/`` dir
    (the shared fallback). Any may be ``None`` — rendering tries them in order.
    """

    acquisition_id: str
    zarr_path: str | None
    st_path: str | None
    frames_dir: str | None


@dataclass(frozen=True)
class AcqThumbResult:
    """Per-acquisition outcome of a thumbnail (re)generation pass.

    ``status`` is ``"ok"`` when a preview rendered, ``"missing_source"`` when
    the acquisition had no zarr/st/frames source to render from, and
    ``"render_failed"`` when a source was present but rendering raised.
    ``source_kind``/``source_path`` record the source that actually rendered
    (post-fallback); ``relpath`` is the cache-relative PNG path on success.
    """

    acquisition_id: str
    status: str  # "ok" | "missing_source" | "render_failed"
    source_kind: str | None = None
    source_path: str | None = None
    relpath: str | None = None


@dataclass(frozen=True)
class ThumbnailRunResult:
    """Result of :func:`generate_thumbnails` for one sample.

    ``representative`` is the sample's representative thumbnail relpath (first
    acquisition by id that produced one); ``per_acq`` is the per-acquisition
    detail used to write thumbnail provenance to ``acquisition_scan_status``.
    """

    representative: str | None
    per_acq: list[AcqThumbResult]


def _safe_segment(value: str) -> str:
    if not value or "/" in value or "\\" in value or value in (".", ".."):
        raise ValueError(f"unsafe id segment: {value!r}")
    return value


def _relpath(sample_id: str, acquisition_id: str) -> str:
    return "/".join((
        _safe_segment(sample_id),
        _safe_segment(acquisition_id) + ".png",
    ))


def _render_one(ref: AcqRef, dest: Path) -> tuple[bool, str | None, str | None]:
    """Render one acquisition's thumbnail to ``dest``.

    Returns ``(ok, source_kind, source_path)`` — the source the renderer
    actually used (post-fallback) so the caller can record real provenance,
    not the pre-call guess.
    """
    from catalog.imaging._tilt_series import (
        render_tilt_series_median_png_with_source,
    )

    guess = "zarr" if ref.zarr_path else "st" if ref.st_path else "frames"
    logger.debug(
        "    rendering thumbnail for {} (source≈{})", ref.acquisition_id, guess
    )
    started = time.perf_counter()
    try:
        png, source_kind, source_path = render_tilt_series_median_png_with_source(
            zarr_path=ref.zarr_path,
            st_path=ref.st_path,
            frames_dir=ref.frames_dir,
            width=THUMBNAIL_WIDTH,
        )
    except Exception as e:
        logger.warning(
            "thumbnail render failed for acquisition {} (source≈{}): {}",
            ref.acquisition_id,
            guess,
            e,
        )
        return False, None, None
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(".png.tmp")
    tmp.write_bytes(png)
    tmp.replace(dest)
    logger.debug(
        "    rendered {} in {:.1f}s ({} bytes)",
        ref.acquisition_id,
        time.perf_counter() - started,
        len(png),
    )
    return True, source_kind, source_path


def generate_thumbnails(
    sample_id: str,
    acqs: list[AcqRef],
    thumbnail_root: Path,
    *,
    skip_existing: bool = False,
) -> ThumbnailRunResult:
    """Render each acquisition's thumbnail; return representative + per-acq detail.

    On ``skip_existing`` an on-disk thumbnail is reused (status ``ok``) without
    re-rendering — its source provenance is left ``None`` for the caller to
    preserve from the prior record (a heal doesn't re-derive the source).
    """
    generated: list[str] = []
    per_acq: list[AcqThumbResult] = []
    for ref in sorted(acqs, key=lambda r: r.acquisition_id):
        rel = _relpath(sample_id, ref.acquisition_id)
        dest = thumbnail_root / rel
        if not (ref.zarr_path or ref.st_path or ref.frames_dir):
            per_acq.append(
                AcqThumbResult(ref.acquisition_id, status="missing_source")
            )
            continue
        if skip_existing and dest.is_file():
            generated.append(rel)
            per_acq.append(
                AcqThumbResult(ref.acquisition_id, status="ok", relpath=rel)
            )
            continue
        ok, source_kind, source_path = _render_one(ref, dest)
        if ok:
            generated.append(rel)
            per_acq.append(
                AcqThumbResult(
                    ref.acquisition_id,
                    status="ok",
                    source_kind=source_kind,
                    source_path=source_path,
                    relpath=rel,
                )
            )
        else:
            per_acq.append(
                AcqThumbResult(ref.acquisition_id, status="render_failed")
            )

    return ThumbnailRunResult(
        representative=representative_relpath(generated), per_acq=per_acq
    )


def representative_relpath(generated: list[str]) -> str | None:
    """The sample's representative thumbnail: first acquisition (by id) with one.

    ``generated`` is the relpath list in acquisition-id order, so the first
    entry is the representative.
    """
    return generated[0] if generated else None


def _acq_ref(acquisition_id: str, path: str | None, tilt_series) -> AcqRef:
    """Build an :class:`AcqRef` from an acquisition's path + tilt-series rows."""
    zarr_path = next((ts.zarr_path for ts in tilt_series if ts.zarr_path), None)
    st_path = next((ts.st_path for ts in tilt_series if ts.st_path), None)
    frames_dir = str(Path(path) / "Frames") if path else None
    return AcqRef(acquisition_id, zarr_path, st_path, frames_dir)


def refs_from_record(record) -> list[AcqRef]:
    return [
        _acq_ref(acq_id, acq.acquisition.path, acq.tilt_series)
        for acq_id, acq in record.acquisitions.items()
    ]


def refs_from_db(session, sample_id: str) -> list[AcqRef]:
    from catalog import orm
    from sqlalchemy import select

    ts_by_acq: dict[str, list] = {}
    for ts in session.execute(
        select(orm.TiltSeriesORM).where(orm.TiltSeriesORM.sample_id == sample_id)
    ).scalars():
        ts_by_acq.setdefault(ts.acquisition_id, []).append(ts)

    refs: list[AcqRef] = []
    for acq in session.execute(
        select(orm.AcquisitionORM).where(orm.AcquisitionORM.sample_id == sample_id)
    ).scalars():
        refs.append(
            _acq_ref(acq.acquisition_id, acq.path, ts_by_acq.get(acq.acquisition_id, []))
        )
    return refs
