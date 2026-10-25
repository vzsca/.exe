"""Small SQLite persistence layer for user scripts, events, and access control."""

from contextlib import contextmanager
from pathlib import Path
import re
import sqlite3
from typing import Iterator


_NAME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_-]{0,31}$")


class StorageError(ValueError):
    """Raised when a stored item has an invalid name or cannot be found."""


class Database:
    def __init__(self, path: str = "data/exe.sqlite3") -> None:
        self.path = path
        if path != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.initialize()

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.path, timeout=5.0)
        connection.row_factory = sqlite3.Row
        try:
            connection.execute("PRAGMA foreign_keys = ON")
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def initialize(self) -> None:
        with self._connect() as db:
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS whitelist (
                    user_id INTEGER PRIMARY KEY CHECK (user_id > 0),
                    added_by INTEGER NOT NULL CHECK (added_by > 0),
                    added_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS scripts (
                    owner_id INTEGER NOT NULL CHECK (owner_id > 0),
                    name TEXT NOT NULL,
                    source TEXT NOT NULL,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (owner_id, name)
                );

                CREATE TABLE IF NOT EXISTS event_handlers (
                    owner_id INTEGER NOT NULL CHECK (owner_id > 0),
                    event_name TEXT NOT NULL,
                    source TEXT NOT NULL,
                    enabled INTEGER NOT NULL DEFAULT 1 CHECK (enabled IN (0, 1)),
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (owner_id, event_name)
                );
                """
            )

    @staticmethod
    def _validate_name(name: str) -> str:
        if not _NAME_RE.fullmatch(name):
            raise StorageError(
                "Name must start with a letter and contain only letters, numbers, '_' or '-'."
            )
        return name

    def add_whitelist(self, user_id: int, added_by: int) -> bool:
        if user_id <= 0 or added_by <= 0:
            raise StorageError("Discord user IDs must be positive integers.")
        with self._connect() as db:
            cursor = db.execute(
                "INSERT OR IGNORE INTO whitelist (user_id, added_by) VALUES (?, ?)",
                (user_id, added_by),
            )
            return cursor.rowcount == 1

    def remove_whitelist(self, user_id: int) -> bool:
        with self._connect() as db:
            cursor = db.execute("DELETE FROM whitelist WHERE user_id = ?", (user_id,))
            return cursor.rowcount == 1

    def list_whitelist(self) -> list[int]:
        with self._connect() as db:
            rows = db.execute("SELECT user_id FROM whitelist ORDER BY user_id").fetchall()
            return [int(row["user_id"]) for row in rows]

    def is_whitelisted(self, user_id: int) -> bool:
        with self._connect() as db:
            row = db.execute(
                "SELECT 1 FROM whitelist WHERE user_id = ?",
                (user_id,),
            ).fetchone()
            return row is not None

    def save_script(self, owner_id: int, name: str, source: str) -> None:
        self._validate_name(name)
        if owner_id <= 0:
            raise StorageError("Owner ID must be a positive integer.")
        if not source.strip() or len(source) > 8000:
            raise StorageError("Script must contain between 1 and 8000 characters.")
        with self._connect() as db:
            db.execute(
                """
                INSERT INTO scripts (owner_id, name, source, updated_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(owner_id, name) DO UPDATE SET
                    source = excluded.source,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (owner_id, name, source),
            )

    def get_script(self, owner_id: int, name: str) -> str | None:
        self._validate_name(name)
        with self._connect() as db:
            row = db.execute(
                "SELECT source FROM scripts WHERE owner_id = ? AND name = ?",
                (owner_id, name),
            ).fetchone()
            return str(row["source"]) if row else None

    def list_scripts(self, owner_id: int) -> list[str]:
        with self._connect() as db:
            rows = db.execute(
                "SELECT name FROM scripts WHERE owner_id = ? ORDER BY name",
                (owner_id,),
            ).fetchall()
            return [str(row["name"]) for row in rows]

    def delete_script(self, owner_id: int, name: str) -> bool:
        self._validate_name(name)
        with self._connect() as db:
            cursor = db.execute(
                "DELETE FROM scripts WHERE owner_id = ? AND name = ?",
                (owner_id, name),
            )
            return cursor.rowcount == 1

    def save_event(self, owner_id: int, event_name: str, source: str, *, enabled: bool = True) -> None:
        self._validate_name(event_name)
        if owner_id <= 0:
            raise StorageError("Owner ID must be a positive integer.")
        if not source.strip() or len(source) > 8000:
            raise StorageError("Event script must contain between 1 and 8000 characters.")
        with self._connect() as db:
            db.execute(
                """
                INSERT INTO event_handlers (owner_id, event_name, source, enabled, updated_at)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(owner_id, event_name) DO UPDATE SET
                    source = excluded.source,
                    enabled = excluded.enabled,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (owner_id, event_name, source, int(enabled)),
            )

    def get_event(self, owner_id: int, event_name: str) -> tuple[str, bool] | None:
        self._validate_name(event_name)
        with self._connect() as db:
            row = db.execute(
                "SELECT source, enabled FROM event_handlers WHERE owner_id = ? AND event_name = ?",
                (owner_id, event_name),
            ).fetchone()
            if row is None:
                return None
            return str(row["source"]), bool(row["enabled"])

    def list_events(self, owner_id: int) -> list[str]:
        with self._connect() as db:
            rows = db.execute(
                "SELECT event_name FROM event_handlers WHERE owner_id = ? ORDER BY event_name",
                (owner_id,),
            ).fetchall()
            return [str(row["event_name"]) for row in rows]

    def delete_event(self, owner_id: int, event_name: str) -> bool:
        self._validate_name(event_name)
        with self._connect() as db:
            cursor = db.execute(
                "DELETE FROM event_handlers WHERE owner_id = ? AND event_name = ?",
                (owner_id, event_name),
            )
            return cursor.rowcount == 1
