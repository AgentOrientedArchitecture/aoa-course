"""SQLite-backed case state and an atomic review/release boundary.

This is a local durable-object teaching implementation, not a Cloudflare SDK
or a claim of exactly-once effects in external systems. SQLite is authoritative;
JSONL remains a regenerable projection for the existing course audit tools.
"""
from __future__ import annotations

import hashlib
import json
import os
import sqlite3
from pathlib import Path


class CaseConflict(ValueError):
    pass


def result_digest(plan_digest: str, outputs: dict) -> str:
    payload = {"plan_digest": plan_digest, "outputs": outputs}
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()[:16]


class CaseStore:
    def __init__(self, path: Path):
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS cases (id TEXT PRIMARY KEY, body TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS events (sequence INTEGER PRIMARY KEY AUTOINCREMENT, case_id TEXT NOT NULL, body TEXT NOT NULL);
                CREATE INDEX IF NOT EXISTS case_events ON events(case_id, sequence);
            """)

    def connect(self):
        db = sqlite3.connect(self.path, timeout=20)
        db.execute("PRAGMA journal_mode=WAL")
        db.execute("PRAGMA synchronous=FULL")
        return db

    def record(self, record: dict, case: dict | None = None):
        self.record_many([record], case)

    def record_many(self, records: list[dict], case: dict | None = None):
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            for record in records:
                db.execute("INSERT INTO events(case_id,body) VALUES(?,?)", (record["trace_id"], json.dumps(record)))
            if case:
                db.execute("INSERT INTO cases VALUES(?,?) ON CONFLICT(id) DO UPDATE SET body=excluded.body", (case["trace_id"], json.dumps(case)))

    def cases(self):
        with self.connect() as db:
            return [json.loads(row[0]) for row in db.execute("SELECT body FROM cases ORDER BY rowid DESC")]

    def get(self, case_id: str):
        with self.connect() as db:
            row = db.execute("SELECT body FROM cases WHERE id=?", (case_id,)).fetchone()
        return json.loads(row[0]) if row else None

    def events(self, case_id: str):
        with self.connect() as db:
            rows = db.execute("SELECT sequence,body FROM events WHERE case_id=? ORDER BY sequence", (case_id,)).fetchall()
        return [{**json.loads(body), "event_sequence": sequence} for sequence, body in rows]

    def project(self, case_id: str, directory: Path):
        directory.mkdir(parents=True, exist_ok=True)
        target = directory / f"{case_id}.jsonl"
        temporary = directory / f".{case_id}.jsonl.tmp"
        with temporary.open("w") as stream:
            for event in self.events(case_id):
                stream.write(json.dumps(event) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, target)

    def review(self, case_id: str, decision: str, digest: str, notes: str, actor: str, timestamp: str):
        if decision not in {"approve", "reject"} or not notes.strip():
            raise CaseConflict("approve/reject and non-empty reviewer notes are required")
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT body FROM cases WHERE id=?", (case_id,)).fetchone()
            if not row:
                raise CaseConflict("unknown saved case")
            case = json.loads(row[0])
            previous = case.get("review")
            if previous:
                if (previous["decision"], previous["result_digest"], previous["review_notes"], previous["actor_id"]) == (decision, digest, notes, actor):
                    return case, []
                raise CaseConflict("this result already has a different recorded review")
            if case["status"] != "draft-held":
                raise CaseConflict("case is not holding a draft")
            if digest != case["result_digest"] or case.get("draft_outputs") is None:
                raise CaseConflict("review must match the held result digest")
            if result_digest(case["plan_digest"], case["draft_outputs"]) != digest:
                raise CaseConflict("saved draft no longer matches its digest")
            case["review"] = {"decision": decision, "actor_id": actor, "reviewed_at": timestamp, "result_digest": digest, "review_notes": notes}
            case["status"] = "released" if decision == "approve" else "quarantined"
            case["outputs"] = case["draft_outputs"] if decision == "approve" else {"status": "quarantined", "result_digest": digest}
            common = {"trace_id": case_id, "ts": timestamp, "workflow": case["workflow"], "plan_digest": case["plan_digest"], "result_digest": digest}
            events = [
                {**common, "step": "result-review", **case["review"]},
                {**common, "step": "result-release" if decision == "approve" else "result-quarantine", "actor_id": actor, "outputs": case["outputs"]},
                {**common, "step": "finish", "outputs": case["outputs"]},
            ]
            for event in events:
                db.execute("INSERT INTO events(case_id,body) VALUES(?,?)", (case_id, json.dumps(event)))
            db.execute("UPDATE cases SET body=? WHERE id=?", (json.dumps(case), case_id))
            return case, events
