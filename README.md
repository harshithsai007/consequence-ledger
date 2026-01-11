# Consequence Ledger

Consequence Ledger is a Python-based prototype that helps organizations avoid repeating harmful decisions by preserving institutional memory.

Instead of predicting the future, it records **past decisions**, their **real outcomes**, **warnings**, **safer alternatives**, and **final leadership responses** in a tamper-evident ledger.

The system ensures that when a similar decision is proposed again, leaders are confronted with what actually happened last time — before acting.

---

## Problem This Solves

Organizations often fail not because they lack intelligent people, but because **institutional memory fades**.

Common failure pattern:
- A decision is made
- Short-term success hides long-term harm
- Time passes, people change
- The same decision is made again — with the same consequences

Consequence Ledger addresses this by creating a **durable, queryable memory of decisions and outcomes** that cannot be silently rewritten.

---

## What This Prototype Implements

This project is a working end-to-end system, not a mockup.

### Core Capabilities
- Structured decision recording with metadata
- Outcome tracking with harm categorization
- Pattern detection across decision types
- Warning generation based on historical evidence
- Counterfactual (safer alternative) suggestions
- Explicit leadership responses:
  - APPROVE
  - REJECT
  - DEFER
- Final decision anchoring using a tamper-evident hash chain
- Immutable audit trail for accountability

### Key Design Principle
This system **does not predict outcomes** and **does not tell leaders what to do**.

It provides **institutional memory**, not judgment.

---

## Example Workflow

```bash
# Propose a decision
python3 review_decision.py "Engagement Optimization" "Increase algorithmic amplification"

# View historical warnings
python3 warn.py "Engagement Optimization"

# See safer alternatives based on past failures
python3 counterfactual.py "Engagement Optimization"

# Record a leadership response
python3 respond.py REJECT "Risk too high due to past misinformation"

# Finalize and anchor the decision
python3 finalize.py REJECT "Repeated harm confirmed"

# Check current status
python3 status.py

consequence_ledger/
├── ledger.py              # Core database logic
├── ai_layer.py            # Memory retrieval & reasoning layer
├── review_decision.py     # Decision review pipeline
├── warn.py                # Historical warning generator
├── counterfactual.py      # Safer alternative suggestions
├── respond.py             # Leadership response recording
├── finalize.py            # Final decision anchoring
├── status.py              # Current decision state
├── patterns.py            # Pattern analysis
├── harm_report.py         # Harm aggregation reports
├── drift.py               # Change detection over time
├── demo_report.py         # End-to-end demo summary
└── README.md


