from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sqlite3
from typing import Any, Iterable


class LedgerError(RuntimeError):
    pass


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


class EventLedger:
    """Append-only, hash-chained SQLite event ledger.

    Events cannot be updated or deleted through SQL after insertion.
    Current state is reconstructed from events rather than trusted mutable rows.
    """

    def __init__(self, path: str | Path):
        self.path = Path(path).expanduser().resolve()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        con = sqlite3.connect(self.path)
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA foreign_keys=ON")
        return con

    def _init_db(self) -> None:
        with self._connect() as con:
            con.executescript(
                """
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS events (
                    seq INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id TEXT NOT NULL UNIQUE,
                    created_at TEXT NOT NULL,
                    task_id TEXT,
                    event_type TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    prev_hash TEXT,
                    event_hash TEXT NOT NULL UNIQUE
                );
                CREATE TRIGGER IF NOT EXISTS events_no_update
                BEFORE UPDATE ON events
                BEGIN
                    SELECT RAISE(ABORT, 'events are append-only');
                END;
                CREATE TRIGGER IF NOT EXISTS events_no_delete
                BEFORE DELETE ON events
                BEGIN
                    SELECT RAISE(ABORT, 'events are append-only');
                END;
                CREATE INDEX IF NOT EXISTS idx_events_task_seq
                    ON events(task_id, seq);
                """
            )

    def append(
        self,
        event_type: str,
        payload: dict[str, Any],
        *,
        task_id: str | None = None,
        event_id: str | None = None,
        created_at: str | None = None,
    ) -> dict[str, Any]:
        if not event_type.strip():
            raise LedgerError("event_type required")
        created_at = created_at or _now()
        with self._connect() as con:
            row = con.execute(
                "SELECT event_hash FROM events ORDER BY seq DESC LIMIT 1"
            ).fetchone()
            prev_hash = row["event_hash"] if row else None
            if event_id is None:
                seed = _canonical({
                    "event_type": event_type,
                    "task_id": task_id,
                    "payload": payload,
                    "created_at": created_at,
                    "prev_hash": prev_hash,
                })
                event_id = "evt_" + hashlib.sha256(seed.encode("utf-8")).hexdigest()[:24]
            body = {
                "event_id": event_id,
                "created_at": created_at,
                "task_id": task_id,
                "event_type": event_type,
                "payload": payload,
                "prev_hash": prev_hash,
            }
            event_hash = hashlib.sha256(_canonical(body).encode("utf-8")).hexdigest()
            try:
                cur = con.execute(
                    """
                    INSERT INTO events(
                        event_id, created_at, task_id, event_type,
                        payload_json, prev_hash, event_hash
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        event_id,
                        created_at,
                        task_id,
                        event_type,
                        _canonical(payload),
                        prev_hash,
                        event_hash,
                    ),
                )
            except sqlite3.IntegrityError as exc:
                raise LedgerError(str(exc)) from exc
            seq = cur.lastrowid
        return {
            "seq": seq,
            **body,
            "event_hash": event_hash,
        }

    def events(self, *, task_id: str | None = None) -> list[dict[str, Any]]:
        sql = "SELECT * FROM events"
        args: tuple[Any, ...] = ()
        if task_id is not None:
            sql += " WHERE task_id=?"
            args = (task_id,)
        sql += " ORDER BY seq"
        with self._connect() as con:
            rows = con.execute(sql, args).fetchall()
        return [
            {
                "seq": int(row["seq"]),
                "event_id": row["event_id"],
                "created_at": row["created_at"],
                "task_id": row["task_id"],
                "event_type": row["event_type"],
                "payload": json.loads(row["payload_json"]),
                "prev_hash": row["prev_hash"],
                "event_hash": row["event_hash"],
            }
            for row in rows
        ]

    def verify_chain(self) -> dict[str, Any]:
        previous = None
        rows = self.events()
        for row in rows:
            body = {
                "event_id": row["event_id"],
                "created_at": row["created_at"],
                "task_id": row["task_id"],
                "event_type": row["event_type"],
                "payload": row["payload"],
                "prev_hash": row["prev_hash"],
            }
            expected = hashlib.sha256(_canonical(body).encode("utf-8")).hexdigest()
            if row["prev_hash"] != previous or row["event_hash"] != expected:
                return {
                    "valid": False,
                    "failed_seq": row["seq"],
                    "event_id": row["event_id"],
                }
            previous = row["event_hash"]
        return {
            "valid": True,
            "event_count": len(rows),
            "head_hash": previous,
        }

    def latest(self, task_id: str, event_type: str) -> dict[str, Any] | None:
        with self._connect() as con:
            row = con.execute(
                """
                SELECT * FROM events
                WHERE task_id=? AND event_type=?
                ORDER BY seq DESC LIMIT 1
                """,
                (task_id, event_type),
            ).fetchone()
        if row is None:
            return None
        return {
            "seq": int(row["seq"]),
            "event_id": row["event_id"],
            "created_at": row["created_at"],
            "task_id": row["task_id"],
            "event_type": row["event_type"],
            "payload": json.loads(row["payload_json"]),
            "prev_hash": row["prev_hash"],
            "event_hash": row["event_hash"],
        }
