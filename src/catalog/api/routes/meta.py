"""GET /meta — portal release version + data format version for the UI footer.

``portal_version`` is the deployed release (a git tag), baked into the image at
build time via the ``PORTAL_VERSION`` build arg → env var; defaults to ``"dev"``
in local/unset runs. ``data_format_version`` is the researcher-facing metadata
format version (``schema.DATA_FORMAT_VERSION``) — what tells a researcher
whether their TOML files are current.
"""
from __future__ import annotations

import os

from fastapi import APIRouter

from schema import DATA_FORMAT_VERSION
from catalog.api.schemas import MetaOut

router = APIRouter()


@router.get("", response_model=MetaOut)
def get_meta() -> MetaOut:
    return MetaOut(
        portal_version=os.getenv("PORTAL_VERSION", "dev"),
        data_format_version=DATA_FORMAT_VERSION,
    )
