"""Acquisition-level tilt-angle extractor.

The tilt geometry of an acquisition is shared by all of its (researcher-
authored) tilt series, so the full per-image tilt-angle list lives on the
:class:`~schema.schema.Acquisition` rather than on any one ``TiltSeries`` row.
This module extracts that single list from the MDOC(s) under an acquisition's
``Frames/`` directory, handling both on-disk MDOC layouts:

1. **Series-level** (rosenlab convention): one ``.mdoc`` with per-tilt
   ``[ZValue = N]`` sections inside; angles come from the file's ``TiltAngle``
   lines (parsed via :func:`~catalog.parsers.mdoc.parse_mdoc_file`).

2. **Per-tilt** (gouauxlab convention): N ``.mdoc`` files (one per frame) with
   no ``[ZValue]`` sections; filenames follow ``..._NNN_<angle>...`` so the
   angle is recoverable from the (sorted) filenames.

When both layouts are present the series-level angles are preferred (they are
authoritative). Returns ``None`` when no angles can be recovered. MDOC parse
failures are recorded in ``unreadable`` so the assembler can surface them.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from catalog.parsers.mdoc import is_series_level_mdoc, parse_mdoc_file


# Per-tilt filename grammar: prefix, then ``_NNN_<angle>``. ``NNN`` is a 3-
# to 5-digit acquisition index; ``<angle>`` is a signed decimal. Match runs
# on the full filename (e.g. ``foo_001_-20.0.eer.mdoc``) so we don't have
# to disambiguate ``.eer.mdoc`` vs ``.mdoc``.
_PER_TILT_FILENAME_RE = re.compile(
    r"^(?P<prefix>.+?)_\d{3,5}_(?P<angle>-?\d+(?:\.\d+)?)"
)


@dataclass
class AcquisitionTiltAngles:
    """Result of :func:`parse_acquisition_tilt_angles`.

    ``tilt_angles`` is the full ordered per-image angle list (``None`` when no
    angles could be recovered). ``unreadable`` records ``(path, error)`` pairs
    for any MDOC that failed to content-parse.
    """

    tilt_angles: list[float] | None = None
    unreadable: list[tuple[str, str]] = field(default_factory=list)


def _per_tilt_group_key(filename: str) -> str | None:
    """Return the per-tilt group key for an MDOC filename, or ``None``.

    The group key is the filename prefix preceding ``_NNN_<angle>``. e.g.
    ``20241211_HippWaffle_49_001_-20.0.eer.mdoc`` → ``20241211_HippWaffle_49``.
    Returning ``None`` signals that the filename doesn't match the per-tilt
    pattern.
    """
    m = _PER_TILT_FILENAME_RE.match(filename)
    return m.group("prefix") if m else None


def _extract_tilt_angle_from_filename(filename: str) -> float | None:
    """Pull the angle out of a per-tilt filename (``_NNN_<angle>...``)."""
    m = _PER_TILT_FILENAME_RE.match(filename)
    return float(m.group("angle")) if m else None


def parse_acquisition_tilt_angles(frames_dir: Path) -> AcquisitionTiltAngles:
    """Extract the acquisition's full tilt-angle list from ``frames_dir``.

    Classifies each ``.mdoc`` independently (series-level via
    ``is_series_level_mdoc``; per-tilt via the ``_NNN_<angle>`` filename
    pattern). Prefers series-level angles when both layouts are present.
    Empty result (``tilt_angles=None``) on a missing dir or no recoverable
    angles. MDOC parse failures are collected in ``unreadable``.
    """
    result = AcquisitionTiltAngles()
    if not frames_dir.is_dir():
        return result

    mdocs = sorted(frames_dir.glob("*.mdoc"))
    if not mdocs:
        return result

    series_level: list[Path] = []
    per_tilt: list[Path] = []
    for p in mdocs:
        if is_series_level_mdoc(p):
            series_level.append(p)
        else:
            per_tilt.append(p)

    # --- Series-level branch (authoritative) ------------------------------
    series_angles: list[float] | None = None
    for mdoc_path in series_level:
        parsed = parse_mdoc_file(mdoc_path)
        if parsed.status == "unreadable":
            result.unreadable.append(
                (str(mdoc_path), parsed.error or "unreadable mdoc")
            )
            continue
        if parsed.status == "missing":
            continue
        if series_angles is None:
            angles = parsed.fields.get("tilt_angles") or None
            if angles is not None:
                series_angles = list(angles)

    if series_angles is not None:
        result.tilt_angles = series_angles
        return result

    # --- Per-tilt branch --------------------------------------------------
    if per_tilt:
        sorted_per_tilt = sorted(per_tilt)
        per_tilt_angles = [
            a
            for p in sorted_per_tilt
            if (a := _extract_tilt_angle_from_filename(p.name)) is not None
        ]
        if per_tilt_angles:
            result.tilt_angles = per_tilt_angles

    return result


__all__ = [
    "AcquisitionTiltAngles",
    "parse_acquisition_tilt_angles",
]
