TRACK_ID=PS6

# TrustTrace AI — Transaction Risk Investigation Assistant

> **Project Tagline:** Evidence-grounded transaction risk investigation for banking fraud desks.  
> **Track:** PS06 — Banking - Transaction Risk Investigation Assistant  
> **Hackathon:** CareerTiQ NexusTIQ 24

---

## 1. What the Project Does

**TrustTrace AI** is a professional, judge-ready investigation assistant built specifically for banking fraud desks. It transforms raw customer transaction histories spanning multi-month periods into structured, evidence-grounded investigation reports.

Unlike generic LLM chatbots that make independent decisions or hallucinate risk claims, TrustTrace AI separates **deterministic Python risk evaluation** from **LLM narrative synthesis**. Python algorithms evaluate objective data, calculate customer-specific baseline statistics, and execute deterministic risk rules. The Gemini LLM (`gemini-3.5-flash-lite`) interprets the objective findings, organizes evidence citations, ranks investigator priorities, and produces human-readable investigation reports.

The system **NEVER** claims "fraud occurred" or "customer is fraudulent." It flags risk signals, highlights baseline deviations, cites exact transactions, surfaces data conflicts, and escalates uncertain cases to human investigators.

---

## 2. Problem Being Solved (PS06)

Fraud desk analysts face high transaction volume and must quickly determine whether an account requires immediate review. Existing automated systems either emit noisy binary alerts or rely on opaque AI models that hallucinate false claims.

TrustTrace AI solves PS06 by addressing the core questions:
1. *"Does anything need attention at all?"* (Explicitly reports `NO ATTENTION REQUIRED` when activity fits normal patterns).
2. *"If something needs attention, which transactions caused it and why?"*
3. *"How does current activity compare to the customer's own historical baseline?"*
4. *"Which specific risk rule was triggered?"*
5. *"What should the investigator inspect first?"*
6. *"Are there missing data points or contradictory ledger records?"*

---

## 3. Core Architecture & Principle

```
+-------------------------------------------------------------------+
|                        UPLOAD TRANSACTIONS                        |
|                    (CSV / JSON or Sample Case)                    |
+---------------------------------+---------------------------------+
                                  |
                                  v
+-------------------------------------------------------------------+
|                         INPUT VALIDATION                          |
|         (Detect missing payees/amounts, duplicates,               |
|              and contradictory ledger records)                    |
+---------------------------------+---------------------------------+
                                  |
                                  v
+-------------------------------------------------------------------+
|                     CUSTOMER BASELINE ENGINE                      |
|      (Computes historical median, typical amount range,           |
|         active operating hours, and top channels)                 |
+---------------------------------+---------------------------------+
                                  |
                                  v
+-------------------------------------------------------------------+
|                    DETERMINISTIC RISK ENGINE                      |
|       (Executes R01 Large Transfer, R02 New Payee Burst,          |
|       R03 Odd-Hours, and R04 Behaviour Deviation rules)           |
+---------------------------------+---------------------------------+
                                  |
                                  v
+-------------------------------------------------------------------+
|                   LOCAL RAG RETRIEVAL PIPELINE                    |
|       (Retrieves relevant rule guidance docs using local          |
|      numpy vector cosine similarity / BM25 term matching)         |
+---------------------------------+---------------------------------+
                                  |
                                  v
+-------------------------------------------------------------------+
|                    GEMINI REASONING ENGINE                        |
|     (gemini-3.5-flash-lite generates grounded structured JSON;    |
|      gracefully falls back to Python synthesis if offline)        |
+---------------------------------+---------------------------------+
                                  |
                                  v
+-------------------------------------------------------------------+
|               EVIDENCE-GROUNDED DASHBOARD FRONTEND                |
|      (Traceable citations, investigator priority ranking,         |
|             modal inspection drawers, and escalation)             |
+-------------------------------------------------------------------+
```

---

## 4. Deterministic Risk Rules

TrustTrace AI implements four core, objective risk rules:

| Rule Code | Rule Title | Evaluation Criteria | Output Evidence |
|---|---|---|---|
| **R01** | **Unusually Large Transfer** | Current amount $\ge 5.0\times$ baseline median or exceeds 95th percentile with ratio $\ge 3.0\times$. | Transaction ID, Amount, Median, Ratio multiplier (e.g. 13.03x). |
| **R02** | **New Payee Burst** | Rapid payments ($\ge 2$ txns or cumulative $> ₹50,000$) to a newly appearing payee not in history within 24h. | Payee name, Transaction list, Payout total. |
| **R03** | **Odd-Hours Activity** | Transaction time falls outside customer's established active hours (e.g. 08:00–22:00 vs 03:17 AM). | Transaction timestamp, Active hours range, Time delta. |
| **R04** | **Behaviour Deviation** | Simultaneous multi-factor deviation (channel switch + amount spike + new payee). | Combined profile shift summary. |

---

## 5. Synthetic Datasets & Demo Scenarios

The repository includes 9 realistic synthetic CSV scenarios in `data/scenarios/`:

1. `normal_customer.csv`: Clean routine activity. Baseline median ~₹4,500, active hours 08:00–18:00. Result: **NO ATTENTION REQUIRED**.
2. `large_transfer.csv`: Historical median ₹14,200 vs current transfer ₹185,000 (13.03x). Result: **R01 Triggered**.
3. `new_payee_burst.csv`: 3 rapid payments (₹75k, ₹65k, ₹45k) to new payee "QuickMoney Services". Result: **R02 Triggered**.
4. `odd_hours.csv`: Transfer of ₹120,000 executed at 03:17 AM. Result: **R03 Triggered**.
5. `behaviour_deviation.csv`: ₹150,000 wire transfer at 03:00 AM via IMPS. Result: **R04 Triggered**.
6. `multiple_rules.csv`: High-value odd-hours burst to new payee. Result: **Multiple Rules & Priority Ranked**.
7. `incomplete_data.csv`: Missing payees and timestamps. Result: **Unknowns surfaced gracefully**.
8. `contradictory_data.csv`: Primary amount ₹50,000 vs secondary record ₹5,000. Result: **ESCALATE TO HUMAN**.
9. `insufficient_history.csv`: Only 1 historical transaction. Result: **INSUFFICIENT EVIDENCE (Low Confidence)**.

---

## 6. RAG / Local Retrieval Pipeline

- Knowledge base markdown documents stored in `data/rules/`: `risk_rules.json`, `rule_R01.md`, `rule_R02.md`, `rule_R03.md`, `rule_R04.md`, `investigator_guidance.md`.
- Vector embeddings fetched via `gemini-embedding-001` with an offline BM25/keyword fallback.
- Zero external vector databases (no Pinecone, Weaviate, or OpenAI). All search is executed locally via Python/numpy.

---

## 7. Gemini API Integration & Structured Output

- Reads API key strictly from environment variable: `GEMINI_API_KEY`.
- Uses official Google GenAI SDK (`google-genai`) with model target `gemini-3.5-flash-lite`.
- Enforces strict JSON output schema (`response_mime_type="application/json"`) validated via Pydantic.
- **Fail-Safe Fallback**: If `GEMINI_API_KEY` is missing or Gemini API fails, system automatically switches to deterministic Python report generation without crashing.

---

## 8. Installation & Environment Setup

### Environment Requirements
- Python 3.11 (Compatible with Python 3.10–3.13)
- Windows, macOS, or Linux

### Installation
```bash
pip install -r requirements.txt
```

### Setting the Gemini API Key

Gemini API key is required for the full GenAI/RAG experience. A deterministic fallback is available for offline or degraded operation.

```bash
# Windows PowerShell:
$env:GEMINI_API_KEY="your-gemini-api-key-here"

# Linux / macOS:
export GEMINI_API_KEY="your-gemini-api-key-here"
```

---

## 9. How to Run

Run the single entry point command:
```bash
python app.py
```

Open your browser and navigate to:
```
http://localhost:8000
```
- No second terminal needed.
- No node/npm build step needed at judge runtime.

---

## 10. Automated Testing

Run the test suite:
```bash
python -m pytest -v tests/
```

Test coverage includes:
- Baseline statistics & median/percentile math (`test_baseline.py`).
- R01, R02, R03, R04 deterministic rule triggering (`test_risk_engine.py`).
- Edge-case data hygiene, duplicates, and contradictions (`test_validation.py`).
- REST API health & scenario endpoints (`test_api.py`).

---

## 11. Edge-Case & Safety Engineering

| Edge Case | System Behavior |
|---|---|
| **Missing Payee / Timestamp** | Marked as `UNKNOWN` without fabricating values. |
| **Contradictory Data** | Triggers `INVESTIGATOR_REVIEW_REQUIRED` and surfaces ledger conflict. |
| **Insufficient History (<3 txns)** | Sets baseline confidence to `LOW` and returns `INSUFFICIENT_EVIDENCE`. |
| **Normal Routine Customer** | Explicitly displays `NO ATTENTION REQUIRED` with green badge. |
| **Gemini API Down / Key Missing** | Seamless deterministic fallback report generated; system never crashes. |

---

## 12. Human-in-the-Loop Protocol

TrustTrace AI enforces strict wording boundaries:
- Prohibited: "Fraud committed", "Customer is fraudulent", "Guilty user".
- Approved: "Attention required", "Risk signal detected", "Investigator review required".
- Banner: *"TrustTrace AI identifies and explains risk signals. Final judgement remains with the human investigator."*

---

## 13. Repository Structure

```
c:/Users/YOGHESH/Documents/Projects/NexusTIQ24/
├── app.py                     # Primary entry point (starts server on port 8000)
├── requirements.txt           # Minimal dependencies
├── README.md                  # Comprehensive README (First line EXACTLY TRACK_ID=PS6)
├── .gitignore                 # Standard git exclusions
│
├── src/
│   ├── models.py              # Pydantic data schemas
│   ├── validators.py          # Data hygiene & contradiction validator
│   ├── baseline.py            # Baseline calculation engine
│   ├── risk_engine.py         # Deterministic rule engine (R01-R04)
│   ├── retrieval.py           # Local RAG vector search engine
│   ├── gemini_service.py      # Gemini API client & fallback report builder
│   ├── report_generator.py    # Main investigation report compiler
│   └── api.py                 # FastAPI REST router
│
├── data/
│   ├── rules/                 # Markdown knowledge base rule docs
│   └── scenarios/             # 9 Precomputed CSV scenarios
│
├── static/
│   ├── index.html             # Investigation dashboard UI
│   ├── style.css              # Custom styling
│   └── app.js                 # Interactive frontend logic
│
├── tests/
│   ├── test_baseline.py
│   ├── test_risk_engine.py
│   ├── test_validation.py
│   └── test_api.py
│
└── scripts/
    └── generate_data.py       # Data generation utility
```

---

## 14. Demo Video Link

https://www.loom.com/share/b64562a740de46db984d83352610aa98

---

## 15. License & Credits

Built for **CareerTiQ NexusTIQ 24 Hackathon** — Track **PS06 (Banking - Transaction Risk Investigation Assistant)**. Developed with Python 3.11, FastAPI, Pydantic, NumPy, Pandas, and Google Gemini 3.5 Flash Lite.
