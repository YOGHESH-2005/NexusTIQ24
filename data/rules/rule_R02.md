# Risk Rule R02: New Payee Burst

## Purpose & Scope
Rule R02 detects velocity anomalies where a newly added payee account receives multiple transactions or high cumulative funds shortly after first appearance. Fraudulent account takeovers or scam coercion often involve rapid drain to a newly introduced account.

## Objective Evaluation Criteria
- **Payee Identification**: Payee does not exist in customer's prior transaction history.
- **Velocity Criteria**: $\ge 2$ transactions within 24 hours OR a single newly added payee transaction exceeding ₹50,000.
- **Trigger Result**: R02 Risk Signal Generated detailing payee creation, total burst amount, and transaction sequence.

## Example Case
- New Payee: "QuickMoney Services"
- 10:02 PM: ₹75,000
- 10:08 PM: ₹65,000
- 10:15 PM: ₹45,000
- Cumulative Payout: ₹185,000 across 13 minutes.
- Trigger: R02 Triggered.

## Investigator Guidance
1. Inspect the total cumulative flow to the new payee across all channels.
2. Check whether the beneficiary account has been flagged by central fraud registries or blacklists.
3. Review channel usage (e.g. rapid UPI transfers followed by IMPS drain).
4. Recommend contacting the customer to confirm if they initiated the transfer under duress or deception.

## Limitations
- Legitimate new billers or urgent family transfers can trigger R02.
- Always present the timeline clearly to the investigator.
