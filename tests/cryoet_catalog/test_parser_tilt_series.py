"""Tests for ``cryoet_catalog.parsers.tilt_series``.

Each test writes its own fixtures inline via ``tmp_path``.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from cryoet_catalog.parsers.tilt_series import (
    TiltSeriesParseResult,
    parse_tilt_series_dir,
)


_MDOC_BASIC = """\
PixelSpacing = 2.93
Voltage = 300
TiltAxisAngle = 84.5

[ZValue = 0]
TiltAngle = -60.0
ExposureDose = 0.5

[ZValue = 1]
TiltAngle = -57.0
ExposureDose = 0.5

[ZValue = 2]
TiltAngle = -54.0
ExposureDose = 0.5
"""


def test_missing_dir_returns_empty_result(tmp_path: Path) -> None:
    result = parse_tilt_series_dir(tmp_path / "nope")
    assert isinstance(result, TiltSeriesParseResult)
    assert result.records == []
    assert result.collisions == []
    assert result.unreadable == []


def test_no_mdocs_returns_empty_result(tmp_path: Path) -> None:
    frames_dir = tmp_path / "Frames"
    frames_dir.mkdir()
    (frames_dir / "001.eer").write_bytes(b"")
    result = parse_tilt_series_dir(frames_dir)
    assert result.records == []
    assert result.collisions == []


def test_single_mdoc_emits_one_record_with_eer_format(tmp_path: Path) -> None:
    frames_dir = tmp_path / "Frames"
    frames_dir.mkdir()
    (frames_dir / "ts.mdoc").write_text(_MDOC_BASIC)
    # Sibling frame files: only EER → image_format='EER'.
    (frames_dir / "001.eer").write_bytes(b"")
    (frames_dir / "002.eer").write_bytes(b"")

    result = parse_tilt_series_dir(frames_dir)

    assert len(result.records) == 1
    rec = result.records[0]
    assert rec.tilt_series_id == "ts"
    assert rec.mdoc_path == str(frames_dir / "ts.mdoc")
    assert rec.n_tilts == 3
    assert rec.tilt_range_min == pytest.approx(-60.0)
    assert rec.tilt_range_max == pytest.approx(-54.0)
    assert rec.tilt_axis_angle == pytest.approx(84.5)
    assert rec.voltage == pytest.approx(300.0)
    assert rec.pixel_spacing == pytest.approx(2.93)
    assert rec.image_format == "EER"
    assert rec.tilt_angles == [
        pytest.approx(-60.0),
        pytest.approx(-57.0),
        pytest.approx(-54.0),
    ]
    # microscope/camera deliberately not populated from MDOC.
    assert rec.microscope is None
    assert rec.camera is None
    assert rec.mtime is not None
    assert result.collisions == []
    assert result.unreadable == []


def test_image_format_tiff(tmp_path: Path) -> None:
    frames_dir = tmp_path / "Frames"
    frames_dir.mkdir()
    (frames_dir / "ts.mdoc").write_text(_MDOC_BASIC)
    (frames_dir / "001.tiff").write_bytes(b"")
    (frames_dir / "002.tif").write_bytes(b"")
    result = parse_tilt_series_dir(frames_dir)
    assert result.records[0].image_format == "TIFF"


def test_image_format_mrc(tmp_path: Path) -> None:
    frames_dir = tmp_path / "Frames"
    frames_dir.mkdir()
    (frames_dir / "ts.mdoc").write_text(_MDOC_BASIC)
    (frames_dir / "001.mrc").write_bytes(b"")
    result = parse_tilt_series_dir(frames_dir)
    assert result.records[0].image_format == "MRC"


def test_ambiguous_image_format_is_none(tmp_path: Path) -> None:
    """Mixed extensions → unable to pick one → image_format=None."""
    frames_dir = tmp_path / "Frames"
    frames_dir.mkdir()
    (frames_dir / "ts.mdoc").write_text(_MDOC_BASIC)
    (frames_dir / "001.eer").write_bytes(b"")
    (frames_dir / "002.tiff").write_bytes(b"")
    result = parse_tilt_series_dir(frames_dir)
    assert result.records[0].image_format is None


def test_zarr_sibling_is_recorded(tmp_path: Path) -> None:
    frames_dir = tmp_path / "Frames"
    frames_dir.mkdir()
    (frames_dir / "ts.mdoc").write_text(_MDOC_BASIC)
    zarr_dir = frames_dir / "ts.zarr"
    zarr_dir.mkdir()
    result = parse_tilt_series_dir(frames_dir)
    assert result.records[0].zarr_path == str(zarr_dir)


def test_st_sibling_is_recorded(tmp_path: Path) -> None:
    frames_dir = tmp_path / "Frames"
    frames_dir.mkdir()
    (frames_dir / "ts.mdoc").write_text(_MDOC_BASIC)
    st_path = frames_dir / "ts.st"
    st_path.write_bytes(b"")
    result = parse_tilt_series_dir(frames_dir)
    assert result.records[0].st_path == str(st_path)


def test_multiple_mdocs_unique_stems(tmp_path: Path) -> None:
    frames_dir = tmp_path / "Frames"
    frames_dir.mkdir()
    (frames_dir / "ts_a.mdoc").write_text(_MDOC_BASIC)
    (frames_dir / "ts_b.mdoc").write_text(_MDOC_BASIC)
    result = parse_tilt_series_dir(frames_dir)
    ids = sorted(r.tilt_series_id for r in result.records)
    assert ids == ["ts_a", "ts_b"]
    assert result.collisions == []


def test_unreadable_mdoc_collected_other_records_kept(tmp_path: Path) -> None:
    frames_dir = tmp_path / "Frames"
    frames_dir.mkdir()
    (frames_dir / "good.mdoc").write_text(_MDOC_BASIC)
    (frames_dir / "bad.mdoc").write_text(
        "Voltage = not_a_number\n[ZValue = 0]\nTiltAngle = 0.0\n"
    )
    result = parse_tilt_series_dir(frames_dir)
    assert [r.tilt_series_id for r in result.records] == ["good"]
    assert len(result.unreadable) == 1
    bad_path, err = result.unreadable[0]
    assert bad_path.endswith("bad.mdoc")
    assert "not_a_number" in err


def test_stem_collision_disambiguates_with_parent_dir(tmp_path: Path) -> None:
    """Two MDOCs sharing a stem (only reachable via copy-into-tmp setup)
    get disambiguated and produce a TiltSeriesCollision entry each.

    Real discovery only scans direct children of ``frames_dir``, so this
    scenario is engineered: we pre-build the collision map by stuffing two
    MDOC files into the dir with the same ``.stem`` — which Python's
    filesystem only allows if their suffix-strings differ. The combination
    ``<stem>.mdoc`` + ``<stem>..mdoc`` yields ``stem`` and ``stem.`` —
    different stems, so we can't trigger via filenames alone.

    Instead, we test the disambiguation helper directly here by feeding it
    two paths whose .stem matches but parent differs (simulating a
    hypothetical future recursive walk).
    """
    from cryoet_catalog.parsers.tilt_series import _disambiguate_ids

    p1 = tmp_path / "dirA" / "shared.mdoc"
    p2 = tmp_path / "dirB" / "shared.mdoc"
    p1.parent.mkdir(parents=True)
    p2.parent.mkdir(parents=True)
    p1.write_text("")
    p2.write_text("")

    ids, collisions = _disambiguate_ids([p1, p2])
    # Both got disambiguated, with parent-dir suffixes.
    assert ids[p1] == "shared__dirA"
    assert ids[p2] == "shared__dirB"
    assert {c.tilt_series_id for c in collisions} == {
        "shared__dirA",
        "shared__dirB",
    }
    assert all(c.original_stem == "shared" for c in collisions)


def test_stem_collision_numeric_suffix_fallback(tmp_path: Path) -> None:
    """If parent-dir disambiguation still collides, a numeric suffix is added.

    Engineered case: two paths with the same ``stem`` and the same
    immediate ``parent.name`` but different ancestors. Real discovery
    won't surface this today, but the algorithm must still produce
    unique ids.
    """
    from cryoet_catalog.parsers.tilt_series import _disambiguate_ids

    p1 = tmp_path / "a" / "x" / "shared.mdoc"
    p2 = tmp_path / "b" / "x" / "shared.mdoc"

    ids, collisions = _disambiguate_ids([p1, p2])
    base = "shared__x"
    assert ids[p1] == base
    assert ids[p2] == f"{base}_1"
    assert {c.tilt_series_id for c in collisions} == {base, f"{base}_1"}
