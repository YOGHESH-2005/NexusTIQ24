from typing import List, Tuple
import pandas as pd
from src.models import Transaction, ValidationResult

def validate_and_normalize_data(df: pd.DataFrame) -> Tuple[List[Transaction], ValidationResult]:
    """
    Validates CSV/JSON input dataframe, handles missing fields gracefully without inventing data,
    detects duplicates, surfaces contradictions, and returns normalized Transactions and ValidationResult.
    """
    res = ValidationResult(total_rows=len(df))
    transactions: List[Transaction] = []
    seen_ids = set()

    for idx, row in df.iterrows():
        # 1. Transaction ID check
        raw_id = str(row.get("transaction_id", f"TXN-GEN-{idx+1}")).strip()
        if not raw_id or raw_id == "nan":
            raw_id = f"TXN-GEN-{idx+1}"

        if raw_id in seen_ids:
            res.duplicate_ids.append(raw_id)
            res.warnings.append(f"Duplicate transaction ID detected: {raw_id}")
        seen_ids.add(raw_id)

        # 2. Date & Time
        date_str = str(row.get("date", "")).strip()
        if date_str == "nan":
            date_str = ""

        time_str = str(row.get("time", "")).strip()
        if time_str == "nan":
            time_str = ""
        
        if not time_str:
            res.missing_timestamps.append(raw_id)

        # 3. Payee
        payee_str = str(row.get("payee", "")).strip()
        if not payee_str or payee_str.lower() in ["nan", "none", "null", ""]:
            payee_str = "UNKNOWN_PAYEE"
            res.missing_payees.append(raw_id)

        # 4. Amount
        raw_amt = row.get("amount", None)
        amt = 0.0
        if pd.isna(raw_amt) or raw_amt is None or str(raw_amt).strip() == "":
            res.missing_amounts.append(raw_id)
            res.warnings.append(f"Missing amount in transaction {raw_id}")
        else:
            try:
                amt = float(raw_amt)
            except ValueError:
                res.missing_amounts.append(raw_id)
                res.warnings.append(f"Invalid numeric amount '{raw_amt}' in transaction {raw_id}")

        # 5. Channel
        channel_str = str(row.get("channel", "UNKNOWN")).strip()
        if channel_str.lower() in ["nan", "none", ""]:
            channel_str = "UNKNOWN"

        # 6. Historical flag
        is_hist = bool(row.get("is_historical", True))

        # 7. Contradiction check (e.g. secondary_amount_record)
        sec_amt = row.get("secondary_amount_record", None)
        secondary_amt_val = None
        if not pd.isna(sec_amt) and sec_amt is not None and str(sec_amt).strip() != "":
            try:
                secondary_amt_val = float(sec_amt)
                if abs(secondary_amt_val - amt) > 0.01:
                    res.contradictions.append({
                        "transaction_id": raw_id,
                        "primary_amount": amt,
                        "secondary_amount": secondary_amt_val,
                        "issue": f"Primary amount (₹{amt:,.2f}) conflicts with secondary ledger record (₹{secondary_amt_val:,.2f})"
                    })
            except ValueError:
                pass

        txn = Transaction(
            transaction_id=raw_id,
            date=date_str,
            time=time_str,
            description=str(row.get("description", "")),
            payee=payee_str,
            amount=amt,
            channel=channel_str,
            is_historical=is_hist,
            secondary_amount_record=secondary_amt_val
        )

        if is_hist:
            res.historical_rows += 1
        else:
            res.current_rows += 1

        transactions.append(txn)

    if res.duplicate_ids or res.missing_amounts or res.contradictions:
        res.is_valid = len(res.contradictions) == 0  # Invalid for execution if hard contradiction exists

    return transactions, res
