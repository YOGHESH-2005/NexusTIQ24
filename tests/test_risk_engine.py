import pytest
from src.models import Transaction
from src.baseline import calculate_customer_baseline
from src.risk_engine import run_risk_engine

def test_r01_large_transfer_trigger():
    hist = [
        Transaction(transaction_id=f"TXN-{i}", date="2026-08-01", time="10:00:00", amount=10000.0, payee="Store", channel="UPI", is_historical=True)
        for i in range(5)
    ]
    curr = [
        Transaction(transaction_id="TXN-EVAL-1", date="2026-09-04", time="14:00:00", amount=150000.0, payee="Global Corp", channel="IMPS", is_historical=False)
    ]

    all_txns = hist + curr
    baseline = calculate_customer_baseline(all_txns)
    findings = run_risk_engine(all_txns, baseline)

    r01_findings = [f for f in findings if f.rule_id == "R01"]
    assert len(r01_findings) == 1
    assert r01_findings[0].ratio >= 10.0
    assert "TXN-EVAL-1" in r01_findings[0].transaction_ids

def test_r02_new_payee_burst_trigger():
    hist = [
        Transaction(transaction_id="TXN-01", date="2026-08-01", time="10:00:00", amount=1000.0, payee="Old Payee", channel="UPI", is_historical=True)
        for _ in range(5)
    ]
    curr = [
        Transaction(transaction_id="TXN-02", date="2026-09-04", time="22:00:00", amount=75000.0, payee="New Scammer", channel="IMPS", is_historical=False),
        Transaction(transaction_id="TXN-03", date="2026-09-04", time="22:05:00", amount=65000.0, payee="New Scammer", channel="IMPS", is_historical=False),
    ]

    all_txns = hist + curr
    baseline = calculate_customer_baseline(all_txns)
    findings = run_risk_engine(all_txns, baseline)

    r02_findings = [f for f in findings if f.rule_id == "R02"]
    assert len(r02_findings) == 1
    assert "TXN-02" in r02_findings[0].transaction_ids
    assert "TXN-03" in r02_findings[0].transaction_ids

def test_r03_odd_hours_trigger():
    hist = [
        Transaction(transaction_id="TXN-01", date="2026-08-01", time="10:00:00", amount=2000.0, payee="Shop", channel="UPI", is_historical=True),
        Transaction(transaction_id="TXN-02", date="2026-08-02", time="14:00:00", amount=3000.0, payee="Shop", channel="UPI", is_historical=True),
        Transaction(transaction_id="TXN-03", date="2026-08-03", time="16:00:00", amount=2500.0, payee="Shop", channel="UPI", is_historical=True),
    ]
    curr = [
        Transaction(transaction_id="TXN-NIGHT", date="2026-09-04", time="03:17:00", amount=50000.0, payee="Night Vendor", channel="IMPS", is_historical=False)
    ]

    all_txns = hist + curr
    baseline = calculate_customer_baseline(all_txns)
    findings = run_risk_engine(all_txns, baseline)

    r03_findings = [f for f in findings if f.rule_id == "R03"]
    assert len(r03_findings) == 1
    assert "TXN-NIGHT" in r03_findings[0].transaction_ids

def test_normal_customer_no_trigger():
    hist = [
        Transaction(transaction_id="TXN-01", date="2026-08-01", time="10:00:00", amount=2500.0, payee="FreshMart", channel="UPI", is_historical=True),
        Transaction(transaction_id="TXN-02", date="2026-08-05", time="14:00:00", amount=4000.0, payee="FreshMart", channel="UPI", is_historical=True),
        Transaction(transaction_id="TXN-03", date="2026-08-10", time="12:00:00", amount=3500.0, payee="FreshMart", channel="UPI", is_historical=True),
    ]
    curr = [
        Transaction(transaction_id="TXN-04", date="2026-09-01", time="11:00:00", amount=3000.0, payee="FreshMart", channel="UPI", is_historical=False)
    ]

    all_txns = hist + curr
    baseline = calculate_customer_baseline(all_txns)
    findings = run_risk_engine(all_txns, baseline)

    assert len(findings) == 0  # No rule triggered for normal customer!

def test_insufficient_history_suppresses_rules():
    hist = [
        Transaction(transaction_id="TXN-01", date="2026-08-01", time="10:00:00", amount=1000.0, payee="Self Deposit", channel="UPI", is_historical=True)
    ]
    curr = [
        Transaction(transaction_id="TXN-02", date="2026-09-04", time="15:00:00", amount=85000.0, payee="Merchant Inc", channel="IMPS", is_historical=False)
    ]

    all_txns = hist + curr
    baseline = calculate_customer_baseline(all_txns)
    assert baseline.historical_count == 1
    
    findings = run_risk_engine(all_txns, baseline)
    assert findings == []  # Must return empty list when historical_count < 3!
