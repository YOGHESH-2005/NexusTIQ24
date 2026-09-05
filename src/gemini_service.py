import os
import json
from typing import Dict, Any, Optional, List
from src.models import (
    InvestigationReport, CustomerBaseline, RuleFinding, 
    ValidationResult, PriorityTransaction, EvidenceItem
)

class GeminiInvestigationService:
    """
    Gemini integration using google-genai SDK and gemini-3.5-flash-lite model.
    Generates structured, grounded investigation reports from deterministic evidence.
    Gracefully falls back to deterministic report generation if API key is missing or call fails.
    """
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY", "").strip()
        self.client = None
        if self.api_key:
            try:
                from google import genai
                self.client = genai.Client(api_key=self.api_key)
                # Inject the authenticated client into the RAG retrieval pipeline
                # so Gemini embeddings (gemini-embedding-001) are available.
                from src.retrieval import get_rule_retrieval_pipeline
                get_rule_retrieval_pipeline(gemini_client=self.client)
            except Exception as e:
                print(f"[GeminiService] SDK initialization warning: {e}")

    def is_available(self) -> bool:
        return self.client is not None and bool(self.api_key)

    def generate_report(
        self,
        validation: ValidationResult,
        baseline: CustomerBaseline,
        findings: List[RuleFinding],
        transactions: List[Any],
        retrieved_docs: List[Dict[str, str]]
    ) -> InvestigationReport:
        """
        Main entry point for report generation.
        Tries Gemini structured JSON generation first; falls back to deterministic synthesis on error.
        """
        # First check hard contradictions or edge cases that require immediate escalation
        if validation.contradictions:
            return self._build_contradiction_report(validation, baseline, transactions)

        if baseline.historical_count < 3:
            return self._build_insufficient_history_report(validation, baseline, transactions, findings)

        if not self.is_available():
            return self.build_deterministic_report(validation, baseline, findings, transactions, retrieved_docs, fallback_reason="GEMINI_API_KEY unconfigured or unavailable.")

        try:
            return self._call_gemini_structured(validation, baseline, findings, transactions, retrieved_docs)
        except Exception as e:
            print(f"[GeminiService] API call failed: {e}. Falling back to deterministic report.")
            return self.build_deterministic_report(validation, baseline, findings, transactions, retrieved_docs, fallback_reason=f"Gemini API fallback ({str(e)})")

    def _call_gemini_structured(
        self,
        validation: ValidationResult,
        baseline: CustomerBaseline,
        findings: List[RuleFinding],
        transactions: List[Any],
        retrieved_docs: List[Dict[str, str]]
    ) -> InvestigationReport:
        """
        Invokes gemini-3.5-flash-lite with strict prompt and structured JSON response schema.
        """
        from google.genai import types

        # Build prompt bundle with exact evidence
        prompt = self._construct_prompt(validation, baseline, findings, transactions, retrieved_docs)

        # Gemini 3.5 Flash Lite call with JSON mime type
        config = types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0.1,  # Low temperature for strict factual grounding
            system_instruction=(
                "You are TrustTrace AI, an evidence-grounded banking transaction risk investigation assistant. "
                "You inspect deterministic rule findings, customer baseline statistics, and transaction records. "
                "CRITICAL RULES:\n"
                "1. NEVER state 'fraud occurred', 'customer is fraudulent', or 'fraud confirmed'. Use 'Attention required', 'Risk signal detected', 'Requires investigator review'.\n"
                "2. Every cited finding MUST reference actual transaction IDs as [EVIDENCE: TXN-xxx] and rule codes as [RULE: R0x].\n"
                "3. Do NOT invent transactions, amounts, dates, or payees.\n"
                "4. If no rules triggered, set status to NO_ATTENTION_REQUIRED and explain consistency with baseline.\n"
                "5. Always emphasize that final judgement belongs to the human investigator."
            )
        )

        response = self.client.models.generate_content(
            model="gemini-3.5-flash-lite",
            contents=prompt,
            config=config
        )

        raw_json = response.text.strip()
        data = json.loads(raw_json)

        # Validate with Pydantic
        report = InvestigationReport(
            status=data.get("status", "ATTENTION_REQUIRED" if findings else "NO_ATTENTION_REQUIRED"),
            risk_level=data.get("risk_level", "HIGH" if findings else "LOW"),
            summary=data.get("summary", "Investigation complete."),
            rules_triggered=findings,
            customer_baseline=baseline,
            priority_transactions=[
                PriorityTransaction(**p) for p in data.get("priority_transactions", [])
            ] if data.get("priority_transactions") else self._rank_priorities(findings, transactions),
            unknowns=validation.missing_payees + validation.missing_timestamps,
            contradictions=[c["issue"] for c in validation.contradictions],
            recommended_investigator_action=data.get("recommended_investigator_action", "Review flagged transactions with customer."),
            human_judgement_required=True,
            retrieved_rule_docs=retrieved_docs
        )
        return report

    def _construct_prompt(self, validation, baseline, findings, transactions, retrieved_docs) -> str:
        txns_summary = []
        for t in transactions:
            t_dict = t.model_dump() if hasattr(t, "model_dump") else dict(t)
            txns_summary.append(f"- ID: {t_dict['transaction_id']} | Date: {t_dict['date']} {t_dict['time']} | Payee: {t_dict['payee']} | Amount: ₹{t_dict['amount']:,.2f} | Channel: {t_dict['channel']} | Hist: {t_dict['is_historical']}")

        rules_summary = []
        for f in findings:
            f_dict = f.model_dump() if hasattr(f, "model_dump") else dict(f)
            rules_summary.append(f"- Rule {f_dict['rule_id']} ({f_dict['rule_name']}): {f_dict['reason']} [TXNs: {', '.join(f_dict['transaction_ids'])}]")

        docs_summary = [d["content"] for d in retrieved_docs]

        return f"""
EVIDENCE BUNDLE FOR INVESTIGATION:

1. CUSTOMER BASELINE:
- Historical Count: {baseline.historical_count}
- Median Amount: ₹{baseline.median_amount:,.2f}
- Typical Amount Range: {baseline.typical_range_str}
- Active Hours Baseline: {baseline.active_hours_str}
- Common Channels: {', '.join(baseline.common_channels)}
- Common Payees: {', '.join(baseline.common_payees[:3])}
- Baseline Confidence: {baseline.baseline_confidence}

2. DETERMINISTIC RULES TRIGGERED ({len(findings)} rules):
{chr(10).join(rules_summary) if rules_summary else "NONE — No risk rule triggered."}

3. DATA HYGIENE & UNKNOWNS:
- Missing Payees: {validation.missing_payees}
- Missing Timestamps: {validation.missing_timestamps}
- Contradictions: {validation.contradictions}

4. TRANSACTIONS EVALUATED ({len(transactions)} total):
{chr(10).join(txns_summary)}

5. RETRIEVED KNOWLEDGE BASE GUIDANCE:
{chr(10).join(docs_summary[:2])}

Generate a JSON object matching this schema:
{{
  "status": "NO_ATTENTION_REQUIRED | ATTENTION_REQUIRED | INSUFFICIENT_EVIDENCE | INVESTIGATOR_REVIEW_REQUIRED",
  "risk_level": "LOW | MEDIUM | HIGH | UNKNOWN",
  "summary": "Clear executive narrative highlighting exact transaction IDs [EVIDENCE: TXN-xxx] and rule codes [RULE: R0x].",
  "recommended_investigator_action": "Clear step-by-step recommendation for the human fraud desk analyst.",
  "priority_transactions": [
    {{
      "rank": 1,
      "transaction_id": "TXN-xxx",
      "amount": 185000.0,
      "payee": "...",
      "date_time": "...",
      "reason": "Why this transaction should be inspected first [EVIDENCE: TXN-xxx]",
      "triggered_rules": ["R01", "R02"]
    }}
  ]
}}
"""

    def build_deterministic_report(
        self, validation, baseline, findings, transactions, retrieved_docs, fallback_reason: str = ""
    ) -> InvestigationReport:
        """
        Pure deterministic fallback generator. Guarantees the application NEVER crashes
        even if Gemini API is completely offline or fails schema parsing.
        """
        if not findings:
            return InvestigationReport(
                status="NO_ATTENTION_REQUIRED",
                risk_level="LOW",
                summary=(
                    "No configured risk rule was triggered. The evaluated transactions are consistent "
                    f"with the customer's established baseline median of ₹{baseline.median_amount:,.2f} "
                    f"and normal active hours ({baseline.active_hours_str})."
                ),
                rules_triggered=[],
                customer_baseline=baseline,
                priority_transactions=[],
                unknowns=validation.missing_payees + validation.missing_timestamps,
                contradictions=[],
                recommended_investigator_action="No further action required. Close investigation as routine activity.",
                human_judgement_required=True,
                retrieved_rule_docs=retrieved_docs
            )

        # Attention required case
        rules_text = ", ".join([f"[RULE: {f.rule_id}] {f.rule_name}" for f in findings])
        flagged_txn_ids = list(set([tid for f in findings for tid in f.transaction_ids]))
        evidence_citations = ", ".join([f"[EVIDENCE: {tid}]" for tid in flagged_txn_ids])

        summary = (
            f"Attention required for evaluated activity. The transaction risk engine triggered {len(findings)} risk rule(s): {rules_text}. "
            f"Flagged transactions ({evidence_citations}) break customer baseline metrics (Median: ₹{baseline.median_amount:,.2f}, Hours: {baseline.active_hours_str})."
        )
        if fallback_reason:
            summary += f" (Note: Report compiled via deterministic engine — {fallback_reason})"

        priorities = self._rank_priorities(findings, transactions)

        return InvestigationReport(
            status="ATTENTION_REQUIRED",
            risk_level="HIGH" if any(f.severity == "HIGH" for f in findings) else "MEDIUM",
            summary=summary,
            rules_triggered=findings,
            customer_baseline=baseline,
            priority_transactions=priorities,
            unknowns=validation.missing_payees + validation.missing_timestamps,
            contradictions=[],
            recommended_investigator_action="Inspect Priority 1 transaction details, verify payee creation timestamp, and contact customer to confirm transfer intent.",
            human_judgement_required=True,
            retrieved_rule_docs=retrieved_docs
        )

    def _build_contradiction_report(self, validation, baseline, transactions) -> InvestigationReport:
        issues = [c["issue"] for c in validation.contradictions]
        return InvestigationReport(
            status="INVESTIGATOR_REVIEW_REQUIRED",
            risk_level="HIGH",
            summary=f"DATA CONFLICT DETECTED: Transaction records contain contradictory information ({'; '.join(issues)}). System execution halted to prevent inaccurate risk scoring.",
            rules_triggered=[],
            customer_baseline=baseline,
            priority_transactions=[],
            unknowns=validation.missing_payees + validation.missing_timestamps,
            contradictions=issues,
            recommended_investigator_action="Escalate case to Level-2 Fraud Operations for core banking ledger reconciliation before proceeding with risk assessment.",
            human_judgement_required=True,
            retrieved_rule_docs=[]
        )

    def _build_insufficient_history_report(self, validation, baseline, transactions, findings) -> InvestigationReport:
        return InvestigationReport(
            status="INSUFFICIENT_EVIDENCE",
            risk_level="UNKNOWN",
            summary=f"INSUFFICIENT HISTORICAL DATA: Account contains only {baseline.historical_count} historical transaction(s). A reliable customer spending baseline cannot be established. Risk rules (R01–R04) are suppressed to prevent inaccurate scoring.",
            rules_triggered=[],
            customer_baseline=baseline,
            priority_transactions=[],
            unknowns=["Historical transaction baseline depth < 3 records"],
            contradictions=[],
            recommended_investigator_action="Request 6-month historical bank statements or KYC onboarding documents to establish an accurate spending profile before evaluating risk rules.",
            human_judgement_required=True,
            retrieved_rule_docs=[]
        )

    def _rank_priorities(self, findings: List[RuleFinding], transactions: List[Any]) -> List[PriorityTransaction]:
        txn_map = {t.transaction_id: t for t in transactions}
        txn_scores = {}

        for f in findings:
            weight = 3 if f.severity == "HIGH" else 1
            for tid in f.transaction_ids:
                if tid not in txn_scores:
                    txn_scores[tid] = {"score": 0, "rules": []}
                txn_scores[tid]["score"] += weight
                txn_scores[tid]["rules"].append(f.rule_id)

        sorted_tids = sorted(txn_scores.keys(), key=lambda tid: (txn_scores[tid]["score"], getattr(txn_map.get(tid), "amount", 0)), reverse=True)

        priorities = []
        for idx, tid in enumerate(sorted_tids, 1):
            t = txn_map.get(tid)
            amt = t.amount if t else 0.0
            payee = t.payee if t else "UNKNOWN"
            dt = f"{t.date} {t.time}".strip() if t else ""
            rules_list = txn_scores[tid]["rules"]
            
            priorities.append(PriorityTransaction(
                rank=idx,
                transaction_id=tid,
                amount=amt,
                payee=payee,
                date_time=dt,
                reason=f"Priority {idx}: Triggered {len(rules_list)} rule(s) ({', '.join(rules_list)}) with transaction amount ₹{amt:,.2f} [EVIDENCE: {tid}]",
                triggered_rules=rules_list
            ))

        return priorities

# Global service instance
gemini_service = GeminiInvestigationService()

def get_gemini_service() -> GeminiInvestigationService:
    return gemini_service
