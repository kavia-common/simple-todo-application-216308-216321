#!/usr/bin/env python3
"""Initialize SQLite database for database.

This script is intended to be safely re-runnable:
- It creates required tables/indexes with IF NOT EXISTS.
- It stores minimal schema metadata in app_info for reproducibility.

Run:
  python3 init_db.py
"""

import os
import sqlite3
from typing import Optional

DB_NAME = "myapp.db"
DB_USER = "kaviasqlite"  # Not used for SQLite, but kept for consistency
DB_PASSWORD = "kaviadefaultpassword"  # Not used for SQLite, but kept for consistency
DB_PORT = "5000"  # Not used for SQLite, but kept for consistency

SCHEMA_VERSION = "0.2.0"  # Bump when schema changes in this container


def _get_connection(db_name: str) -> sqlite3.Connection:
    """Create a SQLite connection with recommended pragmas."""
    conn = sqlite3.connect(db_name)
    conn.row_factory = sqlite3.Row
    # Enable foreign key enforcement (safe even if we don't use FKs yet)
    conn.execute("PRAGMA foreign_keys = ON")
    # Improve concurrency (best-effort; still works if it can't be set)
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


def _ensure_core_schema(conn: sqlite3.Connection) -> None:
    """Create baseline tables used for metadata and example content."""
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS app_info (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key TEXT UNIQUE NOT NULL,
            value TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    # Sample users table (kept as it existed in the template)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )


def _ensure_todos_schema(conn: sqlite3.Connection) -> None:
    """Create todos table and indexes (idempotent)."""
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

    # Index to speed up common filtering (e.g., completed vs active)
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_todos_completed ON todos(completed)"
    )


def _set_app_info(conn: sqlite3.Connection, key: str, value: Optional[str]) -> None:
    """Upsert metadata into app_info."""
    conn.execute(
        "INSERT OR REPLACE INTO app_info (key, value) VALUES (?, ?)",
        (key, value),
    )


def _write_connection_info(db_name: str) -> None:
    """Write db_connection.txt with canonical connection info for this workspace."""
    current_dir = os.getcwd()
    connection_string = f"sqlite:///{current_dir}/{db_name}"

    with open("db_connection.txt", "w", encoding="utf-8") as f:
        f.write("# SQLite connection methods:\n")
        f.write(f"# Python: sqlite3.connect('{db_name}')\n")
        f.write(f"# Connection string: {connection_string}\n")
        f.write(f"# File path: {current_dir}/{db_name}\n")


def _write_visualizer_env(db_name: str) -> None:
    """Write db_visualizer/sqlite.env used by the bundled Node DB viewer."""
    db_path = os.path.abspath(db_name)
    os.makedirs("db_visualizer", exist_ok=True)
    with open("db_visualizer/sqlite.env", "w", encoding="utf-8") as f:
        f.write(f'export SQLITE_DB="{db_path}"\n')


def main() -> None:
    """Entrypoint for database initialization (safe to re-run)."""
    print("Starting SQLite setup...")

    db_exists = os.path.exists(DB_NAME)
    if db_exists:
        print(f"SQLite database already exists at {DB_NAME}")
        try:
            conn = _get_connection(DB_NAME)
            conn.execute("SELECT 1")
            conn.close()
            print("Database is accessible and working.")
        except Exception as e:
            print(f"Warning: Database exists but may be corrupted: {e}")
    else:
        print("Creating new SQLite database...")

    conn = _get_connection(DB_NAME)
    try:
        _ensure_core_schema(conn)
        _ensure_todos_schema(conn)

        # Insert/update metadata (idempotent)
        _set_app_info(conn, "project_name", "database")
        _set_app_info(conn, "version", "0.1.0")
        _set_app_info(conn, "author", "John Doe")
        _set_app_info(conn, "description", "")
        _set_app_info(conn, "schema_version", SCHEMA_VERSION)

        conn.commit()

        # Stats
        table_count = conn.execute(
            "SELECT COUNT(*) AS c FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        ).fetchone()["c"]
        record_count = conn.execute(
            "SELECT COUNT(*) AS c FROM app_info"
        ).fetchone()["c"]

    finally:
        conn.close()

    # Save connection information to a file
    try:
        _write_connection_info(DB_NAME)
        print("Connection information saved to db_connection.txt")
    except Exception as e:
        print(f"Warning: Could not save connection info: {e}")

    # Create environment variables file for Node.js viewer
    try:
        _write_visualizer_env(DB_NAME)
        print("Environment variables saved to db_visualizer/sqlite.env")
    except Exception as e:
        print(f"Warning: Could not save environment variables: {e}")

    current_dir = os.getcwd()
    connection_string = f"sqlite:///{current_dir}/{DB_NAME}"

    print("\nSQLite setup complete!")
    print(f"Database: {DB_NAME}")
    print(f"Location: {current_dir}/{DB_NAME}")
    print("")
    print("To use with Node.js viewer, run: source db_visualizer/sqlite.env")
    print("\nTo connect to the database, use one of the following methods:")
    print(f"1. Python: sqlite3.connect('{DB_NAME}')")
    print(f"2. Connection string: {connection_string}")
    print(f"3. Direct file access: {current_dir}/{DB_NAME}")
    print("")
    print("Database statistics:")
    print(f"  Tables: {table_count}")
    print(f"  App info records: {record_count}")

    # If sqlite3 CLI is available, show how to use it
    try:
        import subprocess

        result = subprocess.run(["which", "sqlite3"], capture_output=True, text=True, check=False)
        if result.returncode == 0:
            print("")
            print("SQLite CLI is available. You can also use:")
            print(f"  sqlite3 {DB_NAME}")
    except Exception:
        pass

    print("\nScript completed successfully.")


if __name__ == "__main__":
    main()
