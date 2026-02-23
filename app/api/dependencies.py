"""
app/api/dependencies.py — Shared FastAPI dependencies.

Provides database connection and service singletons
via FastAPI's dependency injection system.
"""

import sqlite3
from typing import Generator

from config import DATABASE_PATH  # type: ignore
from app.database.init_db import get_connection  # type: ignore


def get_db() -> Generator[sqlite3.Connection, None, None]:
    """
    FastAPI dependency: yields a SQLite connection per request,
    ensures connection is closed after request completes.
    """
    conn = get_connection(DATABASE_PATH)
    try:
        yield conn
    finally:
        conn.close()
