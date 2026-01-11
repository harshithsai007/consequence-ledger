#!/usr/bin/env python3
"""
LOCAL AI (free) for your History Machine
----------------------------------------
No payment, no API. Works offline.

What it does:
- Reads your saved memories from the DB (memories table)
- Makes a simple summary
- Detects themes (by keywords)
- Proposes ONE decision + 3 next actions
- You approve, then we save the approved decision using ai_layer.py

Run:
  python3 local_ai.py review --limit 50
  python3 local_ai.py decide --goal "Become internship-ready by May 1 with 1.5 hours/day" --limit 50
"""

from __future__ import annotations
import argparse
import sqlite3
from collections import Counter
from typing import Dict, List, Tuple

DB_DEFAULT = "ledger.db"

THEMES: Dict[str, List[str]] = {
    "internship": ["internship", "resume", "linkedin", "project", "apply", "application", "recruiter", "interview"],
    "learning": ["learn", "study", "practice", "dsa", "python", "notes", "revision", "understand"],
    "consistency": ["daily", "consistent", "routine", "habit", "discipline", "schedule"],
    "health": ["sleep", "gym", "walk", "stress", "tired", "energy", "burnout"],
    "confidence": ["confidence", "fear", "scared", "doubt", "believe", "hope", "motivation"],
}

STOPWORDS = set(["the","a","an","and","or","but","to","of","in","on","for","with","is","are","was","were","i","my","it","that","this","we","you"])


def connect(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def get_memories(db_path: str, limit: int) -> List[Dict[str, str]]:
    conn = connect(db_path)
    try:
        # table created by ai_layer.py remember
        rows = conn.execute(
            "SELECT created_at, category, text FROM memories ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [{"created_at": r["created_at"], "category": r["category"], "text": r["text"]} for r in rows]
    finally:
        conn.close()


def tokenize(text: str) -> List[str]:
    clean = []
    for ch in text.lower():
        if ch.isalnum() or ch.isspace():
            clean.append(ch)
        else:
            clean.append(" ")
    words = [w for w in "".join(clean).split() if w not in STOPWORDS and len(w) > 2]
    return words


def detect_themes(memories: List[Dict[str, str]]) -> List[Tuple[str, int]]:
    scores = Counter()
    for m in memories:
        t = m["text"].lower()
        for theme, keys in THEMES.items():
            for k in keys:
                if k in t:
                    scores[theme] += 1
    return scores.most_common()


def top_words(memories: List[Dict[str, str]], n: int = 12) -> List[Tuple[str, int]]:
    c = Counter()
    for m in memories:
        c.update(tokenize(m["text"]))
    return c.most_common(n)


def review(memories: List[Dict[str, str]]) -> str:
    if not memories:
        return "No memories yet. Add one:\npython3 ai_layer.py remember --category belief --text \"...\""

    latest = memories[0]
    themes = detect_themes(memories)
    words = top_words(memories, 10)

    lines = []
    lines.append("LOCAL AI REVIEW (FREE / OFFLINE)")
    lines.append("")
    lines.append("1) Latest memory:")
    lines.append(f"- {latest['created_at']} [{latest['category']}] {latest['text']}")
    lines.append("")
    lines.append("2) Themes I notice:")
    if themes:
        for t, s in themes:
            lines.append(f"- {t}: {s}")
    else:
        lines.append("- (No strong themes yet — add more memories.)")
    lines.append("")
    lines.append("3) Words you repeat (signals what matters):")
    for w, c in words:
        lines.append(f"- {w}: {c}")
    lines.append("")
    lines.append("4) Simple next step:")
    lines.append("- Add 1 memory per day (1 sentence).")
    lines.append("- Every Sunday, run review + write 1 decision.")
    return "\n".join(lines)


def decide(memories: List[Dict[str, str]], goal: str) -> str:
    themes = detect_themes(memories)
    top_theme = themes[0][0] if themes else "consistency"

    # Tiny decision templates
    templates = {
        "internship": (
            "Decision: I will apply to 5 internships per week and ship 1 small project milestone every Sunday.",
            ["Update resume for 30 minutes today.", "Apply to 1 internship today.", "Write 1 project update memory tonight."]
        ),
        "learning": (
            "Decision: I will practice DSA for 45 minutes daily and explain one concept in my own words.",
            ["Pick 1 topic (arrays/strings) and do 2 problems.", "Write 5-line explanation memory.", "Review mistakes tomorrow."]
        ),
        "consistency": (
            "Decision: I will protect a daily 60-minute focus block and track it with one sentence each night.",
            ["Set a fixed time for the block.", "Do one focused task now (no phone).", "Record a memory after finishing."]
        ),
        "health": (
            "Decision: I will prioritize sleep and energy so I can learn faster and stay consistent.",
            ["Pick a bedtime.", "Walk 20 minutes.", "Record energy level in a memory."]
        ),
        "confidence": (
            "Decision: I will build confidence through small proof every day, not big promises.",
            ["Do one small task now.", "Record it as proof.", "Repeat tomorrow."]
        ),
    }

    decision, actions = templates.get(top_theme, templates["consistency"])

    lines = []
    lines.append("LOCAL AI DECISION PROPOSAL (FREE / OFFLINE)")
    lines.append("")
    lines.append(f"Goal: {goal}")
    lines.append("")
    lines.append(decision)
    lines.append("")
    lines.append("3 next actions (tiny):")
    for i, a in enumerate(actions, start=1):
        lines.append(f"{i}. {a}")
    lines.append("")
    lines.append("Approval question:")
    lines.append("Do you approve this decision? (yes/no)")
    return "\n".join(lines)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--db", default=DB_DEFAULT)
    sub = p.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("review")
    r.add_argument("--limit", type=int, default=50)

    d = sub.add_parser("decide")
    d.add_argument("--limit", type=int, default=50)
    d.add_argument("--goal", required=True)

    args = p.parse_args()

    memories = get_memories(args.db, args.limit)

    if args.cmd == "review":
        print(review(memories))
    elif args.cmd == "decide":
        print(decide(memories, args.goal))


if __name__ == "__main__":
    main()

