#!/usr/bin/env python3
"""
Review a planned decision using institutional memory + counterfactual options.
Now auto-saves a review record into the ledger DB.

Usage:
  python3 review_decision.py "Type" "Decision description"
"""

import sys
import sqlite3
import datetime as dt
from collections import Counter

DB = "ledger.db"

SUGGESTIONS = {
    "Engagement Optimization": [
        ("Add friction", "Reduce virality speed: add share-confirm prompts for borderline content."),
        ("Improve safety capacity", "Increase moderation staffing/tools before amplification changes."),
        ("Limit reach by risk", "Cap distribution for unverified/trending content until reviewed."),
        ("Measure harm metrics", "Track misinformation rate + trust decline alongside engagement."),
        ("Stage rollout", "Run small pilot with strict harm thresholds before global launch.")
    ],
    "Cost Cutting": [
        ("Protect critical roles", "Do not cut safety/quality functions first; cut non-critical spend."),
        ("Automate safely", "If replacing humans, add QA gates and incident monitoring."),
        ("Slow down scope", "Reduce feature throughput instead of reducing support staff.")
    ],
}

def now_utc_iso():
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

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

def ensure_table(conn):
    # ledger.py already created the memories table, but this keeps it safe.
    conn.execute("""
    CREATE TABLE IF NOT EXISTS memories (
        id TEXT PRIMARY KEY,
        created_at TEXT NOT NULL,
        category TEXT NOT NULL,
        text TEXT NOT NULL
    )
    """)

def insert_memory(conn, category: str, text: str):
    conn.execute(
        "INSERT INTO memories (created_at, category, text) VALUES (?, ?, ?)",
        (now_utc_iso(), category, text),
    )
    return "saved"

def main():
    if len(sys.argv) != 3:
        print('Usage: python3 review_decision.py "Type" "Decision description"')
        sys.exit(1)

    target_type = sys.argv[1].strip()
    planned_desc = sys.argv[2].strip()

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

    harms = Counter()
    for did in decision_ids:
        outcomes = conn.execute(
            "SELECT text FROM memories WHERE category='outcome' AND text LIKE ?",
            (f"%{did}%",)
        ).fetchall()
        for o in outcomes:
            for h in parse_harms(o["text"]):
                harms[h] += 1

    total_harms = sum(harms.values())
    risk_level = "LOW"
    if total_harms >= 5:
        risk_level = "HIGH"
    elif total_harms >= 2:
        risk_level = "MEDIUM"

    # Build review text (human-readable and storable)
    lines = []
    lines.append("REVIEW | Planned decision")
    lines.append(f"Type: {target_type}")
    lines.append(f"Decision: {planned_desc}")
    lines.append(f"Past decisions of this type: {len(decision_ids)}")
    if harms:
        lines.append("Observed harms:")
        for h, c in harms.most_common():
            lines.append(f"- {h}: {c}")
    else:
        lines.append("Observed harms: (none tagged yet)")
    lines.append(f"Risk: {risk_level}")
    if target_type in SUGGESTIONS:
        lines.append("Counterfactuals:")
        for title, desc in SUGGESTIONS[target_type]:
            lines.append(f"- {title}: {desc}")
    else:
        lines.append("Counterfactuals: (none stored for this type yet)")

    review_text = " | ".join(lines)

    # Save review as a memory object
    review_id = insert_memory(conn, "review", review_text)
    conn.commit()
    conn.close()

    # Print output to terminal (same as before)
    print("\n🧠 DECISION REVIEW (Prototype)\n")
    print(f"Planned Type: {target_type}")
    print(f"Planned Decision: {planned_desc}\n")

    print("🚨 Institutional Memory Warnings:\n")
    if not decision_ids:
        print("No past decisions found for this type yet.\n")
    else:
        print(f"We have {len(decision_ids)} past decisions of this type.")
        if harms:
            print("Most common harms previously observed:")
            for h, c in harms.most_common():
                print(f" - {h}: {c} times")
            print()
        else:
            print("No tagged harms found yet for this type.\n")

    print("🔁 Safer Counterfactual Options:\n")
    if target_type in SUGGESTIONS:
        for i, (title, desc) in enumerate(SUGGESTIONS[target_type], 1):
            print(f"{i}) {title}")
            print(f"   - {desc}\n")
    else:
        print("No suggestions stored for this type yet.\n")

    print("📌 Quick Risk Summary:")
    print(f"- Risk Level (based on past tagged harms): {risk_level}")
    print("- This is not prediction. It’s memory + safer options.\n")

    print(f"✅ Saved review to ledger as memory id: {review_id}\n")

if __name__ == "__main__":
    main()

