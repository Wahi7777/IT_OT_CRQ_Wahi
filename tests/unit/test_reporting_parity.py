"""IT/OT reporting parity: shared financial, appetite, insurance, components, packages."""

from __future__ import annotations

import inspect

import numpy as np

from crq.appetite import evaluate_appetite, parse_appetite_inputs
from crq.insurance import apply_programme, parse_programme
from crq.metrics import annual_aggregate_metrics, tvar_tail_contributions
from crq.reporting_helpers import (
    component_rows_from_trials,
    metric_bundle_from_sim,
    package_maturity_overrides,
    treatment_cost_metrics,
)
import it_crq.engine as it_engine
import ot_crq.engine as ot_engine


def test_it_and_ot_import_shared_financial_modules():
    assert it_engine.annual_aggregate_metrics is annual_aggregate_metrics
    assert it_engine.tvar_tail_contributions is tvar_tail_contributions
    assert it_engine.evaluate_appetite is evaluate_appetite
    assert it_engine.apply_programme is apply_programme
    assert ot_engine.annual_aggregate_metrics is annual_aggregate_metrics
    src = inspect.getsource(ot_engine)
    assert "from crq.appetite import" in src
    assert "from crq.insurance import" in src
    assert "apply_programme" in src
    assert "evaluate_appetite" in src


def test_component_tvar_contributions_reconcile():
    rng = np.random.default_rng(7)
    bi = rng.lognormal(8, 1.2, 5000)
    other = rng.lognormal(7, 1.0, 5000)
    total = bi + other
    rows = component_rows_from_trials(total, {"Business interruption": bi, "Other sector-specific costs": other})
    assert abs(sum(r["aal"] for r in rows) - float(total.mean())) < 1e-6
    m = annual_aggregate_metrics(total)
    assert abs(sum(r["contrib_tvar95"] for r in rows) - m["TVaR95"]) < 1e-4
    assert abs(sum(r["contrib_tvar99"] for r in rows) - m["TVaR99"]) < 1e-4


def test_treatment_cost_absent_and_present():
    missing = treatment_cost_metrics(aal_reduction=1000, one_off_cost=None, annual_cost=None, evaluation_years=None)
    assert missing["cost_status"] == "Cost not provided"
    assert missing["benefit_cost_ratio"] is None
    present = treatment_cost_metrics(aal_reduction=1000, one_off_cost=500, annual_cost=100, evaluation_years=3)
    assert present["cost_status"] == "Cost provided"
    assert present["net_benefit"] == 1000 * 3 - (500 + 100 * 3)
    assert present["benefit_cost_ratio"] > 1


def test_package_maturity_overrides_shapes():
    controls = {"C1": {"maturity": "Initial"}, "C2": {"maturity": "Managed"}}
    whatifs = [{"cid": "C1", "mapped": True, "current": "Initial", "whatif": "Developing", "reduction": 10}]
    levels = ["Absent", "Initial", "Developing", "Managed", "Optimised"]
    foundation = package_maturity_overrides(
        controls, package="Foundation", levels=levels,
        effective_level=lambda c: c["maturity"], next_level=lambda x: x, whatifs=whatifs,
    )
    assert foundation == {"C1": "Developing", "C2": "Developing"}
    target = package_maturity_overrides(
        controls, package="Target", levels=levels,
        effective_level=lambda c: c["maturity"], next_level=lambda x: x, whatifs=whatifs,
    )
    assert target == {"C1": "Optimised", "C2": "Optimised"}
    priority = package_maturity_overrides(
        controls, package="Priority", levels=[],
        effective_level=lambda c: c["maturity"], next_level=lambda x: x, whatifs=whatifs,
    )
    assert priority == {"C1": "Developing"}


def test_metric_bundle_five_metrics():
    annual = np.array([0.0] * 90 + [100.0] * 10)
    sim = {"metrics": annual_aggregate_metrics(annual)}
    base = annual_aggregate_metrics(annual * 1.5)
    bundle = metric_bundle_from_sim(sim, base, event_freq=0.1, freq_base=0.2)
    for key in ("aal", "var95", "tvar95", "var99", "tvar99"):
        assert bundle[key] is not None
        assert bundle[f"{key}_base" if key != "aal" else "baseline"] is not None or key == "aal"


def test_insurance_multi_layer_trial_reconcile():
    gu = np.array([0.0, 50.0, 200.0, 800.0, 2000.0])
    prog = parse_programme({
        "INSURANCE_RETENTION": 100,
        "layers": [
            {"name": "Primary", "attachment": 100, "limit": 400, "coinsurance": 1.0},
            {"name": "XS", "attachment": 500, "limit": 1000, "coinsurance": 0.5},
        ],
        "AGGREGATE_PROGRAMME_LIMIT": 1200,
    })
    out = apply_programme(gu, prog)
    assert out["reconcile_ok"]
    assert abs(out["expected_insured_recovery"] + out["expected_retained_loss"] - float(gu.mean())) < 1e-9


def test_appetite_independent_of_retention():
    appetite = parse_appetite_inputs({"ANNUAL_LOSS_TOLERANCE": 1_000_000})
    annual = np.array([0.0, 500_000, 2_000_000])
    status = evaluate_appetite(appetite=appetite, aal=float(annual.mean()), annual_losses=annual)
    assert status["appetite_status"] in {"Within tolerance", "Above tolerance"}
    # Retention is not an appetite input key
    assert "INSURANCE_RETENTION" not in (appetite or {})
