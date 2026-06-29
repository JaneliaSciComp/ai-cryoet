# Version of the researcher-facing data format: the sample.toml /
# acquisition.toml structure + directory layout. Bumped per semver:
#   MAJOR — breaking (field/section/layout removed or renamed)
#   MINOR — additive (new optional field/section)
#   PATCH — clarification only (comments/docs, no structural change)
# Researchers declare the version they authored against via the top-level
# `format_version` key in sample.toml; the loader warns/errors on a major
# mismatch. Separate from the catalog DB schema (Alembic) and from image
# release versions.
DATA_FORMAT_VERSION = "1.0.0"

from .schema import (
    Acquisition,
    AcquisitionFile,
    Annotation,
    Label,
    Fiducial,
    Chromatin,
    DataSource,
    Freezing,
    IdStr,
    MdRun,
    MdSource,
    Milling,
    PostProcessedTomogram,
    Project,
    RawTomogram,
    Sample,
    SampleRecord,
    Simulation,
    TiltSeries,
)

__all__ = [
    "DATA_FORMAT_VERSION",
    "Acquisition",
    "AcquisitionFile",
    "Annotation",
    "Label",
    "Fiducial",
    "Chromatin",
    "DataSource",
    "Freezing",
    "IdStr",
    "MdRun",
    "MdSource",
    "Milling",
    "PostProcessedTomogram",
    "Project",
    "RawTomogram",
    "Sample",
    "SampleRecord",
    "Simulation",
    "TiltSeries",
]
