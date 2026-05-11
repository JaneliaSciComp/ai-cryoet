"""Tilt-series parser.

For each ``.mdoc`` file in a ``frames_dir`` (direct children), emit one
``TiltSeries`` Pydantic record. Multi-MDOC acquisitions yield multiple rows;
the existing acquisition-level MDOC parser (``parse_acquisition_mdocs``)
only consumes the alphabetically-first MDOC for acquisition metadata, so
this parser is the only path that catalogues *every* tilt series.

``microscope`` and ``camera`` are intentionally **not** populated from the
MDOC — those come from ``acquisition.toml`` (plan decision §11.14).

MDOC-stem collisions (two MDOCs in the same acquisition that share a
``.stem``) are auto-disambiguated by appending the parent-dir name, then a
numeric suffix if still colliding; each collision is reported back so the
assembler can emit a ``tilt_series_id_collision`` scan warning (§11.23).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from cryoet_schema import TiltSeries

from cryoet_catalog.parsers.mdoc import parse_mdoc_file


# Tilt-image extensions used for ``image_format`` detection. ``.st`` and
# ``.mdoc`` are deliberately excluded — they're stack files / sidecars, not
# the raw tilt-image format the UI labels.
_FORMAT_EXTS: dict[str, Literal["EER", "TIFF", "MRC"]] = {
    ".eer": "EER",
    ".tif": "TIFF",
    ".tiff": "TIFF",
    ".mrc": "MRC",
}


@dataclass
class TiltSeriesCollision:
    """One detected MDOC-stem collision (already auto-disambiguated)."""

    tilt_series_id: str  # the disambiguated id we ended up assigning
    original_stem: str  # the stem before disambiguation
    mdoc_path: str  # the MDOC whose stem collided


@dataclass
class TiltSeriesParseResult:
    records: list[TiltSeries] = field(default_factory=list)
    collisions: list[TiltSeriesCollision] = field(default_factory=list)
    unreadable: list[tuple[str, str]] = field(default_factory=list)


def _detect_image_format(
    frames_dir: Path,
) -> Literal["EER", "TIFF", "MRC"] | None:
    """Pick the unique tilt-image format present as direct children, or None.

    Returns None if no recognized formats are present OR if more than one
    format is present (ambiguous — the source dashboard makes the same call).
    """
    formats_seen: set[str] = set()
    for entry in frames_dir.iterdir():
        if not entry.is_file():
            continue
        fmt = _FORMAT_EXTS.get(entry.suffix.lower())
        if fmt is not None:
            formats_seen.add(fmt)
    if len(formats_seen) == 1:
        return formats_seen.pop()  # type: ignore[return-value]
    return None


def _find_zarr_for_mdoc(mdoc_path: Path) -> str | None:
    """Return ``<mdoc-stem>.zarr`` next to the MDOC if it exists."""
    candidate = mdoc_path.parent / f"{mdoc_path.stem}.zarr"
    if candidate.is_dir():
        return str(candidate)
    return None


def _find_st_for_mdoc(mdoc_path: Path) -> str | None:
    """Return ``<mdoc-stem>.st`` next to the MDOC if it exists."""
    candidate = mdoc_path.parent / f"{mdoc_path.stem}.st"
    if candidate.is_file():
        return str(candidate)
    return None


def _disambiguate_ids(
    mdoc_paths: list[Path],
) -> tuple[dict[Path, str], list[TiltSeriesCollision]]:
    """Map each MDOC path to a unique ``tilt_series_id``.

    Default id is ``mdoc_path.stem``. On collision, append the MDOC's
    parent-dir name (``<stem>__<parent>``); on still-colliding cases append
    a numeric suffix. Every disambiguated path is reported as a collision.
    """
    by_stem: dict[str, list[Path]] = {}
    for p in mdoc_paths:
        by_stem.setdefault(p.stem, []).append(p)

    ids: dict[Path, str] = {}
    collisions: list[TiltSeriesCollision] = []
    used: set[str] = set()

    for stem, paths in by_stem.items():
        if len(paths) == 1:
            ids[paths[0]] = stem
            used.add(stem)
            continue
        for p in paths:
            base = f"{stem}__{p.parent.name}"
            candidate = base
            n = 0
            while candidate in used:
                n += 1
                candidate = f"{base}_{n}"
            used.add(candidate)
            ids[p] = candidate
            collisions.append(
                TiltSeriesCollision(
                    tilt_series_id=candidate,
                    original_stem=stem,
                    mdoc_path=str(p),
                )
            )
    return ids, collisions


def parse_tilt_series_dir(frames_dir: Path) -> TiltSeriesParseResult:
    """Walk MDOCs in ``frames_dir`` and emit one ``TiltSeries`` Pydantic
    record per readable MDOC.

    Empty result on missing dir or no MDOCs. Per-MDOC parse failures land
    in ``unreadable``; readable MDOCs still produce records.
    """
    if not frames_dir.is_dir():
        return TiltSeriesParseResult()

    mdocs = sorted(frames_dir.glob("*.mdoc"))
    if not mdocs:
        return TiltSeriesParseResult()

    image_format = _detect_image_format(frames_dir)
    id_map, collisions = _disambiguate_ids(mdocs)

    records: list[TiltSeries] = []
    unreadable: list[tuple[str, str]] = []
    for mdoc_path in mdocs:
        parsed = parse_mdoc_file(mdoc_path)
        if parsed.status == "unreadable":
            unreadable.append((str(mdoc_path), parsed.error or "unreadable mdoc"))
            continue
        if parsed.status == "missing":
            # ``parse_mdoc_file`` returns missing only if the file vanishes
            # between glob and parse — skip silently rather than warn.
            continue
        try:
            mtime = mdoc_path.stat().st_mtime
        except OSError:
            mtime = None

        f = parsed.fields
        angles = f.get("tilt_angles") or None  # collapse [] to None for storage
        records.append(
            TiltSeries(
                tilt_series_id=id_map[mdoc_path],
                mdoc_path=str(mdoc_path),
                st_path=_find_st_for_mdoc(mdoc_path),
                zarr_path=_find_zarr_for_mdoc(mdoc_path),
                n_tilts=f.get("frame_count"),
                tilt_range_min=f.get("tilt_min"),
                tilt_range_max=f.get("tilt_max"),
                tilt_axis_angle=f.get("tilt_axis"),
                voltage=f.get("voltage"),
                pixel_spacing=f.get("pixel_size"),
                image_format=image_format,
                # microscope/camera from acquisition.toml only — left None here
                tilt_angles=angles,
                mtime=mtime,
            )
        )

    return TiltSeriesParseResult(
        records=records, collisions=collisions, unreadable=unreadable
    )


__all__ = [
    "TiltSeriesCollision",
    "TiltSeriesParseResult",
    "parse_tilt_series_dir",
]
