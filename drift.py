#!/usr/bin/env python3
"""
Drift Detection (v0)

Usage:
  python3 drift.py
"""

import sqlite3

DB = "ledger.db"

def main():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row

    decisions = conn.execute(
        "SELECT created_at, text FROM memories WHERE category='decision'"
    ).fetchall()

    print("\n🚨 DRIFT REPORT\n")

    for d in decisions:
        decision_text = d["text"]
        decision_id = decision_text.split("|")[0].strip()

        outcomes = conn.execute(
            "SELECT COUNT(*) as c FROM memories WHERE category='outcome' AND text LIKE ?",
            (f"%{decision_id}%",)
        ).fetchone()["c"]

        if outcomes == 0:
            print(f"- DRIFT DETECTED: {decision_id}")
            print(f"  {decision_text}\n")

    conn.close()

if __name__ == "__main__":
    main()

