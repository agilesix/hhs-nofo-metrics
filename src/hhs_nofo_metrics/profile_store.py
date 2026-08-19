"""Load immutable packaged metric profiles."""

from __future__ import annotations

import hashlib
import json
from importlib.resources import files
from typing import Any

from hhs_nofo_metrics.errors import ProfileError
from hhs_nofo_metrics.models import MetricProfile

_PROFILE_FILES = {
    "hhs-nofo-fy27-html@0.4.0": "hhs-nofo-fy27-html-0.4.0.json",
    "hhs-nofo-fy27-pdf-estimate@0.5.0": "hhs-nofo-fy27-pdf-estimate-0.5.0.json",
    "hhs-nofo-fy27-generic-pdf-estimate@0.4.0": (
        "hhs-nofo-fy27-generic-pdf-estimate-0.4.0.json"
    ),
}


def list_profile_references() -> list[str]:
    return sorted(_PROFILE_FILES)


def load_profile_record(reference: str) -> tuple[MetricProfile, str]:
    filename = _PROFILE_FILES.get(reference)
    if filename is None:
        raise ProfileError(
            f"Unknown profile {reference!r}; available: "
            + ", ".join(list_profile_references())
        )
    resource = files("hhs_nofo_metrics.profiles").joinpath(filename)
    raw = resource.read_bytes()
    try:
        value: Any = json.loads(raw)
        profile = MetricProfile.from_dict(value)
    except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        raise ProfileError(f"Invalid packaged profile {reference}: {exc}") from exc
    if profile.reference != reference:
        raise ProfileError(
            f"Profile file identity {profile.reference} does not match {reference}"
        )
    return profile, hashlib.sha256(raw).hexdigest()
