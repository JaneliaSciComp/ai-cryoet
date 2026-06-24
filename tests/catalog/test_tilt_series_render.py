"""Tests for tilt-series median-image rendering, focused on the EER fallback."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import numpy as np

from catalog.imaging._tilt_image import find_eer_tilt_images
from catalog.imaging._tilt_series import render_frames_median_png


def _touch(dir_: Path, name: str) -> Path:
    p = dir_ / name
    p.write_bytes(b"")
    return p


# ── find_eer_tilt_images ──────────────────────────────────────────────────────


def test_find_eer_tilt_images_parses_and_sorts_by_angle(tmp_path):
    _touch(tmp_path, "stack_002_0.0.eer")
    _touch(tmp_path, "stack_001_-30.0.eer")
    _touch(tmp_path, "stack_003_30.0.eer")
    _touch(tmp_path, "notes.txt")  # ignored

    found = find_eer_tilt_images(tmp_path)

    assert [angle for angle, _ in found] == [-30.0, 0.0, 30.0]
    assert all(p.suffix == ".eer" for _, p in found)


def test_find_eer_tilt_images_empty_when_none(tmp_path):
    _touch(tmp_path, "stack_001_-30.0.tif")  # TIFF, not EER
    assert find_eer_tilt_images(tmp_path) == []


# ── render_frames_median_png EER fallback ─────────────────────────────────────


def test_render_frames_falls_back_to_eer_and_picks_median(tmp_path):
    # EER-only Frames dir: no TIFF/MRC siblings, so the viewable finder returns
    # nothing and the renderer must fall back to the EER images.
    _touch(tmp_path, "stack_001_-30.0.eer")
    _touch(tmp_path, "stack_002_0.0.eer")
    _touch(tmp_path, "stack_003_30.0.eer")

    loaded: dict[str, Path] = {}

    def fake_load(path, gain=None, *, preview=False):
        loaded["path"] = Path(path)
        return np.zeros((4, 4), dtype=np.float32)

    with patch("catalog.imaging._tilt_image.load_tilt_image", side_effect=fake_load), patch(
        "catalog.imaging._mrc._array_to_png_bytes", return_value=b"PNG"
    ):
        out = render_frames_median_png(str(tmp_path), width=128)

    assert out == b"PNG"
    # Median angle is 0.0 → the 0.0° EER frame is the one loaded.
    assert loaded["path"].name == "stack_002_0.0.eer"


def test_render_frames_raises_when_no_images(tmp_path):
    import pytest

    with pytest.raises(FileNotFoundError):
        render_frames_median_png(str(tmp_path))
