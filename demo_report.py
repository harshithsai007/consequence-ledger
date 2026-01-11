#!/usr/bin/env python3
"""
Demo Report (v0)
Prints a clean, pitch-ready report of:
- latest review
- all responses + FINAL
- anchor proof (latest_hash)
"""

import sqlite3
from pathlib import Path

DB = "ledger.db"
ANCHOR_FILE = "ANCHOR.txt"

def read_latest_hash():
    p = Path(ANCHOR_FILE)
    if not p.exists():
        return "(no anchor yet)"
    content = p.read_text(encoding="utf-8").strip()
    if not content:
        return "(no anchor yet)"
    for line in content.splitlines():
        if line.startswith("latest_hash="):
            return line.split("=", 1)[1].strip()
    return content.splitlines()[0].strip()

def main():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row

    review = conn.execute(
        "SELECT created_at, text FROM memories WHERE category='review' ORDER BY created_at DESC LIMIT 1"
    ).fetchone()

    if not review:
        print("No review found. Run review_decision.py first.")
        return

    review_at = review["created_at"]
    review_text = review["text"]

    responses = conn.execute(
        "SELECT created_at, text FROM memories WHERE category='response' AND text LIKE ? ORDER BY created_at ASC",
        (f"%ReviewAt: {review_at}%",)
    ).fetchall()

    conn.close()

    latest_hash = read_latest_hash()

    final = None
    for r in responses:
        if "FINAL: yes" in r["text"]:
            final = r

    print("\n" + "="*60)
    print("🧠 ORGANIZATIONAL CONSEQUENCE OS — DEMO REPORT")
    print("="*60 + "\n")

    print("1) Latest Review\n")
    print(f"- ReviewAt: {review_at}")
    print(f"- Review text:\n  {review_text}\n")

    print("2) Recorded Responses\n")
    if not responses:
        print("  (none)\n")
    else:
        for r in responses:
            tag = ""
            if final and r["created_at"] == final["created_at"]:
                tag = " ✅ FINAL"
            print(f"- {r['created_at']}{tag}")
            print(f"  {r['text']}\n")

    print("3) Official Status\n")
    if final:
        print("✅ FINAL decision recorded.\n")
    else:
        print("⚠️ No FINAL decision yet.\n")

    print("4) Tamper-evident Proof\n")
    print(f"- latest_hash (ANCHOR.txt): {latest_hash}")
    print("  (If anyone changes history, this hash chain breaks.)\n")

    print("5) What this prototype proves\n")
    print("- Institutional memory exists (not prediction).")
    print("- Warnings + alternatives are recorded.")
    print("- Leadership must respond (approve/reject/defer).")
    print("- FINAL decisions are anchored to a hash chain.\n")

    print("="*60 + "\n")

if __name__ == "__main__":
    main()

