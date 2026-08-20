"""Environment and configuration helpers for exercise 1."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable

BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent


def load_dotenv(dotenv_paths: Iterable[Path | str] | None = None) -> None:
    """Load key=value pairs from .env files into process environment."""
    paths = list(dotenv_paths or [PROJECT_ROOT / ".env", BASE_DIR / ".env"])
    for raw_path in paths:
        dotenv_path = Path(raw_path)
        if not dotenv_path.exists():
            continue

        with dotenv_path.open("r", encoding="utf-8") as env_file:
            for raw_line in env_file:
                line = raw_line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue

                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                if key:
                    os.environ.setdefault(key, value)


def get_openai_api_key() -> str:
    """Return OPENAI_API_KEY value from environment variables."""
    return os.getenv("OPENAI_API_KEY", "").strip()


def get_serpapi_api_key() -> str:
    """Return SERPAPI_API_KEY value from environment variables."""
    return os.getenv("SERPAPI_API_KEY", "").strip()
