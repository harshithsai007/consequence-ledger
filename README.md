# 🧠 Consequence Ledger

Consequence Ledger is a simple prototype that helps organizations **remember what happened before** when they made important decisions.

It does NOT predict the future.
It does NOT tell leaders what to do.

It simply says:
👉 “Last time you did something like this, here is what happened.”

---

## 👶 Explain Like I’m 10 Years Old

Imagine a company is like a school.

Sometimes teachers make rules.
Later, those rules cause problems.
But after some time, everyone forgets.

So the same bad rule gets made again.

This project is like a **memory book** for companies.

It writes down:
- What decision was made
- What bad things happened later
- Whether someone warned about it
- What safer choices existed
- What final choice the leader made

And once written…
🧱 **It cannot be secretly changed.**

---

## 🧠 What Problem Does This Solve?

Big organizations often fail not because they lack smart people,
but because they **forget past consequences**.

This leads to:
- Repeated mistakes
- Blame shifting
- No accountability
- “We didn’t know” excuses

Consequence Ledger creates **institutional memory**.

---

## 🚫 What This Is NOT

- ❌ Not an AI that predicts outcomes
- ❌ Not a decision-making bot
- ❌ Not surveillance
- ❌ Not a compliance tool (yet)

This is a **memory + accountability system**.

---

## ✅ What This Prototype Can Do

✔ Record decisions  
✔ Record real-world outcomes  
✔ Detect repeated harm patterns  
✔ Warn before similar decisions  
✔ Suggest safer alternatives  
✔ Force leadership responses:
- APPROVE
- REJECT
- DEFER  
✔ Final decisions are **tamper-evident** using hash anchoring  

---

## 🧱 Why This Is Different

Most tools ask:
> “What do you think will happen?”

This tool asks:
> “What actually happened last time?”

That difference matters.

---

## 📁 Project Structure

```text
consequence_ledger/
├── ledger.py            # Core ledger storage (SQLite)
├── ai_layer.py          # Institutional memory (not prediction)
├── review_decision.py   # Reviews new decisions using past data
├── warn.py              # Shows warnings based on history
├── counterfactual.py    # Safer alternative options
├── respond.py           # APPROVE / REJECT / DEFER
├── finalize.py          # Locks final decisions with hash
├── status.py            # Shows current decision state
├── patterns.py          # Detects repeated harm
├── harm_report.py       # Harm summary by decision type
├── ANCHOR.txt           # Latest hash anchor (ignored in git)
├── ANCHOR_HISTORY.log   # Hash chain history (ignored in git)
└── README.md

