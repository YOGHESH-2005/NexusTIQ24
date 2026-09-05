from typing import List
import numpy as np
from src.models import Transaction, CustomerBaseline

def calculate_customer_baseline(transactions: List[Transaction]) -> CustomerBaseline:
    """
    Computes statistical baseline metrics strictly from customer's historical transactions.
    """
    hist_txns = [t for t in transactions if t.is_historical]
    
    # If no explicitly marked historical transactions, treat all but last row as historical
    if not hist_txns and len(transactions) > 1:
        hist_txns = transactions[:-1]
    elif not hist_txns:
        hist_txns = transactions

    count = len(hist_txns)
    
    if count == 0:
        return CustomerBaseline(
            historical_count=0,
            median_amount=0.0,
            mean_amount=0.0,
            min_amount=0.0,
            max_amount=0.0,
            percentile_95_amount=0.0,
            typical_range_str="₹0.00–₹0.00",
            active_hours_start=8,
            active_hours_end=22,
            active_hours_str="08:00–22:00",
            common_channels=[],
            common_payees=[],
            avg_daily_transactions=0.0,
            baseline_confidence="LOW"
        )

    amounts = [t.amount for t in hist_txns if t.amount > 0]
    if not amounts:
        amounts = [0.0]

    median_amt = float(np.median(amounts))
    mean_amt = float(np.mean(amounts))
    min_amt = float(np.min(amounts))
    max_amt = float(np.max(amounts))
    p95_amt = float(np.percentile(amounts, 95)) if len(amounts) >= 3 else max_amt * 1.5

    # Channels
    channel_counts = {}
    for t in hist_txns:
        if t.channel and t.channel != "UNKNOWN":
            channel_counts[t.channel] = channel_counts.get(t.channel, 0) + 1
    top_channels = sorted(channel_counts.keys(), key=lambda c: channel_counts[c], reverse=True)[:3]

    # Payees
    payee_counts = {}
    for t in hist_txns:
        if t.payee and t.payee != "UNKNOWN_PAYEE":
            payee_counts[t.payee] = payee_counts.get(t.payee, 0) + 1
    top_payees = sorted(payee_counts.keys(), key=lambda p: payee_counts[p], reverse=True)[:5]

    # Active Hours Calculation
    hours = []
    for t in hist_txns:
        if t.time and ":" in t.time:
            try:
                h = int(t.time.split(":")[0])
                hours.append(h)
            except ValueError:
                pass

    if hours:
        start_hour = max(0, min(hours))
        end_hour = min(23, max(hours))
        # Add slight buffer for standard activity
        active_str = f"{start_hour:02d}:00–{end_hour:02d}:00"
    else:
        start_hour = 8
        end_hour = 22
        active_str = "08:00–22:00"

    # Confidence rating
    if count >= 5:
        confidence = "HIGH"
    elif count >= 3:
        confidence = "MEDIUM"
    else:
        confidence = "LOW"

    range_str = f"₹{min_amt:,.2f}–₹{max_amt:,.2f}"

    return CustomerBaseline(
        historical_count=count,
        median_amount=median_amt,
        mean_amount=mean_amt,
        min_amount=min_amt,
        max_amount=max_amt,
        percentile_95_amount=p95_amt,
        typical_range_str=range_str,
        active_hours_start=start_hour,
        active_hours_end=end_hour,
        active_hours_str=active_str,
        common_channels=top_channels if top_channels else ["UPI"],
        common_payees=top_payees,
        avg_daily_transactions=round(count / max(1, len(set(t.date for t in hist_txns if t.date))), 1),
        baseline_confidence=confidence
    )
