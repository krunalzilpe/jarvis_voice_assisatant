from __future__ import annotations

from contextlib import closing
import json
import sqlite3
from pathlib import Path

from .models import ActionResult, CommandRecord


class HistoryStore:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with closing(self._connect()) as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS command_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    raw_command TEXT NOT NULL,
                    interpreted_intent TEXT NOT NULL,
                    target TEXT,
                    executed_steps TEXT NOT NULL,
                    success INTEGER NOT NULL,
                    follow_up_kind TEXT,
                    error TEXT,
                    created_at TEXT NOT NULL
                )
                """
            )
            connection.commit()

    def record(self, record: CommandRecord) -> None:
        with closing(self._connect()) as connection:
            connection.execute(
                """
                INSERT INTO command_history (
                    raw_command,
                    interpreted_intent,
                    target,
                    executed_steps,
                    success,
                    follow_up_kind,
                    error,
                    created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.raw_command,
                    record.interpreted_intent,
                    record.target,
                    json.dumps(record.executed_steps),
                    int(record.success),
                    record.follow_up_kind,
                    record.error,
                    record.created_at.isoformat(),
                ),
            )
            connection.commit()

    def recent(self, limit: int = 50) -> list[dict]:
        with closing(self._connect()) as connection:
            rows = connection.execute(
                """
                SELECT raw_command, interpreted_intent, target, executed_steps, success, follow_up_kind, error, created_at
                FROM command_history
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [dict(row) for row in rows]

    def summarize_result(self, raw_command: str, result: ActionResult) -> CommandRecord:
        return CommandRecord(
            raw_command=raw_command,
            interpreted_intent=result.interpreted_intent,
            target=result.target,
            executed_steps=result.steps,
            success=result.success,
            follow_up_kind=result.follow_up_question if result.requires_follow_up else None,
            error=result.error,
        )
