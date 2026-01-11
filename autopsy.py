#!/usr/bin/env python3
import sys
import sqlite3

DB = "ledger.db"

def main():
    if len(sys.argv) != 2:
        print("Usage: python3 autopsy.py DECISION_ID")
        sys.exit(1)

    decision_id = sys.argv[1]
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row

    rows = conn.execute(
        "SELECT created_at, category, text FROM memories WHERE text LIKE ? ORDER BY created_at",
        (f"%{decision_id}%",)
    ).fetchall()

    conn.close()

    print(f"\n🧠 DECISION AUTOPSY: {decision_id}\n")
    if not rows:
        print("No records found.")
        return

    for r in rows:
        print(f"- {r['created_at']} [{r['category']}]")
        print(f"  {r['text']}\n")

if __name__ == "__main__":
    main()

