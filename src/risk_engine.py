from typing import List, Tuple
from src.models import Transaction, CustomerBaseline, RuleFinding, EvidenceItem

def run_risk_engine(
    transactions: List[Transaction], 
    baseline: CustomerBaseline
) -> List[RuleFinding]:
    """
    Executes modular deterministic risk rules (R01, R02, R03, R04).
    Produces objective evidence bundles and traceable citations.
    Does NOT use AI or heuristics that invent data.
    """
    # Guard: Suppress rule scoring if historical count < 3 (insufficient baseline)
    if baseline.historical_count < 3:
        return []

    findings: List[RuleFinding] = []
    
    # Filter current evaluation transactions (is_historical == False)
    current_txns = [t for t in transactions if not t.is_historical]
    if not current_txns:
        # If no explicit current transaction marked, evaluate the latest transaction
        current_txns = transactions[-1:] if transactions else []

    historical_payees = set(t.payee.lower() for t in transactions if t.is_historical and t.payee and t.payee != "UNKNOWN_PAYEE")

    # -------------------------------------------------------------
    # RULE R01 — UNUSUALLY LARGE TRANSFER
    # -------------------------------------------------------------
    r01_flagged_txns = []
    r01_evidence = []
    max_ratio = 0.0

    for t in current_txns:
        if t.amount <= 0:
            continue
        
        # Compare to baseline median or mean
        ref_amt = baseline.median_amount if baseline.median_amount > 0 else (baseline.mean_amount if baseline.mean_amount > 0 else 10000.0)
        ratio = round(t.amount / ref_amt, 2)

        # Trigger if amount >= 5.0x median or > 95th percentile with ratio >= 3.0x
        if ratio >= 5.0 or (t.amount > baseline.percentile_95_amount and ratio >= 3.0):
            r01_flagged_txns.append(t.transaction_id)
            if ratio > max_ratio:
                max_ratio = ratio
            r01_evidence.append(EvidenceItem(
                field="amount",
                value=f"Current: ₹{t.amount:,.2f} | Baseline Median: ₹{ref_amt:,.2f} (Ratio: {ratio}x)",
                source=f"transaction {t.transaction_id}"
            ))

    if r01_flagged_txns:
        findings.append(RuleFinding(
            rule_id="R01",
            rule_name="Unusually Large Transfer",
            severity="HIGH",
            transaction_ids=r01_flagged_txns,
            reason=f"Detected transfer amount significantly exceeding customer baseline median of ₹{baseline.median_amount:,.2f} (Highest ratio: {max_ratio}x).",
            ratio=max_ratio,
            evidence=r01_evidence
        ))

    # -------------------------------------------------------------
    # RULE R02 — NEW PAYEE BURST
    # -------------------------------------------------------------
    new_payee_map = {}
    for t in current_txns:
        p_clean = t.payee.strip()
        if p_clean and p_clean.lower() not in historical_payees and p_clean != "UNKNOWN_PAYEE":
            if p_clean not in new_payee_map:
                new_payee_map[p_clean] = []
            new_payee_map[p_clean].append(t)

    r02_flagged_txns = []
    r02_evidence = []
    burst_payees = []

    for payee, txns in new_payee_map.items():
        total_amt = sum(t.amount for t in txns)
        # Trigger if multiple rapid txns to new payee (>=2) OR single large payment to new payee (> ₹50,000)
        if len(txns) >= 2 or total_amt >= 50000.0:
            burst_payees.append(payee)
            for t in txns:
                r02_flagged_txns.append(t.transaction_id)
                r02_evidence.append(EvidenceItem(
                    field="new_payee_burst",
                    value=f"Payee '{payee}' | Amount: ₹{t.amount:,.2f} | Time: {t.time}",
                    source=f"transaction {t.transaction_id}"
                ))

    if r02_flagged_txns:
        findings.append(RuleFinding(
            rule_id="R02",
            rule_name="New Payee Burst",
            severity="HIGH",
            transaction_ids=list(set(r02_flagged_txns)),
            reason=f"Detected rapid transaction burst to newly observed payee(s): {', '.join(burst_payees)}.",
            evidence=r02_evidence
        ))

    # -------------------------------------------------------------
    # RULE R03 — ODD-HOURS ACTIVITY
    # -------------------------------------------------------------
    r03_flagged_txns = []
    r03_evidence = []

    for t in current_txns:
        if not t.time or ":" not in t.time:
            continue
        try:
            h = int(t.time.split(":")[0])
            # Check if hour is outside normal baseline hours (e.g. < start or > end)
            if (h < baseline.active_hours_start or h > baseline.active_hours_end) and t.amount >= 5000.0:
                r03_flagged_txns.append(t.transaction_id)
                r03_evidence.append(EvidenceItem(
                    field="odd_hours",
                    value=f"Transaction Time: {t.time} (Normal Range: {baseline.active_hours_str}) | Amount: ₹{t.amount:,.2f}",
                    source=f"transaction {t.transaction_id}"
                ))
        except ValueError:
            pass

    if r03_flagged_txns:
        findings.append(RuleFinding(
            rule_id="R03",
            rule_name="Odd-Hours Activity",
            severity="MEDIUM",
            transaction_ids=r03_flagged_txns,
            reason=f"Detected activity occurring outside customer's established active window ({baseline.active_hours_str}).",
            evidence=r03_evidence
        ))

    # -------------------------------------------------------------
    # RULE R04 — CUSTOMER BEHAVIOUR DEVIATION
    # -------------------------------------------------------------
    r04_flagged_txns = []
    r04_evidence = []

    for t in current_txns:
        deviations = []
        # Channel deviation
        if baseline.common_channels and t.channel not in baseline.common_channels and t.channel != "UNKNOWN":
            deviations.append(f"Unusual Channel '{t.channel}' (Normal: {', '.join(baseline.common_channels)})")
        
        # Amount deviation
        if t.amount > baseline.max_amount * 2.0 and baseline.max_amount > 0:
            deviations.append(f"Amount ₹{t.amount:,.2f} exceeds historical peak ₹{baseline.max_amount:,.2f}")

        # New payee deviation
        if t.payee and t.payee.lower() not in historical_payees and t.payee != "UNKNOWN_PAYEE":
            deviations.append(f"First-time Payee '{t.payee}'")

        # Multi-factor trigger (at least 2 deviation signals on same txn)
        if len(deviations) >= 2:
            r04_flagged_txns.append(t.transaction_id)
            r04_evidence.append(EvidenceItem(
                field="behaviour_deviation",
                value=" | ".join(deviations),
                source=f"transaction {t.transaction_id}"
            ))

    if r04_flagged_txns:
        findings.append(RuleFinding(
            rule_id="R04",
            rule_name="Customer Behaviour Deviation",
            severity="HIGH",
            transaction_ids=r04_flagged_txns,
            reason="Detected multi-factor pattern shift breaking historical amount, channel, and payee profile.",
            evidence=r04_evidence
        ))

    return findings
