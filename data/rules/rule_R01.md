# Risk Rule R01: Unusually Large Transfer

## Purpose & Scope
Rule R01 evaluates single transaction amounts against the customer's historical baseline median and established spending thresholds. The purpose is to identify transfer amounts that are statistical outliers relative to the individual's past behaviour.

## Objective Evaluation Criteria
- **Baseline Metric**: Historical median transaction amount ($\tilde{x}$) calculated from at least 3 historical records.
- **Threshold**: Current transaction amount $\ge 5.0 \times \tilde{x}$ OR exceeds 95th percentile of historical activity.
- **Trigger Result**: R01 Risk Signal Generated with ratio ($x / \tilde{x}$).

## Example Case
- Historical Median: ₹14,200
- Current Transaction: ₹185,000
- Multiplier: 13.03x
- Trigger: R01 Triggered.

## Investigator Guidance
1. Compare the flagged transaction against historical high-water mark transactions.
2. Determine if the destination channel (e.g. IMPS vs RTGS) matches typical high-value transfer methods for this account.
3. Check for secondary confirmation (e.g., OTP verification or customer phone outreach) prior to clearing.
4. Do NOT mark as fraud solely based on amount; high-value transfers can be legitimate major purchases.

## Limitations
- If historical dataset is smaller than 3 transactions, baseline confidence is LOW.
- Inflation or scheduled major recurring transfers (e.g., annual tuition/rent) must be accounted for by the human investigator.
