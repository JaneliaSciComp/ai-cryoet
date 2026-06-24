"""Tests for tilt-series median-image rendering, focused on the EER fallback."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import numpy as np

from catalog.imaging._mrc import _array_to_png_bytes, _downscale_local_mean
from catalog.imaging._tilt_image import find_eer_tilt_images, find_gain_reference
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


def test_render_frames_gain_corrects_eer_from_sibling_gains_dir(tmp_path):
    # Acquisition layout: Frames/ and Gains/ side by side.
    frames = tmp_path / "Frames"
    gains = tmp_path / "Gains"
    frames.mkdir()
    gains.mkdir()
    _touch(frames, "stack_001_-30.0.eer")
    _touch(frames, "stack_002_0.0.eer")
    _touch(frames, "stack_003_30.0.eer")
    gain_file = _touch(gains, "ref.gain")

    def fake_load(path, gain=None, *, preview=False):
        return np.zeros((4, 4), dtype=np.float32)

    applied: dict[str, object] = {}

    def fake_apply(image, gain):
        applied["gain"] = gain
        return image

    sentinel_gain = np.ones((4, 4), dtype=np.float32)
    with patch(
        "catalog.imaging._tilt_image.load_tilt_image", side_effect=fake_load
    ), patch(
        "catalog.imaging._tilt_image.load_gain_reference", return_value=sentinel_gain
    ) as load_gain, patch(
        "catalog.imaging._tilt_image.apply_gain_correction", side_effect=fake_apply
    ), patch(
        "catalog.imaging._mrc._array_to_png_bytes", return_value=b"PNG"
    ):
        out = render_frames_median_png(str(frames), width=128)

    assert out == b"PNG"
    # The EER center frame is gain-corrected with the Gains/ reference.
    load_gain.assert_called_once_with(gain_file)
    assert applied["gain"] is sentinel_gain


def test_render_frames_eer_gain_mismatch_falls_back_to_uncorrected(tmp_path):
    # A gain reference larger than the 4K EER render (the 8K/16K case) makes
    # apply_gain_correction raise a broadcasting error. The preview is cosmetic,
    # so the renderer must swallow it and return the uncorrected image — never
    # 500 the endpoint (the route only catches FileNotFoundError).
    frames = tmp_path / "Frames"
    gains = tmp_path / "Gains"
    frames.mkdir()
    gains.mkdir()
    _touch(frames, "stack_002_0.0.eer")
    _touch(gains, "ref.gain")

    def fake_load(path, gain=None, *, preview=False):
        return np.zeros((4, 4), dtype=np.float32)

    # Gain bigger than the image (e.g. 8K gain vs 4K EER) -> not upsampled ->
    # division broadcasts to a ValueError inside apply_gain_correction.
    too_big_gain = np.ones((8, 8), dtype=np.float32)
    with patch(
        "catalog.imaging._tilt_image.load_tilt_image", side_effect=fake_load
    ), patch(
        "catalog.imaging._tilt_image.load_gain_reference", return_value=too_big_gain
    ), patch(
        "catalog.imaging._mrc._array_to_png_bytes", return_value=b"PNG"
    ):
        out = render_frames_median_png(str(frames), width=128)

    assert out == b"PNG"  # rendered despite the gain shape mismatch


def test_render_frames_no_gain_when_center_is_tiff(tmp_path):
    # TIFF/MRC frames are left as-is even if a Gains/ dir exists.
    frames = tmp_path / "Frames"
    gains = tmp_path / "Gains"
    frames.mkdir()
    gains.mkdir()
    _touch(frames, "stack_002_0.0.tif")
    _touch(gains, "ref.gain")

    def fake_load(path, gain=None, *, preview=False):
        return np.zeros((4, 4), dtype=np.float32)

    with patch(
        "catalog.imaging._tilt_image.load_tilt_image", side_effect=fake_load
    ), patch(
        "catalog.imaging._tilt_image.apply_gain_correction"
    ) as apply_mock, patch(
        "catalog.imaging._mrc._array_to_png_bytes", return_value=b"PNG"
    ):
        render_frames_median_png(str(frames), width=128)

    # No gain correction for TIFF frames.
    apply_mock.assert_not_called()


# ── find_gain_reference ───────────────────────────────────────────────────────


def test_find_gain_reference_locates_sibling_gains_dir(tmp_path):
    frames = tmp_path / "Frames"
    gains = tmp_path / "Gains"
    frames.mkdir()
    gains.mkdir()
    ref = _touch(gains, "camera.gain")

    assert find_gain_reference(frames) == ref


def test_find_gain_reference_none_when_no_gains_dir(tmp_path):
    frames = tmp_path / "Frames"
    frames.mkdir()
    assert find_gain_reference(frames) is None


# ── downscale / binning ───────────────────────────────────────────────────────


def test_downscale_local_mean_averages_blocks_and_reduces_noise():
    rng = np.random.default_rng(0)
    arr = rng.normal(100.0, 20.0, size=(4096, 4096)).astype(np.float32)
    out = _downscale_local_mean(arr, 512)
    # 4096 // 512 == 8, so an 8x8 block average -> 512x512 output.
    assert out.shape == (512, 512)
    # Block-averaging preserves the mean but cuts the standard deviation.
    assert abs(out.mean() - arr.mean()) < 1.0
    assert out.std() < arr.std() / 4


def test_downscale_local_mean_noop_when_already_small():
    arr = np.zeros((128, 200), dtype=np.float32)
    out = _downscale_local_mean(arr, 800)
    assert out is arr


def test_array_to_png_bytes_renders_large_noisy_array():
    rng = np.random.default_rng(1)
    arr = rng.normal(0.0, 1.0, size=(2048, 2048)).astype(np.float32)
    png = _array_to_png_bytes(arr, percentile=(2, 98), width=512)
    assert png.startswith(b"\x89PNG")
