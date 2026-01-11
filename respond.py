#!/usr/bin/env python3
"""
Respond to the most recent REVIEW with an explicit decision:
APPROVE / REJECT / DEFER

Usage:
  python3 respond.py APPROVE "reason text"
  python3 respond.py REJECT  "reason text"
  python3 respond.py DEFER   "reason text"
"""

import sys
import sqlite3
import datetime as dt

DB = "ledger.db"

def now_utc_iso():
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

def main():
    if len(sys.argv) < 3:
        print('Usage: python3 respond.py APPROVE|REJECT|DEFER "reason"')
        sys.exit(1)

    action = sys.argv[1].strip().upper()
    reason = " ".join(sys.argv[2:]).strip()

    if action not in {"APPROVE", "REJECT", "DEFER"}:
        print("Action must be APPROVE, REJECT, or DEFER")
        sys.exit(1)

    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row

    # Find most recent review
    row = conn.execute(
        "SELECT created_at, text FROM memories WHERE category='review' ORDER BY created_at DESC LIMIT 1"
    ).fetchone()

    if not row:
        print("No review found. Run review_decision.py first.")
        sys.exit(1)

    review_created = row["created_at"]
    review_text = row["text"]

    response_text = (
        f"RESPONSE | {action} | ReviewAt: {review_created} | "
        f"Reason: {reason} | Review: {review_text}"
    )

    # Save response
    conn.execute(
        "INSERT INTO memories (created_at, category, text) VALUES (?, ?, ?)",
        (now_utc_iso(), "response", response_text),
    )
    conn.commit()
    conn.close()

    print("\n🧾 RESPONSE RECORDED\n")
    print(f"Action: {action}")
    print(f"Reason: {reason}")
    print("✅ Saved as category [response] in the ledger.\n")

if __name__ == "__main__":
    main()

