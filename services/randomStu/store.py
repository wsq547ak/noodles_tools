from __future__ import annotations

import hashlib
import json
import os
import secrets
import sqlite3
import time
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, time as datetime_time, timedelta
from pathlib import Path
from typing import Any, Iterator
from zoneinfo import ZoneInfo

DEFAULT_DB_PATH = Path(__file__).parents[2] / "data" / "randomStu.sqlite3"
MAX_CLASSROOMS = 100
MAX_STUDENTS_PER_CLASSROOM = 2_000


class RevisionConflictError(Exception):
    def __init__(self, current_revision: int) -> None:
        super().__init__("远端数据已在其他设备更新，请刷新后重试。")
        self.current_revision = current_revision


@dataclass(frozen=True)
class StoredState:
    data: dict[str, Any] | None
    revision: int
    updated_at: str | None


class RandomStuStore:
    def __init__(self, db_path: str | Path | None = None) -> None:
        configured_path = os.environ.get("RANDOMSTU_DB_PATH", "").strip()
        self.db_path = Path(db_path or configured_path or DEFAULT_DB_PATH).expanduser()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def get_state(self) -> StoredState:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT data_json, revision, updated_at FROM random_stu_state WHERE id = 1"
            ).fetchone()
        if row is None:
            return StoredState(data=None, revision=0, updated_at=None)
        return StoredState(
            data=json.loads(row["data_json"]),
            revision=int(row["revision"]),
            updated_at=str(row["updated_at"]),
        )

    def save_state(
        self,
        data: dict[str, Any],
        expected_revision: int,
    ) -> StoredState:
        normalized = validate_random_stu_data(data)
        serialized = json.dumps(normalized, ensure_ascii=False, separators=(",", ":"))
        updated_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT revision FROM random_stu_state WHERE id = 1"
            ).fetchone()
            current_revision = int(row["revision"]) if row else 0
            if current_revision != expected_revision:
                raise RevisionConflictError(current_revision)
            next_revision = current_revision + 1
            connection.execute(
                """
                INSERT INTO random_stu_state (id, data_json, revision, updated_at)
                VALUES (1, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    data_json = excluded.data_json,
                    revision = excluded.revision,
                    updated_at = excluded.updated_at
                """,
                (serialized, next_revision, updated_at),
            )

        return StoredState(normalized, next_revision, updated_at)

    def create_session(self) -> str:
        token = secrets.token_urlsafe(32)
        token_hash = _token_hash(token)
        day_key, expires_at = _session_day_and_expiry()
        with self._connect() as connection:
            connection.execute("DELETE FROM random_stu_sessions WHERE expires_at <= ?", (int(time.time()),))
            connection.execute(
                "INSERT INTO random_stu_sessions (token_hash, expires_at, day_key) VALUES (?, ?, ?)",
                (token_hash, expires_at, day_key),
            )
        return token

    def has_session(self, token: str) -> bool:
        if not token:
            return False
        now = int(time.time())
        day_key, _ = _session_day_and_expiry()
        with self._connect() as connection:
            connection.execute("DELETE FROM random_stu_sessions WHERE expires_at <= ?", (now,))
            row = connection.execute(
                """
                SELECT 1 FROM random_stu_sessions
                WHERE token_hash = ? AND expires_at > ? AND day_key = ?
                """,
                (_token_hash(token), now, day_key),
            ).fetchone()
        return row is not None

    def delete_session(self, token: str) -> None:
        if not token:
            return
        with self._connect() as connection:
            connection.execute(
                "DELETE FROM random_stu_sessions WHERE token_hash = ?",
                (_token_hash(token),),
            )

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.db_path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA journal_mode = WAL")
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS random_stu_state (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    data_json TEXT NOT NULL,
                    revision INTEGER NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS random_stu_sessions (
                    token_hash TEXT PRIMARY KEY,
                    expires_at INTEGER NOT NULL,
                    day_key TEXT
                );
                CREATE INDEX IF NOT EXISTS idx_random_stu_sessions_expires
                    ON random_stu_sessions(expires_at);
                """
            )
            columns = {
                str(row["name"])
                for row in connection.execute("PRAGMA table_info(random_stu_sessions)")
            }
            if "day_key" not in columns:
                connection.execute("ALTER TABLE random_stu_sessions ADD COLUMN day_key TEXT")


def validate_random_stu_data(value: object) -> dict[str, Any]:
    if not isinstance(value, dict) or value.get("version") != 1:
        raise ValueError("名单数据版本无效。")
    classrooms = value.get("classrooms")
    if not isinstance(classrooms, list) or len(classrooms) > MAX_CLASSROOMS:
        raise ValueError("班级数据无效或数量过多。")

    normalized_classrooms: list[dict[str, Any]] = []
    classroom_ids: set[str] = set()
    for classroom in classrooms:
        if not isinstance(classroom, dict):
            raise ValueError("班级数据格式无效。")
        classroom_id = _required_text(classroom.get("id"), "班级 ID", 200)
        if classroom_id in classroom_ids:
            raise ValueError("班级 ID 重复。")
        classroom_ids.add(classroom_id)
        students = classroom.get("students")
        if not isinstance(students, list) or len(students) > MAX_STUDENTS_PER_CLASSROOM:
            raise ValueError("学生名单无效或数量过多。")
        normalized_students = [_validate_student(student) for student in students]
        normalized_classrooms.append(
            {
                "id": classroom_id,
                "name": _required_text(classroom.get("name"), "班级名称", 200),
                "students": normalized_students,
                "locked": bool(classroom.get("locked", False)),
                "createdAt": _required_text(classroom.get("createdAt"), "创建时间", 100),
                "updatedAt": _required_text(classroom.get("updatedAt"), "更新时间", 100),
            }
        )

    active_id = value.get("activeClassroomId")
    if active_id is not None and active_id not in classroom_ids:
        active_id = normalized_classrooms[0]["id"] if normalized_classrooms else None
    return {"version": 1, "classrooms": normalized_classrooms, "activeClassroomId": active_id}


def _validate_student(value: object) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError("学生数据格式无效。")
    return {
        "id": _required_text(value.get("id"), "学生 ID", 200),
        "number": _optional_text(value.get("number"), 100),
        "name": _required_text(value.get("name"), "学生姓名", 200),
        "enabled": bool(value.get("enabled", True)),
    }


def _required_text(value: object, field: str, max_length: int) -> str:
    text = str(value or "").strip()
    if not text or len(text) > max_length:
        raise ValueError(f"{field}无效。")
    return text


def _optional_text(value: object, max_length: int) -> str:
    text = str(value or "").strip()
    if len(text) > max_length:
        raise ValueError("文本字段过长。")
    return text


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _session_day_and_expiry() -> tuple[str, int]:
    timezone_name = os.environ.get("RANDOMSTU_TIMEZONE", "Asia/Shanghai").strip()
    try:
        timezone = ZoneInfo(timezone_name)
    except Exception as error:
        raise ValueError(f"无效的 RANDOMSTU_TIMEZONE: {timezone_name}") from error
    now = datetime.now(timezone)
    tomorrow = now.date() + timedelta(days=1)
    next_midnight = datetime.combine(tomorrow, datetime_time.min, tzinfo=timezone)
    return now.date().isoformat(), int(next_midnight.timestamp())
