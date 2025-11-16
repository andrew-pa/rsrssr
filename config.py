"""Runtime configuration helpers for RSRSSR."""
from __future__ import annotations

import os
from pathlib import Path
from functools import lru_cache

_DEFAULT_DB_RELATIVE = Path("instance") / "rss_feeds.db"


def _resolve_db_path() -> Path:
    raw_path = os.environ.get("RSRSSR_DB_PATH")
    path = Path(raw_path) if raw_path else _DEFAULT_DB_RELATIVE
    if not path.is_absolute():
        path = Path.cwd() / path
    parent = path.parent
    if parent:
        parent.mkdir(parents=True, exist_ok=True)
    return path


@lru_cache(maxsize=1)
def database_path() -> Path:
    """Return the absolute path to the SQLite database file."""
    return _resolve_db_path()


def database_uri() -> str:
    """Return a SQLAlchemy-compatible URI for the configured database."""
    path = database_path()
    return f"sqlite:///{path}"
