# TrustTrace AI — Master Investigator Guidance

## Core Philosophy
TrustTrace AI is an evidence-grounded investigation assistant. It NEVER declares fraud or guilt. The final judgement always belongs to the human investigator.

## Standard Operating Procedure for Risk Desk Analysts

### 1. Initial Triage
- First inspect the **Executive Finding**: `NO ATTENTION REQUIRED`, `ATTENTION REQUIRED`, `INSUFFICIENT EVIDENCE`, or `INVESTIGATOR REVIEW REQUIRED`.
- If `NO ATTENTION REQUIRED`, verify that no risk rule was triggered and that transactions fall within established baseline metrics. Close case with standard documentation.

### 2. High-Priority Case Handling
- Review the **Investigator Priority List**. Start with Priority 1 transactions.
- Examine the exact **Evidence Reference** (`[EVIDENCE: TXN-xxx]`) and triggered **Rule Code** (`[RULE: R0x]`).
- Compare current transaction metrics (amount, time, payee, channel) against the customer baseline table.

### 3. Handling Edge Cases & Data Conflicts
- **Missing Information**: If payees or timestamps are missing, inspect whether auxiliary logs exist before drawing conclusions.
- **Contradictions**: If transaction amounts or dates differ across records (e.g. ₹50,000 vs ₹5,000), escalate immediately to Level 2 Fraud Ops for record reconciliation.
- **Insufficient History**: For accounts with $<3$ transactions, do not assume a normal spending baseline. Request additional bank statements or KYC activity logs.

### 4. Communication & Escalation Language
- Use approved terminology: "Risk signal detected", "Unusual pattern observed", "Attention required".
- Prohibited terminology: "Fraud committed", "Guilty customer", "Confirmed scammer".
