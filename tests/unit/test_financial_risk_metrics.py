"""Canonical AAL / VaR / TVaR definitions and reconciliation checks."""
from __future__ import annotations

import numpy as np
import pytest

from crq.metrics import (
    FORBIDDEN_PRIMARY_LOSS_LABELS,
    VAR_QUANTILE_METHOD,
    annual_aggregate_metrics,
    expected_shortfall,
    executive_risk_narrative,
    multi_year_event_probability,
    normalize_tail_basis,
    tvar_tail_contributions,
    value_at_risk,
)
from it_crq.engine import _metrics as it_metrics
from ot_crq.engine import expected_shortfall as ot_es


def test_aal_is_mean_including_zeros():
    arr = np.array([0.0, 0.0, 10.0, 30.0])
    m = annual_aggregate_metrics(arr)
    assert m["AAL"] == pytest.approx(10.0)


def test_var_uses_documented_higher_method():
    arr = np.arange(1, 101, dtype=float)
    assert VAR_QUANTILE_METHOD == "higher"
    assert value_at_risk(arr, 0.95) == float(np.quantile(arr, 0.95, method="higher"))
    assert value_at_risk(arr, 0.99) == float(np.quantile(arr, 0.99, method="higher"))


def test_tvar95_is_mean_of_worst_5_percent():
    arr = np.array([0.0] * 99 + [100.0])
    m = annual_aggregate_metrics(arr)
    assert m["TVaR95"] == pytest.approx(20.0)
    assert m["VaR95"] == 0.0
    assert expected_shortfall(arr, 0.95) == pytest.approx(20.0)
    assert ot_es(arr, 0.95) == pytest.approx(20.0)
    assert it_metrics(arr)["TVaR95"] == pytest.approx(20.0)


def test_tvar99_is_mean_of_worst_1_percent():
    arr = np.array([0.0] * 99 + [100.0])
    m = annual_aggregate_metrics(arr)
    assert m["TVaR99"] == pytest.approx(100.0)
    assert m["VaR99"] == 100.0


def test_scenario_actor_aal_reconcile_pattern():
    total = np.array([0.0, 10.0, 20.0, 30.0])
    a = np.array([0.0, 4.0, 8.0, 12.0])
    b = np.array([0.0, 6.0, 12.0, 18.0])
    assert float(a.mean() + b.mean()) == pytest.approx(float(total.mean()))


def test_tvar_contributions_reconcile():
    total = np.array([0.0, 10.0, 20.0, 40.0, 80.0, 100.0, 120.0, 140.0, 160.0, 200.0])
    c1 = total * 0.4
    c2 = total * 0.6
    contrib = tvar_tail_contributions(total, {"c1": c1, "c2": c2}, 0.90)
    tvar = expected_shortfall(total, 0.90)
    assert contrib["c1"] + contrib["c2"] == pytest.approx(tvar)


def test_normalize_tail_basis_aliases():
    assert normalize_tail_basis("TVaR 99%") == "TVaR 99"
    assert normalize_tail_basis("TVaR 95") == "TVaR 95"


def test_multi_year_and_narrative():
    assert multi_year_event_probability(0.1, 5) == pytest.approx(1 - 0.9**5)
    text = executive_risk_narrative(
        p_any_1y=0.1,
        p_any_5y=0.4,
        aal=1e6,
        var95=2e6,
        tvar95=3e6,
        var99=4e6,
        tvar99=5e6,
        top_aal_name="Operational Disruption",
        top_tvar99_name="Safety System Compromise",
        within_tolerance=False,
        tolerance=1e6,
    )
    assert "VaR 95" in text and "TVaR 99" in text
    assert "Operational Disruption" in text
    assert "above the selected tolerance" in text
    for bad in FORBIDDEN_PRIMARY_LOSS_LABELS:
        assert bad not in text
