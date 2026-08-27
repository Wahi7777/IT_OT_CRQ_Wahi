"""Driver / category aggregation and reconciliation helpers."""

from __future__ import annotations

from typing import Any

import numpy as np

from crq.impact.catalogue import driver_category, driver_name
from crq.metrics import annual_aggregate_metrics
from crq.reporting_helpers import component_rows_from_trials, portfolio_tail_reconcile


def fit_lognormal(p50: float, p99: float) -> dict[str, float | None]:
    """Shared P50/P99 → lognormal parameters (core-owned fitting)."""
    import math

    if p50 <= 0 and p99 <= 0:
        return {"p50": 0.0, "p99": 0.0, "mu": None, "sigma": 0.0, "mean": 0.0}
    p50 = max(float(p50), 1.0)
    p99 = max(float(p99), p50 * 1.000001)
    mu = math.log(p50)
    sigma = (math.log(p99) - mu) / 2.326347874
    mean = math.exp(mu + 0.5 * sigma * sigma)
    return {"p50": p50, "p99": p99, "mu": mu, "sigma": sigma, "mean": mean}


def rollup_driver_trials_to_categories(
    driver_annuals: dict[str, np.ndarray],
) -> dict[str, np.ndarray]:
    """Sum driver trial arrays into Balbix major categories."""
    out: dict[str, np.ndarray] = {}
    for did, arr in driver_annuals.items():
        cat = driver_category(did)
        a = np.asarray(arr, dtype=float)
        if cat not in out:
            out[cat] = np.zeros_like(a)
        out[cat] = out[cat] + a
    return out


def driver_contribution_rows(
    total_annual: np.ndarray,
    driver_annuals: dict[str, np.ndarray],
) -> list[dict[str, Any]]:
    """Applicable-driver rows only (omit zero clutter)."""
    labeled = {driver_name(did): arr for did, arr in driver_annuals.items()}
    rows = component_rows_from_trials(total_annual, labeled)
    name_to_id = {driver_name(did): did for did in driver_annuals}
    for r in rows:
        did = name_to_id.get(r["name"])
        r["driver_id"] = did
        r["category"] = driver_category(did) if did else None
    return rows


def category_contribution_rows(
    total_annual: np.ndarray,
    driver_annuals: dict[str, np.ndarray],
) -> list[dict[str, Any]]:
    cats = rollup_driver_trials_to_categories(driver_annuals)
    return component_rows_from_trials(total_annual, cats)


def reconcile_impact_hierarchy(
    total_annual: np.ndarray,
    driver_annuals: dict[str, np.ndarray],
    *,
    atol: float = 1.0,
) -> dict[str, Any]:
    """Check driver→total and category→total AAL/TVaR reconciliations."""
    total = np.asarray(total_annual, dtype=float)
    if driver_annuals:
        stacked = np.zeros_like(total)
        for arr in driver_annuals.values():
            stacked = stacked + np.asarray(arr, dtype=float)
        sum_drivers = stacked
    else:
        sum_drivers = np.zeros_like(total)
    cats = rollup_driver_trials_to_categories(driver_annuals)
    sum_cats = np.zeros_like(total)
    for arr in cats.values():
        sum_cats = sum_cats + np.asarray(arr, dtype=float)

    m_total = annual_aggregate_metrics(total)
    driver_rows = driver_contribution_rows(total, driver_annuals)
    cat_rows = category_contribution_rows(total, driver_annuals)

    aal_drivers = float(sum(r["aal"] for r in driver_rows))
    aal_cats = float(sum(r["aal"] for r in cat_rows))
    aal_ok = abs(aal_drivers - m_total["AAL"]) <= max(atol, abs(m_total["AAL"]) * 1e-6)
    aal_cat_ok = abs(aal_cats - m_total["AAL"]) <= max(atol, abs(m_total["AAL"]) * 1e-6)
    trial_ok = bool(np.allclose(sum_drivers, total, rtol=1e-6, atol=atol))
    trial_cat_ok = bool(np.allclose(sum_cats, total, rtol=1e-6, atol=atol))

    t99_drv = portfolio_tail_reconcile(driver_rows, m_total["TVaR99"], atol=atol)
    t99_cat = portfolio_tail_reconcile(cat_rows, m_total["TVaR99"], atol=atol)
    t95_drv = portfolio_tail_reconcile(
        driver_rows, m_total["TVaR95"], value_key="contrib_tvar95", atol=atol
    )
    t95_cat = portfolio_tail_reconcile(
        cat_rows, m_total["TVaR95"], value_key="contrib_tvar95", atol=atol
    )

    return {
        "aal_drivers_ok": aal_ok,
        "aal_categories_ok": aal_cat_ok,
        "trial_drivers_ok": trial_ok,
        "trial_categories_ok": trial_cat_ok,
        "tvar99_drivers": t99_drv,
        "tvar99_categories": t99_cat,
        "tvar95_drivers": t95_drv,
        "tvar95_categories": t95_cat,
        "ok": aal_ok
        and aal_cat_ok
        and trial_ok
        and trial_cat_ok
        and t99_drv["ok"]
        and t99_cat["ok"],
    }
