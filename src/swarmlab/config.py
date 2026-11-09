"""YAML execution configuration without credentials or inferred provider prices."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

import yaml


def check_no_credentials(value: object) -> None:
    """Reject credential fields before a configuration can be persisted."""
    if isinstance(value, Mapping):
        for key, item in value.items():
            if str(key).lower() in {"api_key", "password", "secret", "authorization", "token"}:
                raise ValueError("Credentials must come from environment variables")
            check_no_credentials(item)
    elif isinstance(value, list):
        for item in value:
            check_no_credentials(item)


def load_config(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Configuration must be a YAML mapping")
    check_no_credentials(data)
    return data
