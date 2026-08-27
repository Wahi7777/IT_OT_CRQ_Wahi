# 00 Output Bridge field classes (after a Python run)

Principal financial metrics use the labels **AAL**, **VaR 95**, **TVaR 95**, **VaR 99**, **TVaR 99**
(see `docs/methodology/FINANCIAL_RISK_METRICS.md`).

## ENGINE_WRITTEN

- B15:C23 — AAL, VaR 95, TVaR 95, VaR 99, TVaR 99, P(any successful event), successful-event frequency, attempt frequency, P(annual loss exceeds tolerance) (Best / Prudent)
- B24 — Risk-appetite status
- Actor AAL rows from A27; scenario AAL from A34
- A43:E53 — aggregate LEC (exceedance probability, Best/Prudent AEP and OEP)
- Duplicate snapshot H14:J22 and actor/scenario H/I
- Entire `00 Engine Results` sheet
- Run metadata H41:I58 (versions, hashes, seed, years, OI yes/no, validation, run ID)
- Dashboard B71:B78 selected-view cache

Successful-event frequency is the engine value, **not** Attempt × P(success) recomputed in Excel.

## PRESENTATION_FORMULA

- `00 Dashboard` headline cards (P(any), AAL, VaR 95, TVaR 95, VaR 99, TVaR 99, P(exceed tolerance), appetite): Best Estimate vs Prudent `IF` onto Bridge B/C
- Filters, ranking, chart sources, hyperlinks
- Risk Transfer selected TVaR minus retention (indicative diagnostic, not a policy pricer)

## STATIC_METADATA

- Sector, domain, asset, pack ID, reporting basis (Bridge B6:B10 after a run)

## Anti-double-counting

Outside-In may change (1) facility/organisation/route opportunity or (2) a TTP Prevent barrier multiplier in (0, 1], not both for the same finding unless `double_counting_assessment` contains `exposure vs exploitability`. Final P(success) remains the product of stage-throughs.
