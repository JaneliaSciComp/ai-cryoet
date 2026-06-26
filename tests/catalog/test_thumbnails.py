"""Tests for catalog.thumbnails."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from catalog.thumbnails import (
    AcqRef,
    _relpath,
    _safe_segment,
    generate_thumbnails,
    representative_relpath,
)

# Minimal PNG header used as fake output from _render_one.
_FAKE_PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100


def _ref(acquisition_id: str, *, zarr_path=None, st_path=None, frames_dir="/data/Frames") -> AcqRef:
    return AcqRef(
        acquisition_id=acquisition_id,
        zarr_path=zarr_path,
        st_path=st_path,
        frames_dir=frames_dir,
    )


# ── _safe_segment ─────────────────────────────────────────────────────────────


def test_safe_segment_valid():
    assert _safe_segment("sample_chromatin") == "sample_chromatin"
    assert _safe_segment("Position_86") == "Position_86"
    assert _safe_segment("bp_3dctf_bin4") == "bp_3dctf_bin4"


def test_safe_segment_rejects_traversal():
    with pytest.raises(ValueError):
        _safe_segment("..")
    with pytest.raises(ValueError):
        _safe_segment("a/b")
    with pytest.raises(ValueError):
        _safe_segment("")


# ── _relpath ─────────────────────────────────────────────────────────────────


def test_relpath_structure():
    assert _relpath("s", "a") == "s/a.png"


# ── generate_thumbnails ───────────────────────────────────────────────────────


def _fake_render_one(
    ref: AcqRef, dest: Path
) -> tuple[bool, str | None, str | None]:
    """Side effect for patching _render_one: writes fake PNG and returns the
    new ``(ok, source_kind, source_path)`` triple (§4.5)."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(_FAKE_PNG)
    # Report the source as the renderer's first available branch (post-fallback
    # would be inside the real renderer; here we just echo the guess).
    kind = "zarr" if ref.zarr_path else "st" if ref.st_path else "frames"
    path = ref.zarr_path or ref.st_path or ref.frames_dir
    return True, kind, path


def test_generate_thumbnails_writes_png_and_returns_relpath(tmp_path):
    with patch("catalog.thumbnails._render_one", side_effect=_fake_render_one):
        result = generate_thumbnails("sample_a", [_ref("acq1")], tmp_path)

    expected_rel = "sample_a/acq1.png"
    assert result.representative == expected_rel
    assert len(result.per_acq) == 1
    acq = result.per_acq[0]
    assert acq.acquisition_id == "acq1"
    assert acq.status == "ok"
    assert acq.relpath == expected_rel
    # frames-only ref → source_kind "frames", source_path echoed.
    assert acq.source_kind == "frames"
    assert acq.source_path == "/data/Frames"
    out_file = tmp_path / expected_rel
    assert out_file.is_file()
    assert out_file.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"


def test_generate_thumbnails_no_source_skipped(tmp_path):
    # Acquisition with no tilt-series source (no zarr/st/frames) is skipped.
    ref = _ref("acq1", frames_dir=None)
    with patch("catalog.thumbnails._render_one") as mock_render:
        result = generate_thumbnails("sample_a", [ref], tmp_path)

    mock_render.assert_not_called()
    assert result.representative is None
    assert result.per_acq[0].status == "missing_source"


def test_generate_thumbnails_render_failed_status(tmp_path):
    """A present source whose render raises → status ``render_failed`` (the
    renderer surfaces ok=False)."""
    def _fail(ref, dest):
        return False, None, None

    with patch("catalog.thumbnails._render_one", side_effect=_fail):
        result = generate_thumbnails("sample_a", [_ref("acq1")], tmp_path)

    assert result.representative is None
    assert result.per_acq[0].status == "render_failed"


def test_generate_thumbnails_source_after_fallback(tmp_path):
    """§9.5: zarr absent → the renderer falls back to st and records ``st`` +
    its path (the post-fallback source, not the pre-call guess)."""
    def _fallback(ref, dest):
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(_FAKE_PNG)
        # zarr_path was None on the ref, so the real renderer would fall to st.
        return True, "st", ref.st_path

    ref = _ref("acq1", zarr_path=None, st_path="/data/x.st", frames_dir="/data/Frames")
    with patch("catalog.thumbnails._render_one", side_effect=_fallback):
        result = generate_thumbnails("sample_a", [ref], tmp_path)

    acq = result.per_acq[0]
    assert acq.status == "ok"
    assert acq.source_kind == "st"
    assert acq.source_path == "/data/x.st"


def test_generate_thumbnails_skip_existing_does_not_re_render(tmp_path):
    expected_rel = "sample_a/acq1.png"
    dest = tmp_path / expected_rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(_FAKE_PNG)
    original_mtime = dest.stat().st_mtime

    with patch("catalog.thumbnails._render_one") as mock_render:
        result = generate_thumbnails("sample_a", [_ref("acq1")], tmp_path, skip_existing=True)

    mock_render.assert_not_called()
    assert result.representative == expected_rel
    assert result.per_acq[0].status == "ok"
    # A heal-style reuse leaves the source provenance None for the caller to
    # preserve from the prior record.
    assert result.per_acq[0].source_kind is None
    assert dest.stat().st_mtime == original_mtime


def test_generate_thumbnails_skip_existing_renders_missing(tmp_path):
    with patch("catalog.thumbnails._render_one", side_effect=_fake_render_one) as mock_render:
        result = generate_thumbnails("sample_a", [_ref("acq1")], tmp_path, skip_existing=True)

    mock_render.assert_called_once()
    assert result.representative == "sample_a/acq1.png"


def test_generate_thumbnails_overwrites_no_tmp_left_behind(tmp_path):
    with patch("catalog.thumbnails._render_one", side_effect=_fake_render_one):
        generate_thumbnails("sample_a", [_ref("acq1")], tmp_path)

    # No .png.tmp files should be left behind
    tmp_files = list(tmp_path.rglob("*.png.tmp"))
    assert tmp_files == []


def test_generate_thumbnails_representative_is_first_acq(tmp_path):
    # Two acquisitions both render; representative is the first by id.
    refs = [_ref("acq2"), _ref("acq1")]
    with patch("catalog.thumbnails._render_one", side_effect=_fake_render_one):
        result = generate_thumbnails("sample_a", refs, tmp_path)

    assert result.representative == "sample_a/acq1.png"
    assert {a.acquisition_id for a in result.per_acq} == {"acq1", "acq2"}
    assert (tmp_path / "sample_a/acq1.png").is_file()
    assert (tmp_path / "sample_a/acq2.png").is_file()


# ── representative_relpath ────────────────────────────────────────────────────


def test_representative_relpath_first_wins():
    assert representative_relpath(["s/acq1.png", "s/acq2.png"]) == "s/acq1.png"


def test_representative_relpath_empty():
    assert representative_relpath([]) is None
