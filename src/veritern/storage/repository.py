import json
import sqlite3
import threading
from contextlib import contextmanager
from datetime import timedelta
from pathlib import Path

from veritern.schemas import Case, now


class Repository:
    """All mutations check owner and tombstone inside the same transaction."""

    def __init__(self, root: Path):
        self.root = root.resolve()
        if self.root in (Path(self.root.anchor), Path.home(), Path.cwd()):
            raise ValueError("Unsafe storage root")
        self.root.mkdir(parents=True, exist_ok=True)
        self.path = self.root / "veritern.sqlite3"
        self.lock = threading.RLock()
        self.migrate()

    @contextmanager
    def connect(self):
        con = sqlite3.connect(self.path, timeout=10)
        con.execute("PRAGMA foreign_keys=ON")
        con.execute("PRAGMA busy_timeout=10000")
        try:
            with con:
                yield con
        finally:
            con.close()

    def migrate(self):
        with self.connect() as con:
            con.execute("PRAGMA journal_mode=WAL")
            con.executescript("""
            CREATE TABLE IF NOT EXISTS cases (
              id TEXT PRIMARY KEY, owner TEXT NOT NULL, payload TEXT NOT NULL,
              deleted INTEGER NOT NULL DEFAULT 0, saved INTEGER NOT NULL DEFAULT 0,
              updated TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS jobs (
              key TEXT PRIMARY KEY, case_id TEXT NOT NULL REFERENCES cases(id),
              owner TEXT NOT NULL, phase TEXT NOT NULL, message TEXT NOT NULL,
              cancelled INTEGER NOT NULL DEFAULT 0);
            CREATE TABLE IF NOT EXISTS cache (
              key TEXT PRIMARY KEY, payload TEXT NOT NULL, expires TEXT NOT NULL);
            PRAGMA user_version=1;
            """)

    def create(self, case: Case):
        with self.connect() as con:
            con.execute(
                "INSERT INTO cases(id,owner,payload,saved,updated) VALUES(?,?,?,?,?)",
                (case.id, case.owner, case.model_dump_json(), case.saved, now().isoformat()),
            )

    def save(self, case: Case):
        Case.model_validate(case.model_dump())
        with self.connect() as con:
            cursor = con.execute(
                "UPDATE cases SET payload=?, saved=?, updated=? WHERE id=? AND owner=? AND deleted=0",
                (case.model_dump_json(), case.saved, now().isoformat(), case.id, case.owner),
            )
            if cursor.rowcount != 1:
                raise ValueError("Case unavailable or deleted")

    def get(self, case_id: str, owner: str) -> Case | None:
        with self.connect() as con:
            row = con.execute(
                "SELECT payload FROM cases WHERE id=? AND owner=? AND deleted=0", (case_id, owner)
            ).fetchone()
        return Case.model_validate_json(row[0]) if row else None

    def list_saved(self) -> list[Case]:
        # Called only by the single-user localhost library, never by protected deployments.
        with self.connect() as con:
            rows = con.execute(
                "SELECT payload FROM cases WHERE saved=1 AND deleted=0 ORDER BY updated DESC"
            ).fetchall()
        return [Case.model_validate_json(row[0]) for row in rows]

    def delete(self, case_id: str, owner: str):
        with self.connect() as con:
            con.execute(
                "UPDATE cases SET deleted=1,payload='{}' WHERE id=? AND owner=?", (case_id, owner)
            )
            con.execute(
                "UPDATE jobs SET cancelled=1,phase='cancelled',message='Case deleted' WHERE case_id=? AND owner=?",
                (case_id, owner),
            )
        # Raw uploads are processed in memory and never stored. The tombstone is content-free.

    def claim_job(self, key: str, case_id: str, owner: str) -> bool:
        with self.connect() as con:
            if not con.execute(
                "SELECT 1 FROM cases WHERE id=? AND owner=? AND deleted=0", (case_id, owner)
            ).fetchone():
                return False
            cursor = con.execute(
                "INSERT OR IGNORE INTO jobs VALUES(?,?,?,'queued','Waiting to start',0)",
                (key, case_id, owner),
            )
            return cursor.rowcount == 1

    def job(self, key: str, owner: str) -> dict | None:
        with self.connect() as con:
            row = con.execute(
                "SELECT phase,message,cancelled FROM jobs WHERE key=? AND owner=?", (key, owner)
            ).fetchone()
        return dict(zip(("phase", "message", "cancelled"), row, strict=True)) if row else None

    def progress(self, key: str, phase: str, message: str):
        with self.connect() as con:
            con.execute(
                "UPDATE jobs SET phase=?,message=? WHERE key=? AND cancelled=0",
                (phase, message, key),
            )

    def cancel(self, key: str, owner: str):
        with self.connect() as con:
            con.execute(
                "UPDATE jobs SET cancelled=1,phase='cancelled',message='Cancelled; in-flight request may finish' WHERE key=? AND owner=?",
                (key, owner),
            )

    def recover(self):
        with self.connect() as con:
            con.execute(
                "UPDATE jobs SET phase='partial', message='Interrupted by restart; use Reassess to resume' WHERE phase NOT IN ('complete','partial','cancelled','failed')"
            )

    def cleanup(self, ephemeral_hours: int = 24):
        cutoff = (now() - timedelta(hours=ephemeral_hours)).isoformat()
        with self.connect() as con:
            con.execute(
                "UPDATE jobs SET cancelled=1,phase='cancelled',message='Expired' WHERE case_id IN (SELECT id FROM cases WHERE saved=0 AND updated<?)",
                (cutoff,),
            )
            con.execute(
                "UPDATE cases SET deleted=1,payload='{}' WHERE saved=0 AND updated<?", (cutoff,)
            )
            con.execute("DELETE FROM cache WHERE expires<?", (now().isoformat(),))

    def cache_get(self, key: str):
        with self.connect() as con:
            row = con.execute(
                "SELECT payload FROM cache WHERE key=? AND expires>?", (key, now().isoformat())
            ).fetchone()
        return json.loads(row[0]) if row else None

    def cache_put(self, key: str, value: dict, ttl_hours: int):
        with self.connect() as con:
            con.execute(
                "INSERT OR REPLACE INTO cache VALUES(?,?,?)",
                (key, json.dumps(value), (now() + timedelta(hours=ttl_hours)).isoformat()),
            )

    def clear_cache(self):
        with self.connect() as con:
            con.execute("DELETE FROM cache")
