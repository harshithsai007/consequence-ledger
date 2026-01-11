#!/usr/bin/env python3
"""
History Machine (Consequence Ledger) — Mac + Email publishing
-------------------------------------------------------------
What we're building (simple):
- A system that creates "history" for organizational decisions.
- That history is tamper-evident (hash chain).
- Every day it writes a fingerprint (anchor) and emails it externally.

Files created:
- ledger.db (SQLite DB)
- ANCHOR.txt (current fingerprint)
- ANCHOR_HISTORY.log (append-only fingerprint log)

Main command you will run daily (or via cron):
  python3 ledger.py daily-publish --label "EOD"
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import sqlite3
import sys
import textwrap
import uuid
from email.message import EmailMessage
import smtplib
from typing import Any, Dict, Optional


DB_DEFAULT = "ledger.db"
ANCHOR_FILE_DEFAULT = "ANCHOR.txt"
ANCHOR_HISTORY_DEFAULT = "ANCHOR_HISTORY.log"
GENESIS_HASH = "GENESIS"


# -----------------------------
# Utilities
# -----------------------------

def utc_now_iso() -> str:
    return dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def today_utc() -> str:
    return dt.datetime.utcnow().date().isoformat()


def new_uuid() -> str:
    return str(uuid.uuid4())


def pretty_wrap(s: str, width: int = 88, indent: str = "") -> str:
    return "\n".join(textwrap.wrap(s, width=width, subsequent_indent=indent, initial_indent=indent))


def canonical_json(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_hex(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def connect(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def env(name: str, default: Optional[str] = None) -> Optional[str]:
    v = os.environ.get(name)
    return v if v is not None and v.strip() != "" else default


# -----------------------------
# DB Schema
# -----------------------------

SCHEMA_SQL = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS decisions (
    decision_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    decision_text TEXT NOT NULL,
    context TEXT,
    decision_maker_role TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS rationales (
    rationale_id TEXT PRIMARY KEY,
    decision_id TEXT NOT NULL,
    stated_reason TEXT NOT NULL,
    assumptions_json TEXT,
    expected_metrics_json TEXT,
    added_at TEXT NOT NULL,
    FOREIGN KEY(decision_id) REFERENCES decisions(decision_id)
);

CREATE TABLE IF NOT EXISTS outcomes (
    outcome_id TEXT PRIMARY KEY,
    decision_id TEXT NOT NULL,
    signal_type TEXT NOT NULL,
    signal_description TEXT NOT NULL,
    evidence_json TEXT,
    observed_at TEXT NOT NULL,
    confidence INTEGER NOT NULL CHECK(confidence BETWEEN 0 AND 100),
    added_at TEXT NOT NULL,
    FOREIGN KEY(decision_id) REFERENCES decisions(decision_id)
);

CREATE TABLE IF NOT EXISTS annotations (
    annotation_id TEXT PRIMARY KEY,
    decision_id TEXT NOT NULL,
    annotation_text TEXT NOT NULL,
    author_role TEXT,
    added_at TEXT NOT NULL,
    FOREIGN KEY(decision_id) REFERENCES decisions(decision_id)
);

-- Hash-chained, append-only history events (tamper-evident)
CREATE TABLE IF NOT EXISTS ledger_events (
    event_id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL,
    event_type TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    prev_hash TEXT NOT NULL,
    event_hash TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_ledger_events_created_at ON ledger_events(created_at);
CREATE UNIQUE INDEX IF NOT EXISTS idx_ledger_events_event_hash ON ledger_events(event_hash);
"""


def init_db(db_path: str) -> None:
    conn = connect(db_path)
    try:
        conn.executescript(SCHEMA_SQL)
        conn.commit()
    finally:
        conn.close()


# -----------------------------
# Anchors (external fingerprint)
# -----------------------------

def write_anchor_files(
    *,
    anchor_file: str,
    anchor_history: str,
    latest_hash: str,
    note: str,
    created_at: str,
) -> None:
    # Snapshot (current fingerprint)
    with open(anchor_file, "w", encoding="utf-8") as f:
        f.write(f"latest_hash={latest_hash}\n")
        f.write(f"timestamp={created_at}\n")
        f.write(f"note={note}\n")

    # Append-only external history
    with open(anchor_history, "a", encoding="utf-8") as f:
        f.write(f"{created_at} | {latest_hash} | {note}\n")


def read_anchor_file(anchor_file: str) -> Dict[str, str]:
    if not os.path.exists(anchor_file):
        raise ValueError(f"Anchor file not found: {anchor_file}")
    data: Dict[str, str] = {}
    with open(anchor_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if "=" in line:
                k, v = line.split("=", 1)
                data[k.strip()] = v.strip()
    return data


# -----------------------------
# Hash chain (tamper-evident history)
# -----------------------------

def get_last_event_hash(conn: sqlite3.Connection) -> str:
    row = conn.execute("SELECT event_hash FROM ledger_events ORDER BY created_at DESC LIMIT 1").fetchone()
    return row["event_hash"] if row else GENESIS_HASH


def append_event(
    conn: sqlite3.Connection,
    *,
    event_type: str,
    entity_type: str,
    entity_id: str,
    created_at: str,
    payload: Dict[str, Any],
) -> str:
    prev_hash = get_last_event_hash(conn)
    payload_json = canonical_json(payload)
    material = "|".join([prev_hash, created_at, event_type, entity_type, entity_id, payload_json])
    event_hash = sha256_hex(material)

    conn.execute(
        """
        INSERT INTO ledger_events (event_id, created_at, event_type, entity_type, entity_id, payload_json, prev_hash, event_hash)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (new_uuid(), created_at, event_type, entity_type, entity_id, payload_json, prev_hash, event_hash),
    )
    return event_hash


def verify_chain(db_path: str) -> str:
    conn = connect(db_path)
    try:
        events = conn.execute("SELECT * FROM ledger_events ORDER BY created_at ASC").fetchall()
        if not events:
            return GENESIS_HASH

        prev = GENESIS_HASH
        for idx, e in enumerate(events, start=1):
            if e["prev_hash"] != prev:
                raise ValueError(f"Chain broken at event #{idx}: prev_hash mismatch.")
            material = "|".join([e["prev_hash"], e["created_at"], e["event_type"], e["entity_type"], e["entity_id"], e["payload_json"]])
            expected = sha256_hex(material)
            if expected != e["event_hash"]:
                raise ValueError(f"Tamper detected at event #{idx}: hash mismatch.")
            prev = e["event_hash"]

        return prev
    finally:
        conn.close()


def verify_anchor(db_path: str, anchor_file: str) -> None:
    db_last = verify_chain(db_path)
    anchored = read_anchor_file(anchor_file).get("latest_hash")
    if not anchored:
        raise ValueError("Anchor file missing latest_hash")
    if db_last != anchored:
        raise ValueError(
            "ANCHOR MISMATCH\n"
            f"DB last hash: {db_last}\n"
            f"Anchor hash : {anchored}\n"
        )


# -----------------------------
# Email publish (external proof)
# -----------------------------

def send_email(subject: str, body: str) -> None:
    host = env("LEDGER_SMTP_HOST")
    user = env("LEDGER_SMTP_USER")
    pwd = env("LEDGER_SMTP_PASS")
    mail_from = env("LEDGER_EMAIL_FROM")
    mail_to = env("LEDGER_EMAIL_TO")
    port = int(env("LEDGER_SMTP_PORT", "587"))

    if not (host and user and pwd and mail_from and mail_to):
        raise ValueError(
            "Missing SMTP environment variables. You must set:\n"
            "LEDGER_SMTP_HOST, LEDGER_SMTP_PORT, LEDGER_SMTP_USER, LEDGER_SMTP_PASS, LEDGER_EMAIL_FROM, LEDGER_EMAIL_TO"
        )

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = mail_from
    msg["To"] = mail_to
    msg.set_content(body)

    with smtplib.SMTP(host, port, timeout=15) as s:
        s.starttls()
        s.login(user, pwd)
        s.send_message(msg)


# -----------------------------
# Daily publish (the "unavoidable ritual")
# -----------------------------

def daily_publish(db_path: str, anchor_file: str, anchor_history: str, label: str) -> None:
    # 1) Verify DB chain first
    last_hash = verify_chain(db_path)

    # 2) Write daily anchor files (external fingerprint)
    ts = utc_now_iso()
    note = f"DAILY_ANCHOR {today_utc()} {label}".strip()
    write_anchor_files(
        anchor_file=anchor_file,
        anchor_history=anchor_history,
        latest_hash=last_hash,
        note=note,
        created_at=ts,
    )

    # 3) Verify DB hash matches anchor file (local proof)
    verify_anchor(db_path, anchor_file)

    # 4) Email the anchor (external proof)
    payload = {
        "type": "daily_anchor",
        "date_utc": today_utc(),
        "label": label,
        "timestamp": ts,
        "latest_hash": last_hash,
        "anchor_file": anchor_file,
        "anchor_history": anchor_history,
    }

    subject = f"History Anchor {payload['date_utc']} {payload['latest_hash'][:12]}"
    body = canonical_json(payload)

    send_email(subject, body)

    print("✅ Daily publish complete.")
    print(f"   Anchor hash: {last_hash}")
    print(f"   Wrote: {anchor_file}, {anchor_history}")
    print("   Sent email.")


# -----------------------------
# CLI
# -----------------------------

def cmd_init(args: argparse.Namespace) -> None:
    init_db(args.db)
    print("✅ Initialized DB.")
    print("Next: configure SMTP env vars, then run daily-publish.")
    # Optional first publish to create initial files (will require SMTP configured)
    if args.publish_now:
        daily_publish(args.db, args.anchor_file, args.anchor_history, label="init")


def cmd_daily_publish(args: argparse.Namespace) -> None:
    daily_publish(args.db, args.anchor_file, args.anchor_history, label=args.label)


def cmd_verify_anchor(args: argparse.Namespace) -> None:
    verify_anchor(args.db, args.anchor_file)
    print("✅ Verified: DB fingerprint == ANCHOR.txt")


def cmd_verify_chain(args: argparse.Namespace) -> None:
    last = verify_chain(args.db)
    print(f"✅ Chain OK. Last hash: {last}")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="History Machine (Mac + Email): daily anchor + email external proof.")
    p.add_argument("--db", default=DB_DEFAULT)
    p.add_argument("--anchor-file", default=ANCHOR_FILE_DEFAULT)
    p.add_argument("--anchor-history", default=ANCHOR_HISTORY_DEFAULT)

    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("init", help="Initialize DB")
    s.add_argument("--publish-now", action="store_true", help="Also run first daily-publish (requires SMTP configured)")
    s.set_defaults(func=cmd_init)

    s = sub.add_parser("daily-publish", help="Write daily anchor + send email proof")
    s.add_argument("--label", default="EOD")
    s.set_defaults(func=cmd_daily_publish)

    s = sub.add_parser("verify-chain", help="Verify DB chain integrity")
    s.set_defaults(func=cmd_verify_chain)

    s = sub.add_parser("verify-anchor", help="Verify DB matches ANCHOR.txt")
    s.set_defaults(func=cmd_verify_anchor)

    return p


def main(argv: Optional[list[str]] = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    args = build_parser().parse_args(argv)

    if args.cmd != "init" and not os.path.exists(args.db):
        print(f"DB not found: {args.db}. Run: python3 ledger.py init", file=sys.stderr)
        return 2

    try:
        args.func(args)
        return 0
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

