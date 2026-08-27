# Principal financial-risk metrics

This document is the authoritative definition for annual-aggregate financial-risk
metrics used by the IT and OT CRQ engines, output bridge, dashboards, charts,
methodology text and generated narrative.

## Core metrics

All five principal metrics are taken from the **annual aggregate loss
distribution**, including zero-loss years:

| Metric | Definition |
| --- | --- |
| **AAL** | Mean annual aggregate loss across all simulation trials |
| **VaR 95** | 95th percentile of the annual aggregate loss distribution |
| **TVaR 95** | Mean annual aggregate loss across the worst 5% of simulation trials |
| **VaR 99** | 99th percentile of the annual aggregate loss distribution |
| **TVaR 99** | Mean annual aggregate loss across the worst 1% of simulation trials |

Implementation: `src/crq/metrics.py`.

### VaR percentile convention

VaR uses NumPy `np.quantile(..., method="higher")` (`VAR_QUANTILE_METHOD`).
This selects the smallest sample value at or above the theoretical percentile
position and does **not** interpolate between adjacent order statistics.

Secondary executive language may note:

* VaR 95 ≈ 1-in-20 annual aggregate loss
* VaR 99 ≈ 1-in-100 annual aggregate loss

The formal label remains `VaR 95` / `VaR 99`. Do not headline return-period or
PML language.

### TVaR / Expected Shortfall

TVaR is the mean of the upper `(1 - q)` mass of ordered annual trials, including
fractional mass at the cut so tied values / point masses do not expand the tail
beyond the intended 5% or 1%.

## Forbidden primary labels

Do not use these as primary annual financial-risk labels:

* P95 loss / P99 loss
* Conditional event loss P95 / P99
* PML / 1-in-100 PML
* Tail loss
* Return-period loss (as the primary metric name)

Event-level severity belongs under **Successful-Event Consequence Diagnostics**
and must be labelled `Loss severity per successful event`, never VaR/TVaR.

## Charts

The dashboard chart title is **Annual Aggregate Loss Exceedance Curve**.
Annotate VaR 95 and VaR 99 as points on the annual aggregate exceedance curve.
TVaR is the mean loss within the relevant tail, not a single curve abscissa.
