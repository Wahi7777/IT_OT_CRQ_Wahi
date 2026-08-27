"""Appetite and insurance programme unit tests."""
from __future__ import annotations

import numpy as np
import pytest

from crq.appetite import evaluate_appetite, parse_appetite_inputs
from crq.insurance import apply_programme, parse_programme


def test_blank_appetite_is_tolerance_not_set():
    appet = parse_appetite_inputs({})
    out = evaluate_appetite(appetite=appet, aal=1e6, p_any=0.1)
    assert out["appetite_status"] == "Tolerance not set"
    assert out["p_exceed_tolerance"] is None


def test_appetite_not_inferred_from_retention():
    # Retention must never appear in appetite inputs
    appet = parse_appetite_inputs({"INSURANCE_RETENTION": 5_000_000})
    assert appet["ANNUAL_LOSS_TOLERANCE"] is None
    out = evaluate_appetite(appetite=appet, aal=9_000_000)
    assert out["appetite_status"] == "Tolerance not set"


def test_appetite_above_and_within():
    appet = parse_appetite_inputs({"ANNUAL_LOSS_TOLERANCE": 1_000_000, "MAX_ACCEPTABLE_TVAR_99": 10_000_000})
    above = evaluate_appetite(appetite=appet, aal=2_000_000, tvar99=5_000_000, annual_losses=np.array([0.0, 2e6]))
    assert above["appetite_status"] == "Above tolerance"
    within = evaluate_appetite(appetite=appet, aal=500_000, tvar99=5_000_000, annual_losses=np.array([0.0, 100.0]))
    assert within["appetite_status"] == "Within tolerance"


def test_insurance_trial_reconcile():
    prog = parse_programme({"INSURANCE_RETENTION": 100, "layers": [
        {"name": "Primary", "attachment": 100, "limit": 400, "coinsurance": 1.0},
        {"name": "XS", "attachment": 500, "limit": 1000, "coinsurance": 0.8},
    ]})
    gu = np.array([50.0, 300.0, 2000.0, 0.0])
    out = apply_programme(gu, prog)
    assert out["reconcile_ok"]
    assert out["metrics_ground_up"]["AAL"] == pytest.approx(gu.mean())
    assert out["expected_insured_recovery"] >= 0
