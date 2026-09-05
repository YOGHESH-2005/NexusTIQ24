# Risk Rule R04: Customer Behaviour Deviation

## Purpose & Scope
Rule R04 detects complex multi-attribute behavioural shifts that deviate significantly from a customer's multi-month transaction profile across amount, frequency, channel, and payee type.

## Objective Evaluation Criteria
- **Channel Shift**: Customer historically uses UPI/ATM ($>90\%$), but current activity shifts to high-value wire transfers (IMPS/NEFT/RTGS).
- **Frequency Spike**: Single-day transaction count exceeds $3\times$ daily average.
- **Combined Deviation**: Multiple minor deviations occurring simultaneously that together represent a pattern break.

## Example Case
- Historical Profile: Mostly daytime UPI transactions between ₹2,000 and ₹10,000.
- Current Activity: ₹150,000 IMPS transfer at 03:00 AM to an unseen recipient.
- Trigger: R04 Triggered (Multi-attribute pattern deviation).

## Investigator Guidance
1. Synthesize the overall profile change.
2. Look for recent credential changes, address updates, or device registrations.
3. Prioritize verification of high-risk channel transactions (Wire/IMPS/NEFT).

## Limitations
- Behavioural shifts can occur naturally due to major life events (e.g. house purchase, vacation). Human verification is mandatory.
