"""Stable JSON serialization helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def write_json(path: str | Path, value: Any) -> Path:
    output = Path(path).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = value.to_dict() if hasattr(value, "to_dict") else value
    output.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return output
