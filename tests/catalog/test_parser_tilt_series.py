"""Tests for ``catalog.parsers.tilt_series.parse_acquisition_tilt_angles``.

The tilt geometry is an acquisition-level property: the parser extracts a single
ordered ``tilt_angles`` list from the MDOC(s) under an acquisition's ``Frames/``
dir, handling both on-disk layouts (series-level ``[ZValue]`` MDOCs and per-tilt
MDOCs whose angle lives in the ``_NNN_<angle>`` filename slot). It no longer
emits per-MDOC tilt-series records or collisions.

Each test writes its own fixtures inline via ``tmp_path``.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from catalog.parsers.tilt_series import (
    AcquisitionTiltAngles,
    parse_acquisition_tilt_angles,
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

_PER_TILT_HEADER = """\
PixelSpacing = 1.7
Voltage = 200
TiltAxisAngle = 92.5
"""


def test_missing_dir_returns_empty_result(tmp_path: Path) -> None:
    result = parse_acquisition_tilt_angles(tmp_path / "nope")
    assert isinstance(result, AcquisitionTiltAngles)
    assert result.tilt_angles is None
    assert result.unreadable == []


def test_no_mdocs_returns_empty_result(tmp_path: Path) -> None:
    frames_dir = tmp_path / "Frames"
    frames_dir.mkdir()
    (frames_dir / "001.eer").write_bytes(b"")
    result = parse_acquisition_tilt_angles(frames_dir)
    assert result.tilt_angles is None
    assert result.unreadable == []


def test_series_level_mdoc_yields_zvalue_angles(tmp_path: Path) -> None:
    frames_dir = tmp_path / "Frames"
    frames_dir.mkdir()
    (frames_dir / "ts.mdoc").write_text(_MDOC_BASIC)
    (frames_dir / "001.eer").write_bytes(b"")

    result = parse_acquisition_tilt_angles(frames_dir)

    assert result.tilt_angles == [
        pytest.approx(-60.0),
        pytest.approx(-57.0),
        pytest.approx(-54.0),
    ]
    assert result.unreadable == []


def test_per_tilt_mdocs_yield_filename_angles(tmp_path: Path) -> None:
    """Gouauxlab pattern: N per-tilt MDOCs → one sorted angle list."""
    frames_dir = tmp_path / "Frames"
    frames_dir.mkdir()
    for idx, angle in enumerate(["-30.0", "-15.0", "0.0", "15.0", "30.0"], start=1):
        (frames_dir / f"HippWaffle_49_{idx:03d}_{angle}.eer.mdoc").write_text(
            _PER_TILT_HEADER
        )

    result = parse_acquisition_tilt_angles(frames_dir)

    assert result.tilt_angles == [
        pytest.approx(-30.0),
        pytest.approx(-15.0),
        pytest.approx(0.0),
        pytest.approx(15.0),
        pytest.approx(30.0),
    ]
    assert result.unreadable == []


def test_series_level_preferred_over_per_tilt(tmp_path: Path) -> None:
    """When both layouts are present, the series-level [ZValue] angles win."""
    frames_dir = tmp_path / "Frames"
    frames_dir.mkdir()
    (frames_dir / "ts.mdoc").write_text(_MDOC_BASIC)
    for idx, angle in enumerate(["-10.0", "10.0"], start=1):
        (frames_dir / f"extra_{idx:03d}_{angle}.eer.mdoc").write_text(
            _PER_TILT_HEADER
        )

    result = parse_acquisition_tilt_angles(frames_dir)

    assert result.tilt_angles == [
        pytest.approx(-60.0),
        pytest.approx(-57.0),
        pytest.approx(-54.0),
    ]


def test_unreadable_series_mdoc_recorded_others_kept(tmp_path: Path) -> None:
    """A series-level MDOC that fails to parse is collected in ``unreadable``;
    a sibling good series-level MDOC still supplies the angles.
    """
    frames_dir = tmp_path / "Frames"
    frames_dir.mkdir()
    # ``aaa`` sorts before ``good``; make the first one unreadable so we also
    # cover "keep scanning after a failure".
    (frames_dir / "aaa_bad.mdoc").write_text(
        "Voltage = not_a_number\n[ZValue = 0]\nTiltAngle = 0.0\n"
    )
    (frames_dir / "good.mdoc").write_text(_MDOC_BASIC)

    result = parse_acquisition_tilt_angles(frames_dir)

    assert result.tilt_angles == [
        pytest.approx(-60.0),
        pytest.approx(-57.0),
        pytest.approx(-54.0),
    ]
    assert len(result.unreadable) == 1
    bad_path, err = result.unreadable[0]
    assert bad_path.endswith("aaa_bad.mdoc")
    assert "not_a_number" in err


def test_per_tilt_unparseable_filename_is_dropped(tmp_path: Path) -> None:
    """A per-tilt MDOC whose name lacks ``_NNN_<angle>`` contributes no angle;
    the matching MDOCs still yield their angles.
    """
    frames_dir = tmp_path / "Frames"
    frames_dir.mkdir()
    for idx, angle in enumerate(["-10.0", "0.0", "10.0"], start=1):
        (frames_dir / f"sampleX_{idx:03d}_{angle}.eer.mdoc").write_text(
            _PER_TILT_HEADER
        )
    (frames_dir / "sampleX_misnamed.eer.mdoc").write_text(_PER_TILT_HEADER)

    result = parse_acquisition_tilt_angles(frames_dir)

    assert result.tilt_angles == [
        pytest.approx(-10.0),
        pytest.approx(0.0),
        pytest.approx(10.0),
    ]


def test_per_tilt_no_matching_names_yields_none(tmp_path: Path) -> None:
    """If no per-tilt MDOC name matches the pattern, no angles are recovered."""
    frames_dir = tmp_path / "Frames"
    frames_dir.mkdir()
    (frames_dir / "weird_name.mdoc").write_text(_PER_TILT_HEADER)
    (frames_dir / "another_weird.mdoc").write_text(_PER_TILT_HEADER)

    result = parse_acquisition_tilt_angles(frames_dir)

    assert result.tilt_angles is None
    assert result.unreadable == []
