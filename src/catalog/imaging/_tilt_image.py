"""EER/TIFF/MRC tilt-image loading for the tilt-series preview endpoint.

Originally vendored from
``aicryoet-tools/src/aicryoet_tools/eer.py`` at commit ``083ccec``.
The ``TiltImage`` / ``TiltSeries`` class graph from ``mdoc.py`` is
intentionally dropped — the API works directly off DB-recorded paths and
``tilt_angles`` cached on the ``tilt_series`` row.

Public surface:
    - ``load_tilt_image(path, gain=None, preview=False)`` — single 2D image
    - ``load_gain_reference(path)``
    - ``find_gain_reference(frames_dir)`` — sibling ``Gains/`` reference or None
    - ``apply_gain_correction(image, gain)``
    - ``render_eer(path, superres=None)``
    - ``find_viewable_tilt_images(frames_dir)`` — sorted ``(angle, path)``
"""
from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import tifffile

# File extensions recognized as tilt images.
_TILT_IMAGE_EXTENSIONS: tuple[str, ...] = ("*.eer", "*.tif", "*.tiff", "*.mrc")
# Gouauxlab-style filename pattern: ``..._NNN_<tilt-angle>...``
_FILENAME_ANGLE_RE = re.compile(r"_\d{3,5}_(-\d+\.?\d*|\d+\.\d+)")


def extract_tilt_angle_from_filename(filename: str) -> float | None:
    """Extract a tilt angle from a gouauxlab-style filename.

    The angle always follows a 3- to 5-digit image number, e.g.
    ``..._001_-20.0.eer`` → ``-20.0``.
    """
    m = _FILENAME_ANGLE_RE.search(filename)
    return float(m.group(1)) if m else None


def get_eer_superres_level(eer_path: Path) -> int:
    """Determine the super-resolution level of an EER file (0=4K, 1=8K, 2=16K)."""
    with tifffile.TiffFile(eer_path) as tiff:
        metadata = tiff.eer_metadata
        n_subpixels = metadata.get("nrOfSubPixelPerDirection", 1)
    match n_subpixels:
        case 1:
            return 0
        case 2:
            return 1
        case 4:
            return 2
        case _:
            return 0


def render_eer(eer_path: Path, superres: int | None = None) -> np.ndarray:
    """Render an EER as a summed 2D image, auto-detecting super-resolution.

    Sums the dose-fractionation frames one at a time into a single 2D
    accumulator rather than materializing the whole ``(n_frames, H, W)`` stack
    via ``asarray()``. An EER routinely holds 500+ frames at 8K, so the full
    stack is tens of GB (OOM); the incremental sum peaks at one frame plus the
    accumulator (a few hundred MB) and yields a bit-identical result.
    """
    if superres is None:
        superres = get_eer_superres_level(eer_path)
    with tifffile.TiffFile(eer_path, superres=superres) as tiff:
        series = tiff.series[0]
        acc = np.zeros(series.shape[1:], dtype=np.uint32)
        for page in series.pages:
            acc += page.asarray()
    return acc


def find_gain_reference(frames_dir: Path) -> Path | None:
    """Find a gain reference in the acquisition's sibling ``Gains/`` dir.

    ``Frames/`` and ``Gains/`` sit side by side under the acquisition dir (see
    the experimental starter skeleton). Returns the first recognized reference
    (``.gain``/``.tif``/``.tiff``/``.mrc``), or ``None`` when there is no
    ``Gains/`` dir or it holds nothing usable.
    """
    gains_dir = frames_dir.parent / "Gains"
    if not gains_dir.is_dir():
        return None
    for ext in ("*.gain", "*.tif", "*.tiff", "*.mrc"):
        matches = sorted(gains_dir.glob(ext))
        if matches:
            return matches[0]
    return None


def load_gain_reference(gain_path: Path) -> np.ndarray:
    """Load a gain reference (``.gain`` TIFF or ``.mrc``)."""
    match gain_path.suffix.lower():
        case ".mrc":
            import mrcfile

            with mrcfile.open(gain_path, permissive=True) as mrc:
                return mrc.data.copy()
        case _:
            return tifffile.imread(gain_path)


def apply_gain_correction(image: np.ndarray, gain: np.ndarray) -> np.ndarray:
    """Divide an image by its gain reference, upsampling the gain if needed."""
    image_shape = image.shape[-2:]
    if gain.shape != image_shape:
        scale_h = image_shape[0] // gain.shape[0]
        scale_w = image_shape[1] // gain.shape[1]
        if scale_h > 1 or scale_w > 1:
            gain = np.repeat(np.repeat(gain, scale_h, axis=0), scale_w, axis=1)
    gain_safe = np.where(gain == 0, 1, gain)
    return image.astype(np.float32) / gain_safe.astype(np.float32)


def load_tilt_image(
    path: Path,
    gain: np.ndarray | None = None,
    *,
    preview: bool = False,
) -> np.ndarray:
    """Load a single tilt image from an EER, TIFF, or MRC file.

    :param path: Path to the tilt image.
    :param gain: Optional gain reference array.
    :param preview: If True, load only the first frame of multi-frame files
        instead of summing — faster for previewing.
    """
    suffix = path.suffix.lower()
    match suffix:
        case ".eer":
            # Previews/thumbnails don't need super-resolution: force the 4K
            # (superres=0) render, a quarter the pixels of the auto-detected
            # 8K/16K levels, so the downstream percentile + matplotlib pass
            # stays well within the scanner's memory limit.
            image = render_eer(path, superres=0 if preview else None)
        case ".tif" | ".tiff":
            if preview:
                image = tifffile.imread(path, key=0)
            else:
                image = tifffile.imread(path)
                if image.ndim == 3:
                    image = image.sum(axis=0, dtype=np.float32)
        case ".mrc":
            import mrcfile

            with mrcfile.open(path, permissive=True) as mrc:
                image = mrc.data.copy()
            if image.ndim == 3:
                image = image[0]
        case _:
            raise ValueError(f"unsupported tilt image format: {suffix}")

    if gain is not None:
        image = apply_gain_correction(image, gain)
    return image


def find_viewable_tilt_images(frames_dir: Path) -> list[tuple[float, Path]]:
    """Find TIFF/MRC tilt images (skipping EER) in a frames dir, sorted by angle.

    EER files load slowly (multi-frame summation) so the preview endpoint
    prefers TIFF/MRC siblings — mirrors ``_find_viewable_tilt_images`` in
    ``aicryoet-tools/dashboard/pages/cryoet.py``.
    """
    out: list[tuple[float, Path]] = []
    for ext in ("*.tif", "*.tiff", "*.mrc"):
        for img_path in frames_dir.glob(ext):
            angle = extract_tilt_angle_from_filename(img_path.name)
            if angle is not None:
                out.append((angle, img_path))
    out.sort(key=lambda x: x[0])
    return out


def find_eer_tilt_images(frames_dir: Path) -> list[tuple[float, Path]]:
    """Find EER tilt images in a frames dir, sorted by angle.

    EER summation is slow, so callers should prefer
    :func:`find_viewable_tilt_images` and fall back to this only when no
    TIFF/MRC siblings exist (i.e. an EER-only acquisition).
    """
    out: list[tuple[float, Path]] = []
    for img_path in frames_dir.glob("*.eer"):
        angle = extract_tilt_angle_from_filename(img_path.name)
        if angle is not None:
            out.append((angle, img_path))
    out.sort(key=lambda x: x[0])
    return out
