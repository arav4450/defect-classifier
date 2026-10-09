"""
Feedback storage.

A single sqlite file is fine for a demo or single-process deployment.
If you need multi-process writes, point FEEDBACK_DB_PATH at a real
Database backend instead. Swapping that in only touches this file.
"""

import os
import sqlite3
import time
from contextlib import contextmanager

from app.config import settings

_SCHEMA = """
CREATE TABLE IF NOT EXISTS feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    request_id TEXT NOT NULL,
    rating INTEGER NOT NULL,
    comment TEXT,
    created_at REAL NOT NULL
);
"""


@contextmanager
def _connect():
    os.makedirs(os.path.dirname(settings.FEEDBACK_DB_PATH) or ".", exist_ok=True)
    conn = sqlite3.connect(settings.FEEDBACK_DB_PATH)
    try:
        yield conn
    finally:
        conn.close()


def init_db() -> None:
    with _connect() as conn:
        conn.execute(_SCHEMA)
        conn.commit()


def record_feedback(request_id: str, rating: int, comment: str = "") -> None:
    with _connect() as conn:
        conn.execute(
            "INSERT INTO feedback (request_id, rating, comment, created_at) VALUES (?, ?, ?, ?)",
            (request_id, rating, comment, time.time()),
        )
        conn.commit()
