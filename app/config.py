"""Small, secret-safe configuration helpers for local development."""

from __future__ import annotations

import os
from pathlib import Path


FIGMA_ACCESS_TOKEN_KEY = "FIGMA_ACCESS_TOKEN"
ENV_FILE = Path(__file__).resolve().parents[1] / ".env"


def _read_env_value(key: str, env_file: Path = ENV_FILE) -> str | None:
    """Read one simple KEY=value entry without loading or logging every value."""
    if not env_file.is_file():
        return None

    for raw_line in env_file.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        if name.strip() == key:
            return value.strip().strip('"').strip("'") or None
    return None


def figma_token_configured() -> bool:
    """Return only whether a Figma token exists; never return the token itself."""
    return bool(os.getenv(FIGMA_ACCESS_TOKEN_KEY) or _read_env_value(FIGMA_ACCESS_TOKEN_KEY))
