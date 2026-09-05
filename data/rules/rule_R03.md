# Risk Rule R03: Odd-Hours Activity

## Purpose & Scope
Rule R03 evaluates temporal anomalies by comparing transaction timestamps against the customer's established active hours baseline.

## Objective Evaluation Criteria
- **Customer Baseline Hours**: Computed start and end hours during which $\ge 90\%$ of past historical transactions occurred (typically 08:00 to 22:00 local time).
- **Temporal Outlier**: Any high-value or unusual transaction executed outside this normal window (e.g. 00:00 to 05:00 AM).
- **Trigger Result**: R03 Risk Signal Generated with exact timestamp and hour discrepancy.

## Example Case
- Historical Operating Window: 08:00 – 22:00
- Flagged Transaction Time: 03:17 AM
- Deviation: Executed 4 hours 43 minutes outside normal operational window.
- Trigger: R03 Triggered.

## Investigator Guidance
1. Determine if odd-hours execution is accompanied by other risk signals (e.g. R01 or R02).
2. Check for international travel context or automated subscription charges.
3. If executed via mobile banking in the middle of the night along with a new payee burst, elevate priority for customer callback.

## Limitations
- Shift workers, travelers, or nocturnal users may naturally transact at night; baseline computation must adapt if historical night activity exists.
