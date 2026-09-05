import pytest
import pandas as pd
from src.validators import validate_and_normalize_data

def test_missing_and_unknown_fields():
    data = [
        {"transaction_id": "TXN-01", "date": "2026-08-01", "time": "10:00:00", "payee": "", "amount": 1000.0, "is_historical": True},
        {"transaction_id": "TXN-02", "date": "2026-08-02", "time": "", "payee": "Vendor", "amount": None, "is_historical": False},
    ]
    df = pd.DataFrame(data)
    transactions, res = validate_and_normalize_data(df)

    assert len(transactions) == 2
    assert "TXN-01" in res.missing_payees
    assert "TXN-02" in res.missing_timestamps
    assert "TXN-02" in res.missing_amounts
    assert transactions[0].payee == "UNKNOWN_PAYEE"

def test_duplicate_transaction_ids():
    data = [
        {"transaction_id": "TXN-DUP", "date": "2026-08-01", "time": "10:00:00", "payee": "A", "amount": 100.0, "is_historical": True},
        {"transaction_id": "TXN-DUP", "date": "2026-08-02", "time": "11:00:00", "payee": "B", "amount": 200.0, "is_historical": False},
    ]
    df = pd.DataFrame(data)
    transactions, res = validate_and_normalize_data(df)

    assert "TXN-DUP" in res.duplicate_ids

def test_contradiction_detection():
    data = [
        {"transaction_id": "TXN-CONFLICT", "date": "2026-08-01", "time": "10:00:00", "payee": "Vendor", "amount": 50000.0, "secondary_amount_record": 5000.0, "is_historical": False}
    ]
    df = pd.DataFrame(data)
    transactions, res = validate_and_normalize_data(df)

    assert len(res.contradictions) == 1
    assert res.contradictions[0]["transaction_id"] == "TXN-CONFLICT"
    assert res.is_valid is False
