from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from backend.models.session import TripSession


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class TripSessionStore:
    def __init__(self, database_path: str | Path | None = None) -> None:
        configured = database_path or os.getenv("TRAVELDORIS_DB_PATH")
        self.database_path = Path(configured or "backend/data/traveldoris.db")
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS trip_sessions (
                    id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    payload TEXT NOT NULL
                )
                """
            )

    def create(self) -> TripSession:
        now = _now()
        session = TripSession(id=str(uuid4()), created_at=now, updated_at=now)
        self.save(session)
        return session

    def get(self, session_id: str) -> TripSession | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT payload FROM trip_sessions WHERE id = ?", (session_id,)
            ).fetchone()
        return TripSession.model_validate_json(row["payload"]) if row else None

    def save(self, session: TripSession) -> TripSession:
        session.updated_at = _now()
        payload = json.dumps(session.model_dump(mode="json"))
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO trip_sessions (id, created_at, updated_at, payload)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    updated_at = excluded.updated_at,
                    payload = excluded.payload
                """,
                (session.id, session.created_at, session.updated_at, payload),
            )
        return session
