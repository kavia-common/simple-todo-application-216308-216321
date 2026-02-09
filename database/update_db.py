#!/usr/bin/env python3
"""Apply SQLite schema updates/migrations for this container.

Why this exists:
- `init_db.py` is safe to re-run, but this script provides an explicit "update" path
  that can be invoked independently by other containers or automation.

Design:
- Uses idempotent DDL (IF NOT EXISTS) rather than maintaining separate .sql files.

Run:
  python3 update_db.py
"""

import os
import sqlite3

DB_NAME = "myapp.db"


def _connect() -> sqlite3.Connection:
    """Create a SQLite connection with recommended pragmas."""
    conn = sqlite3.connect(DB_NAME)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


def _apply(conn: sqlite3.Connection) -> None:
    """Apply schema updates (idempotent)."""
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS todos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            completed INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_todos_completed ON todos(completed)"
    )


def main() -> None:
    """Entrypoint to apply updates."""
    if not os.path.exists(DB_NAME):
        raise SystemExit(
            f"Database file '{DB_NAME}' not found. Run init_db.py first to create it."
        )

    conn = _connect()
    try:
        _apply(conn)
        conn.commit()
    finally:
        conn.close()

    print("Database update complete (todos table ensured).")


if __name__ == "__main__":
    main()
