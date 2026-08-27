"""Canonical annual-aggregate financial-risk metrics for IT and OT CRQ.

Principal metrics (always from the annual aggregate loss distribution, including
zero-loss years):

* AAL — mean annual aggregate loss
* VaR 95 — 95th percentile (numpy quantile method documented below)
* TVaR 95 — mean of the worst 5% of simulation trials (fractional ES)
* VaR 99 — 99th percentile
* TVaR 99 — mean of the worst 1% of simulation trials (fractional ES)

VaR percentile convention
-------------------------
``VAR_QUANTILE_METHOD = "higher"`` (NumPy ``np.quantile``).

This selects the smallest sample value that is greater than or equal to the
theoretical percentile position. It does not interpolate between adjacent
order statistics. Secondary executive language may note that VaR 95 ≈ 1-in-20
and VaR 99 ≈ 1-in-100 annual aggregate loss; the formal labels remain
``VaR 95`` and ``VaR 99``.

TVaR / Expected Shortfall
-------------------------
TVaR is the mean of the upper ``(1 - q)`` mass of the ordered annual trials,
including fractional mass at the cut so point masses do not expand the tail
beyond the intended 5% or 1%.
"""

from __future__ import annotations

import math

import numpy as np

# Formal display labels (workbook, charts, narrative).
LABEL_AAL = "AAL"
LABEL_VAR_95 = "VaR 95"
LABEL_TVAR_95 = "TVaR 95"
LABEL_VAR_99 = "VaR 99"
LABEL_TVAR_99 = "TVaR 99"

CORE_METRIC_LABELS = (
    LABEL_AAL,
    LABEL_VAR_95,
    LABEL_TVAR_95,
    LABEL_VAR_99,
    LABEL_TVAR_99,
)

# NumPy quantile method for VaR on annual aggregate loss vectors.
VAR_QUANTILE_METHOD = "higher"

# Forbidden primary labels for annual financial risk (search / QA).
FORBIDDEN_PRIMARY_LOSS_LABELS = (
    "P95 loss",
    "P99 loss",
    "Conditional event loss P95",
    "Conditional event loss P99",
    "PML",
    "1-in-100 PML",
    "Tail loss",
    "Return-period loss",
)

TAIL_ABOVE_RETENTION_LABEL = "Selected TVaR minus illustrative retention"


def expected_shortfall(arr, q: float) -> float:
    """Mean of the worst (1-q) fraction of trials, with fractional cut mass."""
    x = np.sort(np.asarray(arr, dtype=float))
    n = len(x)
    if n == 0:
        raise ValueError("Expected shortfall requires at least one observation.")
    q = float(np.clip(q, 0.0, 1.0 - 1.0 / n))
    cut = q * n
    k = int(math.floor(cut))
    frac = cut - k
    tail_sum = float(x[k:].sum())
    tail_count = float(n - k)
    if frac > 0 and k < n:
        tail_sum -= frac * float(x[k])
        tail_count -= frac
    return tail_sum / tail_count if tail_count > 0 else float(x[-1])


def value_at_risk(arr, q: float) -> float:
    """VaR at probability level q from the annual aggregate loss vector."""
    a = np.asarray(arr, dtype=float)
    if a.size == 0:
        raise ValueError("VaR requires at least one observation.")
    return float(np.quantile(a, q, method=VAR_QUANTILE_METHOD))


def var_tvar(arr, q: float) -> tuple[float, float]:
    """Return (VaR, TVaR) at level q for an annual aggregate loss vector."""
    return value_at_risk(arr, q), expected_shortfall(arr, q)


def annual_aggregate_metrics(arr) -> dict[str, float]:
    """Compute the five principal metrics plus P(any successful year)."""
    a = np.asarray(arr, dtype=float)
    if a.size == 0:
        raise ValueError("Annual aggregate metrics require at least one trial.")
    v95, t95 = var_tvar(a, 0.95)
    v99, t99 = var_tvar(a, 0.99)
    return {
        "AAL": float(a.mean()),
        "VaR95": v95,
        "TVaR95": t95,
        "VaR99": v99,
        "TVaR99": t99,
        "PAny": float(np.mean(a > 0)),
    }


def multi_year_event_probability(p_any_1y: float, years: int) -> float:
    """Independent-year approximation: 1 - (1 - p)^n."""
    p = float(np.clip(p_any_1y, 0.0, 1.0))
    n = int(years)
    if n <= 0:
        return 0.0
    return float(1.0 - (1.0 - p) ** n)


def exceedance_probability(arr, threshold: float) -> float:
    """Share of annual aggregate trials exceeding a tolerance amount."""
    a = np.asarray(arr, dtype=float)
    if a.size == 0:
        return 0.0
    return float(np.mean(a > float(threshold)))


def tvar_tail_contributions(total_annual, component_annuals: dict[str, np.ndarray], q: float) -> dict[str, float]:
    """Allocate TVaR by mean component contribution within the worst (1-q) trials.

    Contributions are mean(component | trial in worst tail mass), using the same
    fractional cut convention as expected_shortfall. They reconcile to TVaR
    subject to rounding when components partition total annual loss.
    """
    total = np.asarray(total_annual, dtype=float)
    n = total.size
    if n == 0:
        return {k: 0.0 for k in component_annuals}
    q = float(np.clip(q, 0.0, 1.0 - 1.0 / n))
    order = np.argsort(total)
    cut = q * n
    k = int(math.floor(cut))
    frac = cut - k
    out: dict[str, float] = {}
    for name, comp in component_annuals.items():
        c = np.asarray(comp, dtype=float)[order]
        tail_sum = float(c[k:].sum())
        tail_count = float(n - k)
        if frac > 0 and k < n:
            tail_sum -= frac * float(c[k])
            tail_count -= frac
        out[name] = tail_sum / tail_count if tail_count > 0 else float(c[-1])
    return out


def normalize_tail_basis(value) -> str:
    """Map workbook aliases to formal TVaR 95 / TVaR 99 labels."""
    raw = str(value or LABEL_TVAR_99).strip()
    aliases = {
        "TVaR 95%": LABEL_TVAR_95,
        "TVaR95": LABEL_TVAR_95,
        LABEL_TVAR_95: LABEL_TVAR_95,
        "TVaR 99%": LABEL_TVAR_99,
        "TVaR99": LABEL_TVAR_99,
        LABEL_TVAR_99: LABEL_TVAR_99,
    }
    if raw not in aliases:
        raise ValueError("TAIL_BASIS / TVaR selection must be TVaR 95 or TVaR 99.")
    return aliases[raw]


def format_money(value: float) -> str:
    return f"${float(value):,.0f}"


def format_pct(value: float) -> str:
    return f"{100.0 * float(value):.1f}%"


def executive_risk_narrative(
    *,
    p_any_1y: float,
    p_any_5y: float | None,
    aal: float,
    var95: float,
    tvar95: float,
    var99: float,
    tvar99: float,
    top_aal_name: str | None,
    top_tvar99_name: str | None,
    within_tolerance: bool | None,
    tolerance: float | None = None,
) -> str:
    """Dynamic Executive Risk Story paragraph from the selected run."""
    five = ""
    if p_any_5y is not None:
        five = f", increasing to {format_pct(p_any_5y)} over five years"
    parts = [
        f"The facility has an estimated {format_pct(p_any_1y)} probability of at least one "
        f"successful material cyber event in the next year{five}.",
        f"Annual Average Loss is {format_money(aal)}.",
        f"VaR 95 is {format_money(var95)} and average loss across the worst 5% of simulated years, "
        f"TVaR 95, is {format_money(tvar95)}.",
        f"VaR 99 is {format_money(var99)} and average loss across the worst 1% of simulated years, "
        f"TVaR 99, is {format_money(tvar99)}.",
    ]
    if top_aal_name:
        contrib = f"{top_aal_name} is the largest contributor to expected annual loss"
        if top_tvar99_name:
            contrib += f", while {top_tvar99_name} is the largest contributor to TVaR 99"
        parts.append(contrib + ".")
    if within_tolerance is not None and tolerance is not None:
        status = "within" if within_tolerance else "above"
        parts.append(
            f"Current risk is {status} the selected tolerance of {format_money(tolerance)}."
        )
    elif within_tolerance is not None:
        status = "within" if within_tolerance else "above"
        parts.append(f"Current risk is {status} the selected tolerance.")
    return " ".join(parts)
