#!/usr/bin/env python3
"""
Finalize the most recent review with ONE official decision and anchor it
into a tamper-evident hash chain (ANCHOR_HISTORY.log + ANCHOR.txt).

Usage:
  python3 finalize.py APPROVE "final reason"
  python3 finalize.py REJECT  "final reason"
  python3 finalize.py DEFER   "final reason"
"""

import sys
import sqlite3
import datetime as dt
import hashlib
from pathlib import Path

DB = "ledger.db"
ANCHOR_FILE = "ANCHOR.txt"
HISTORY_FILE = "ANCHOR_HISTORY.log"


def now_utc_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def sha256(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def read_prev_anchor() -> str:
    """
    Supports both formats:
      - simple hash-only ANCHOR.txt
      - key=value format with 'latest_hash=...'
    """
    p = Path(ANCHOR_FILE)
    if not p.exists():
        return "GENESIS"

    content = p.read_text(encoding="utf-8").strip()
    if not content:
        return "GENESIS"

    # If file contains key=value lines (from ledger.py), parse latest_hash
    for line in content.splitlines():
        line = line.strip()
        if line.startswith("latest_hash="):
            return line.split("=", 1)[1].strip()

    # Otherwise treat the whole file as the previous hash
    return content.splitlines()[0].strip()


def append_history_line(record_line: str) -> None:
    Path(HISTORY_FILE).write_text(
        (Path(HISTORY_FILE).read_text(encoding="utf-8") if Path(HISTORY_FILE).exists() else "")
        + record_line
        + "\n",
        encoding="utf-8",
    )


def write_anchor_file(new_hash: str, note: str) -> None:
    """
    Keep the same ANCHOR.txt style as your ledger.py (key=value).
    """
    Path(ANCHOR_FILE).write_text(
        f"latest_hash={new_hash}\n"
        f"timestamp={now_utc_iso()}\n"
        f"note={note}\n",
        encoding="utf-8",
    )


def anchor_record(record_line: str, note: str) -> str:
    """
    Hash-chains record_line using previous anchor hash.
    new_hash = sha256(prev + "\\n" + record_line)
    Then appends record_line to history and writes ANCHOR.txt with new_hash.
    """
    prev = read_prev_anchor()
    new_hash = sha256(prev + "\n" + record_line)

    append_history_line(f"{record_line} | {new_hash} | {note}")
    write_anchor_file(new_hash, note)

    return new_hash


def main():
    if len(sys.argv) < 3:
        print('Usage: python3 finalize.py APPROVE|REJECT|DEFER "final reason"')
        sys.exit(1)

    action = sys.argv[1].strip().upper()
    reason = " ".join(sys.argv[2:]).strip()

    if action not in {"APPROVE", "REJECT", "DEFER"}:
        print("Action must be APPROVE, REJECT, or DEFER")
        sys.exit(1)

    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row

    review = conn.execute(
        "SELECT created_at, text FROM memories WHERE category='review' ORDER BY created_at DESC LIMIT 1"
    ).fetchone()

    if not review:
        conn.close()
        print("No review found. Run review_decision.py first.")
        sys.exit(1)

    review_at = review["created_at"]
    review_text = review["text"]

    # Save FINAL response to DB
    response_text = (
        f"RESPONSE | {action} | FINAL: yes | ReviewAt: {review_at} | "
        f"Reason: {reason} | Review: {review_text}"
    )

    conn.execute(
        "INSERT INTO memories (created_at, category, text) VALUES (?, ?, ?)",
        (now_utc_iso(), "response", response_text),
    )
    conn.commit()
    conn.close()

    # Anchor FINAL decision (tamper-evident)
    record_line = f"{now_utc_iso()} | FINAL | {action} | ReviewAt: {review_at} | Reason: {reason}"
    note = f"finalize {action} {review_at}"
    new_anchor = anchor_record(record_line, note)

    print("\n✅ FINALIZED\n")
    print(f"Final Action: {action}")
    print(f"Final Reason: {reason}")
    print(f"🔒 Anchored hash: {new_anchor}\n")


if __name__ == "__main__":
    main()

