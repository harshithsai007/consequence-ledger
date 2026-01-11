#!/usr/bin/env python3
"""
AI Layer for your History Machine
---------------------------------
What this adds:
1) 'memories' table: plain sentences from you (timestamped)
2) memory.add events: appended into the SAME hash chain (ledger_events)
3) anchors updated after each write (ANCHOR.txt + ANCHOR_HISTORY.log)
4) AI review + AI decision proposal (human approves)

Safety design:
- AI never executes actions.
- AI only proposes.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import sqlite3
import sys
import uuid
from typing import Any, Dict, List, Optional

from openai import OpenAI  # official SDK :contentReference[oaicite:2]{index=2}


DB_DEFAULT = "ledger.db"
ANCHOR_FILE_DEFAULT = "ANCHOR.txt"
ANCHOR_HISTORY_DEFAULT = "ANCHOR_HISTORY.log"
GENESIS_HASH = "GENESIS"

# ---------- small utilities ----------

def utc_now_iso() -> str:
    # timezone-aware UTC (avoids your earlier warning)
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

def canonical_json(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))

def sha256_hex(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

def new_uuid() -> str:
    return str(uuid.uuid4())

def connect(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def write_anchor_files(anchor_file: str, anchor_history: str, latest_hash: str, note: str, created_at: str) -> None:
    with open(anchor_file, "w", encoding="utf-8") as f:
        f.write(f"latest_hash={latest_hash}\n")
        f.write(f"timestamp={created_at}\n")
        f.write(f"note={note}\n")
    with open(anchor_history, "a", encoding="utf-8") as f:
        f.write(f"{created_at} | {latest_hash} | {note}\n")

# ---------- ensure table exists ----------

MEMORY_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS memories (
  memory_id TEXT PRIMARY KEY,
  created_at TEXT NOT NULL,
  category TEXT NOT NULL,
  text TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_memories_created_at ON memories(created_at);
"""

def ensure_memories_table(conn: sqlite3.Connection) -> None:
    conn.executescript(MEMORY_SCHEMA_SQL)

# ---------- hash chain helpers (re-use your ledger_events) ----------

def get_last_event_hash(conn: sqlite3.Connection) -> str:
    row = conn.execute("SELECT event_hash FROM ledger_events ORDER BY created_at DESC LIMIT 1").fetchone()
    return row["event_hash"] if row else GENESIS_HASH

def append_event(conn: sqlite3.Connection, *, event_type: str, entity_type: str, entity_id: str,
                 created_at: str, payload: Dict[str, Any]) -> str:
    prev_hash = get_last_event_hash(conn)
    payload_json = canonical_json(payload)
    material = "|".join([prev_hash, created_at, event_type, entity_type, entity_id, payload_json])
    event_hash = sha256_hex(material)

    conn.execute(
        """
        INSERT INTO ledger_events (event_id, created_at, event_type, entity_type, entity_id,
                                  payload_json, prev_hash, event_hash)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (new_uuid(), created_at, event_type, entity_type, entity_id, payload_json, prev_hash, event_hash),
    )
    return event_hash

def verify_chain(conn: sqlite3.Connection) -> str:
    events = conn.execute("SELECT * FROM ledger_events ORDER BY created_at ASC").fetchall()
    if not events:
        return GENESIS_HASH
    prev = GENESIS_HASH
    for i, e in enumerate(events, start=1):
        if e["prev_hash"] != prev:
            raise ValueError(f"Chain broken at event #{i}: prev_hash mismatch.")
        material = "|".join([e["prev_hash"], e["created_at"], e["event_type"], e["entity_type"], e["entity_id"], e["payload_json"]])
        expected = sha256_hex(material)
        if expected != e["event_hash"]:
            raise ValueError(f"Tamper detected at event #{i}: hash mismatch.")
        prev = e["event_hash"]
    return prev

# ---------- core features ----------

def remember(db_path: str, anchor_file: str, anchor_history: str, category: str, text: str) -> str:
    created_at = utc_now_iso()
    memory_id = new_uuid()

    conn = connect(db_path)
    try:
        ensure_memories_table(conn)

        conn.execute(
            "INSERT INTO memories (memory_id, created_at, category, text) VALUES (?, ?, ?, ?)",
            (memory_id, created_at, category, text),
        )

        latest_hash = append_event(
            conn,
            event_type="memory.add",
            entity_type="memory",
            entity_id=memory_id,
            created_at=created_at,
            payload={"memory_id": memory_id, "created_at": created_at, "category": category, "text": text},
        )

        conn.commit()
    finally:
        conn.close()

    write_anchor_files(anchor_file, anchor_history, latest_hash, f"memory.add {category} {memory_id}", created_at)
    return memory_id

def get_recent_memories(db_path: str, limit: int) -> List[Dict[str, str]]:
    conn = connect(db_path)
    try:
        ensure_memories_table(conn)
        rows = conn.execute(
            "SELECT created_at, category, text FROM memories ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [{"created_at": r["created_at"], "category": r["category"], "text": r["text"]} for r in rows]
    finally:
        conn.close()

# ---------- AI functions (Responses API) ----------

def ai_review(memories: List[Dict[str, str]]) -> str:
    """
    Uses Responses API: recommended primitive for new apps. :contentReference[oaicite:3]{index=3}
    """
    client = OpenAI()
    prompt = {
        "task": "Summarize and extract patterns from my memories for my future self.",
        "style": "simple English, short bullets",
        "output": {
            "summary": "What happened / what I believed",
            "patterns": "repeating themes, risks, strengths",
            "next_week_plan": "3 actions max",
            "one_sentence_identity": "who I am becoming"
        },
        "memories": memories
    }

    resp = client.responses.create(
        model="gpt-5.2",  # pick any available model in your account
        input=canonical_json(prompt),
    )
    return resp.output_text

def ai_decision_proposal(memories: List[Dict[str, str]], goal: str) -> str:
    client = OpenAI()
    prompt = {
        "task": "Propose a decision for me. I will approve/reject. Do NOT assume you can execute anything.",
        "goal": goal,
        "rules": [
            "Make exactly 1 decision proposal",
            "Include rationale and risks",
            "Give 3 next actions (tiny steps)",
            "Ask me 1 yes/no approval question at the end"
        ],
        "memories": memories
    }
    resp = client.responses.create(
        model="gpt-5.2",
        input=canonical_json(prompt),
    )
    return resp.output_text

# ---------- CLI ----------

def main(argv: Optional[List[str]] = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    p = argparse.ArgumentParser()
    p.add_argument("--db", default=DB_DEFAULT)
    p.add_argument("--anchor-file", default=ANCHOR_FILE_DEFAULT)
    p.add_argument("--anchor-history", default=ANCHOR_HISTORY_DEFAULT)

    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("remember", help="Save a memory (tamper-evident + anchored)")
    s.add_argument("--category", default="belief")
    s.add_argument("--text", required=True)

    s = sub.add_parser("recent", help="Show recent memories")
    s.add_argument("--limit", type=int, default=10)

    s = sub.add_parser("ai-review", help="AI summarizes your recent memories")
    s.add_argument("--limit", type=int, default=25)

    s = sub.add_parser("ai-decide", help="AI proposes one decision (you approve)")
    s.add_argument("--limit", type=int, default=25)
    s.add_argument("--goal", required=True)

    args = p.parse_args(argv)

    if args.cmd == "remember":
        mid = remember(args.db, args.anchor_file, args.anchor_history, args.category, args.text)
        print(f"✅ Saved memory: {mid}")
        return 0

    if args.cmd == "recent":
        items = get_recent_memories(args.db, args.limit)
        for m in reversed(items):
            print(f"- {m['created_at']} [{m['category']}] {m['text']}")
        return 0

    if args.cmd == "ai-review":
        items = get_recent_memories(args.db, args.limit)
        print(ai_review(items))
        return 0

    if args.cmd == "ai-decide":
        items = get_recent_memories(args.db, args.limit)
        print(ai_decision_proposal(items, args.goal))
        return 0

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

