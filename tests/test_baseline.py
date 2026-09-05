import pytest
from src.models import Transaction
from src.baseline import calculate_customer_baseline

def test_baseline_calculation():
    txns = [
        Transaction(transaction_id="TXN-01", date="2026-08-01", time="10:00:00", amount=2000.0, payee="A", channel="UPI", is_historical=True),
        Transaction(transaction_id="TXN-02", date="2026-08-02", time="14:00:00", amount=4500.0, payee="B", channel="UPI", is_historical=True),
        Transaction(transaction_id="TXN-03", date="2026-08-03", time="16:00:00", amount=8200.0, payee="C", channel="Card", is_historical=True),
        Transaction(transaction_id="TXN-04", date="2026-08-04", time="18:00:00", amount=6700.0, payee="A", channel="UPI", is_historical=True),
        Transaction(transaction_id="TXN-05", date="2026-08-05", time="11:00:00", amount=3100.0, payee="B", channel="UPI", is_historical=True),
    ]

    baseline = calculate_customer_baseline(txns)

    assert baseline.historical_count == 5
    assert baseline.median_amount == 4500.0
    assert baseline.min_amount == 2000.0
    assert baseline.max_amount == 8200.0
    assert baseline.active_hours_start == 10
    assert baseline.active_hours_end == 18
    assert baseline.baseline_confidence == "HIGH"
    assert "UPI" in baseline.common_channels

def test_insufficient_baseline_confidence():
    txns = [
        Transaction(transaction_id="TXN-01", date="2026-08-01", time="10:00:00", amount=1000.0, payee="A", channel="UPI", is_historical=True),
    ]

    baseline = calculate_customer_baseline(txns)
    assert baseline.historical_count == 1
    assert baseline.baseline_confidence == "LOW"
