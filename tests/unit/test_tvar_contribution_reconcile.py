"""Regression: portfolio TVaR contributions reconcile; leading component headline."""
from __future__ import annotations

import numpy as np

from crq.metrics import annual_aggregate_metrics, tvar_tail_contributions
from crq.reporting_helpers import (
    component_rows_from_trials,
    leading_tvar99_component,
    portfolio_tail_reconcile,
)


def _partitioned_trials(n=2000, seed=20260821):
    rng = np.random.default_rng(seed)
    # Sparse positive years with additive scenario parts that sum to total
    s1 = rng.gamma(2.0, 50_000.0, size=n)
    s2 = rng.gamma(1.5, 40_000.0, size=n)
    s3 = rng.gamma(1.2, 30_000.0, size=n)
    mask = rng.random(n) < 0.12
    s1 *= mask
    s2 *= mask
    s3 *= mask
    total = s1 + s2 + s3
    return total, {"A": s1, "B": s2, "C": s3}


def test_scenario_and_actor_tvar_contributions_reconcile():
    total, parts = _partitioned_trials()
    m = annual_aggregate_metrics(total)
    for q, key in ((0.95, "TVaR95"), (0.99, "TVaR99")):
        contrib = tvar_tail_contributions(total, parts, q)
        check = portfolio_tail_reconcile(contrib, m[key])
        assert check["ok"], check
    # Actor-style partition (different cut of same total)
    actors = {"X": parts["A"] + 0.5 * parts["B"], "Y": parts["C"] + 0.5 * parts["B"]}
    assert np.allclose(actors["X"] + actors["Y"], total)
    for q, key in ((0.95, "TVaR95"), (0.99, "TVaR99")):
        check = portfolio_tail_reconcile(tvar_tail_contributions(total, actors, q), m[key])
        assert check["ok"], check


def test_loss_component_tvar_contributions_reconcile_and_leading_headline():
    total, parts = _partitioned_trials()
    rows = component_rows_from_trials(total, parts)
    m = annual_aggregate_metrics(total)
    for key in ("contrib_tvar95", "contrib_tvar99"):
        agg_key = "TVaR95" if key.endswith("95") else "TVaR99"
        check = portfolio_tail_reconcile(rows, m[agg_key], value_key=key)
        assert check["ok"], check
    top = leading_tvar99_component(rows)
    assert top is not None
    assert top["name"] == max(rows, key=lambda r: r["contrib_tvar99"])["name"]
    assert abs(top["contrib_tvar99"] - max(r["contrib_tvar99"] for r in rows)) < 1e-9
    assert top["name"] in top["label"]
    assert f"${top['contrib_tvar99']:,.0f}" in top["label"]
    assert "See Business Impact" not in top["label"]


def test_leading_component_ignores_blank_rows():
    rows = [
        {"name": "", "contrib_tvar99": 9e9},
        {"name": "Incident response", "contrib_tvar99": 100.0, "pct_tvar99": 0.8},
        {"name": "Business interruption", "contrib_tvar99": 25.0, "pct_tvar99": 0.2},
    ]
    top = leading_tvar99_component(rows)
    assert top["name"] == "Incident response"
    assert top["contrib_tvar99"] == 100.0
