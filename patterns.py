#!/usr/bin/env python3
"""
Pattern Memory (v0)

Shows decision types and how often harm followed.
"""

import sqlite3
from collections import defaultdict

DB = "ledger.db"

def main():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row

    decisions = conn.execute(
        "SELECT text FROM memories WHERE category='decision'"
    ).fetchall()

    patterns = defaultdict(lambda: {"decisions": 0, "outcomes": 0})

    for d in decisions:
        text = d["text"]
        if "Type:" not in text:
            continue

        type_part = text.split("Type:")[1].split("|")[0].strip()
        decision_id = text.split("|")[0].strip()

        patterns[type_part]["decisions"] += 1

        outcome_count = conn.execute(
            "SELECT COUNT(*) as c FROM memories WHERE category='outcome' AND text LIKE ?",
            (f"%{decision_id}%",)
        ).fetchone()["c"]

        if outcome_count > 0:
            patterns[type_part]["outcomes"] += 1

    conn.close()

    print("\n📊 DECISION PATTERN REPORT\n")
    for t, v in patterns.items():
        print(f"- {t}: {v['decisions']} decisions, {v['outcomes']} with recorded outcomes")

if __name__ == "__main__":
    main()

