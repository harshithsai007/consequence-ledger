#!/usr/bin/env python3
"""
Harm Report (v1)

Counts harms per Decision Type, deduplicated by Outcome ID (O-XXXX).
"""

import sqlite3
from collections import defaultdict, Counter

DB = "ledger.db"

def parse_type(decision_text: str):
    if "Type:" not in decision_text:
        return None
    return decision_text.split("Type:")[1].split("|")[0].strip()

def parse_decision_id(decision_text: str) -> str:
    return decision_text.split("|")[0].strip()

def parse_outcome_id(outcome_text: str):
    first = outcome_text.split("|")[0].strip()
    if first.startswith("O-"):
        return first
    return None

def parse_harms(outcome_text: str):
    if "Harm:" not in outcome_text:
        return []
    harms_part = outcome_text.split("Harm:")[1]
    if "|" in harms_part:
        harms_part = harms_part.split("|")[0]
    return [h.strip() for h in harms_part.split(",") if h.strip()]

def main():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row

    decisions = conn.execute(
        "SELECT text FROM memories WHERE category='decision'"
    ).fetchall()

    type_to_decision_ids = defaultdict(list)
    for d in decisions:
        t = parse_type(d["text"])
        if not t:
            continue
        did = parse_decision_id(d["text"])
        type_to_decision_ids[t].append(did)

    print("\n🧾 HARM REPORT (by Decision Type, deduped)\n")

    for t, decision_ids in type_to_decision_ids.items():
        harm_counter = Counter()
        seen_outcome_ids = set()

        for did in decision_ids:
            outcomes = conn.execute(
                "SELECT text FROM memories WHERE category='outcome' AND text LIKE ?",
                (f"%{did}%",)
            ).fetchall()

            for o in outcomes:
                oid = parse_outcome_id(o["text"])
                if oid and oid in seen_outcome_ids:
                    continue
                if oid:
                    seen_outcome_ids.add(oid)

                for h in parse_harms(o["text"]):
                    harm_counter[h] += 1

        print(f"- {t}:")
        if not harm_counter:
            print("  (no tagged harms yet)\n")
            continue
        for harm, count in harm_counter.most_common():
            print(f"  • {harm}: {count}")
        print()

    conn.close()

if __name__ == "__main__":
    main()

