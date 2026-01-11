#!/usr/bin/env python3
"""
Status viewer (v0)

Shows the most recent review and its responses.
Also selects the FINAL response if one exists, else shows latest response.

Usage:
  python3 status.py
"""

import sqlite3

DB = "ledger.db"

def main():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row

    review = conn.execute(
        "SELECT created_at, text FROM memories WHERE category='review' ORDER BY created_at DESC LIMIT 1"
    ).fetchone()

    if not review:
        print("No review found.")
        return

    review_at = review["created_at"]
    review_text = review["text"]

    responses = conn.execute(
        "SELECT created_at, text FROM memories WHERE category='response' AND text LIKE ? ORDER BY created_at ASC",
        (f"%ReviewAt: {review_at}%",)
    ).fetchall()

    conn.close()

    print("\n📌 CURRENT STATUS (latest review)\n")
    print(f"ReviewAt: {review_at}\n")
    print("Review (summary):")
    print(review_text[:250] + ("..." if len(review_text) > 250 else ""))
    print("\nResponses:\n")

    if not responses:
        print("(no responses yet)\n")
        return

    final = None
    latest = responses[-1]

    for r in responses:
        if "FINAL:" in r["text"]:
            final = r
            break

    for r in responses:
        marker = ""
        if final and r["created_at"] == final["created_at"]:
            marker = " ✅ FINAL"
        elif r["created_at"] == latest["created_at"]:
            marker = " (latest)"
        print(f"- {r['created_at']}{marker}")
        print(f"  {r['text'][:180]}{'...' if len(r['text'])>180 else ''}\n")

    if final:
        print("✅ Official status is FINAL.")
    else:
        print("⚠️ No FINAL response yet. Latest response shown as current behavior.\n")

if __name__ == "__main__":
    main()

