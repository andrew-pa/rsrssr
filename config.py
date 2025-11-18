"""Runtime configuration helpers for RSRSSR."""
from __future__ import annotations

import os
from pathlib import Path
from functools import lru_cache
from typing import Dict, Type

from sqlalchemy.orm import Session as SQLASession

from db_mirror import DatabaseMirror, build_mirrored_session_class

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
def _database_mirror() -> DatabaseMirror:
    path = _resolve_db_path()
    remote_uri = os.environ.get("RSRSSR_DB_GCS_URI")
    mirror = DatabaseMirror(path, remote_uri)
    mirror.ensure_local_copy()
    return mirror


def database_path() -> Path:
    """Return the absolute path to the SQLite database file."""
    return _database_mirror().local_path


def database_uri() -> str:
    """Return a SQLAlchemy-compatible URI for the configured database."""
    path = database_path()
    return f"sqlite:///{path}"


def database_mirror() -> DatabaseMirror:
    return _database_mirror()


_SESSION_CLASS_CACHE: Dict[Type[SQLASession], Type[SQLASession]] = {}


def database_session_class(base: Type[SQLASession] | None = None) -> Type[SQLASession]:
    base_cls = base or SQLASession
    if base_cls not in _SESSION_CLASS_CACHE:
        _SESSION_CLASS_CACHE[base_cls] = build_mirrored_session_class(
            _database_mirror(), base_cls
        )
    return _SESSION_CLASS_CACHE[base_cls]
