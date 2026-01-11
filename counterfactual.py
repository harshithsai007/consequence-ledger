#!/usr/bin/env python3
"""
Counterfactual suggestions (v0) - offline, rule-based.

Usage:
  python3 counterfactual.py "Engagement Optimization"
"""

import sys

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

def main():
    if len(sys.argv) != 2:
        print('Usage: python3 counterfactual.py "Decision Type"')
        return

    t = sys.argv[1].strip()
    print(f"\n🔁 COUNTERFACTUAL OPTIONS for Type: {t}\n")

    if t not in SUGGESTIONS:
        print("No template suggestions for this type yet.")
        print("Add your own suggestions into SUGGESTIONS dict.\n")
        return

    for i, (title, desc) in enumerate(SUGGESTIONS[t], 1):
        print(f"{i}) {title}")
        print(f"   - {desc}\n")

    print("✅ This is not AI prediction. It is safer decision options based on known failure modes.\n")

if __name__ == "__main__":
    main()

