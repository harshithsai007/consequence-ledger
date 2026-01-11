#!/usr/bin/env python3
"""
Warnings (v0)

Usage:
  python3 warn.py "Engagement Optimization"
"""

import sys
import sqlite3
from collections import defaultdict, Counter

DB = "ledger.db"

def parse_type(decision_text: str):
    if "Type:" not in decision_text:
        return None
    return decision_text.split("Type:")[1].split("|")[0].strip()

def parse_decision_id(decision_text: str) -> str:
    return decision_text.split("|")[0].strip()

def parse_harms(outcome_text: str):
    if "Harm:" not in outcome_text:
        return []
    harms_part = outcome_text.split("Harm:")[1]
    if "|" in harms_part:
        harms_part = harms_part.split("|")[0]
    return [h.strip() for h in harms_part.split(",") if h.strip()]

def main():
    if len(sys.argv) != 2:
        print('Usage: python3 warn.py "Decision Type"')
        sys.exit(1)

    target_type = sys.argv[1].strip()

    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row

    decisions = conn.execute(
        "SELECT text FROM memories WHERE category='decision'"
    ).fetchall()

    decision_ids = []
    for d in decisions:
        t = parse_type(d["text"])
        if t == target_type:
            decision_ids.append(parse_decision_id(d["text"]))

    if not decision_ids:
        print(f"\n⚠️ No decisions found for type: {target_type}\n")
        return

    harms = Counter()
    examples = defaultdict(list)

    for did in decision_ids:
        outcomes = conn.execute(
            "SELECT text FROM memories WHERE category='outcome' AND text LIKE ?",
            (f"%{did}%",)
        ).fetchall()

        for o in outcomes:
            hs = parse_harms(o["text"])
            for h in hs:
                harms[h] += 1
                if len(examples[h]) < 2:
                    examples[h].append(did)

    conn.close()

    print(f"\n🚨 WARNING REPORT for Type: {target_type}\n")
    print(f"We have {len(decision_ids)} past decisions of this type.\n")

    if not harms:
        print("No tagged harms found yet. Add Harm: tags to outcomes.\n")
        return

    print("Most common harms seen after this type:\n")
    for h, c in harms.most_common():
        ex = ", ".join(examples[h]) if examples[h] else "N/A"
        print(f"- {h}: {c} times (examples: {ex})")

    print("\n✅ This is not prediction. This is institutional memory.\n")

if __name__ == "__main__":
    main()

