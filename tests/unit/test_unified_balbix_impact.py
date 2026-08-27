"""Unified Balbix impact catalogue, formulas, and IT driver aggregation."""

from __future__ import annotations

import numpy as np
import pytest

from crq.impact import (
    DRIVERS,
    OT_BALBIX_GAPS,
    OT_TO_BALBIX,
    assert_pack_drivers_are_balbix,
    category_contribution_rows,
    driver_category,
    driver_contribution_rows,
    formulas,
    reconcile_impact_hierarchy,
)
from crq.reporting_helpers import IT_DRIVER_TO_COMPONENT


FS_PACK_DRIVERS = {
    "IR_FORENSICS",
    "EXTERNAL_RESPONSE",
    "LEGAL_RESPONSE",
    "RESTORATION",
    "BUSINESS_INTERRUPTION",
    "ENDPOINT_RECOVERY",
    "SERVER_RECOVERY",
    "NOTIFICATION",
    "CREDIT_MONITORING",
    "REGULATORY",
    "CUSTOMER_ATTRITION",
    "FRAUD_NET_RECOVERY",
    "EXTORTION",
    "POST_EVENT_UPLIFT",
}


def test_catalogue_covers_fs_pack_and_rejects_unknown():
    assert assert_pack_drivers_are_balbix(FS_PACK_DRIVERS) == []
    assert assert_pack_drivers_are_balbix({"IR_FORENSICS", "NOT_A_BALBIX_DRIVER"}) == [
        "NOT_A_BALBIX_DRIVER"
    ]


def test_fraud_is_not_incident_response_category():
    assert driver_category("FRAUD_NET_RECOVERY") == "Direct Loss of Funds costs"
    assert IT_DRIVER_TO_COMPONENT["FRAUD_NET_RECOVERY"] == "Direct Loss of Funds costs"
    assert driver_category("IR_FORENSICS") == "Incident & response costs"
    assert driver_category("BUSINESS_INTERRUPTION") == "Business Interruption costs"
    assert driver_category("EXTORTION") == "Data Recovery & Restoration costs"


def test_formula_library_matches_legacy_fs_arithmetic():
    assert formulas.daily_rate_x_duration(2000, 10) == 20000
    assert formulas.records_x_share_x_unit(1_000_000, 0.1, 0.5) == 50_000
    assert formulas.payment_value_x_compromised_x_unrecovered(
        76_500_000_000, 3, 0.01, 0.4
    ) == pytest.approx(76_500_000_000 / 365 * 3 * 0.01 * 0.4)
    assert formulas.revenue_per_day_x_duration_x_share_x_margin(
        365_000, 2, 0.5, 0.4
    ) == pytest.approx(400.0)


def test_domain_relevance_does_not_activate_missing_pack_driver():
    # Catalogue contains CARD_REPLACEMENT but FS pack does not enable it.
    assert "CARD_REPLACEMENT" in DRIVERS
    assert "CARD_REPLACEMENT" not in FS_PACK_DRIVERS


def test_driver_and_category_contributions_reconcile():
    rng = np.random.default_rng(42)
    n = 5000
    # Correlated annual driver losses
    common = rng.random(n) * 1e6
    drivers = {
        "FRAUD_NET_RECOVERY": common * 0.7,
        "IR_FORENSICS": common * 0.2,
        "BUSINESS_INTERRUPTION": common * 0.1,
    }
    total = sum(drivers.values())
    drv_rows = driver_contribution_rows(total, drivers)
    cat_rows = category_contribution_rows(total, drivers)
    assert {r["name"] for r in drv_rows} == {
        DRIVERS[d]["name"] for d in drivers
    }
    assert "Direct Loss of Funds costs" in {r["name"] for r in cat_rows}
    assert "Incident & response costs" in {r["name"] for r in cat_rows}
    assert "Business Interruption costs" in {r["name"] for r in cat_rows}
    # No zero-clutter: empty driver omitted
    empty = {"FRAUD_NET_RECOVERY": drivers["FRAUD_NET_RECOVERY"], "NOTIFICATION": np.zeros(n)}
    rows = driver_contribution_rows(drivers["FRAUD_NET_RECOVERY"], empty)
    assert all(r["aal"] > 0 for r in rows)
    rec = reconcile_impact_hierarchy(total, drivers)
    assert rec["ok"]


def test_channel_comonotonic_drivers_rank_together():
    """Drivers in the same control channel must share the latent (Spearman ≈ 1)."""
    from it_crq.engine import _simulate

    cells = [{
        "event_rate": 5.0,
        "actor": "Nation-state",
        "scenario": "Ransomware",
        "drivers": [
            {"driver_id": "IR_FORENSICS", "block": "Duration", "mu": 8.0, "sigma": 0.5},
            {"driver_id": "EXTERNAL_RESPONSE", "block": "Duration", "mu": 9.0, "sigma": 0.4},
            {"driver_id": "FRAUD_NET_RECOVERY", "block": "Direct", "mu": 12.0, "sigma": 0.6},
        ],
    }]
    sim = _simulate(cells, 8000, 20260821, 1.0, ["Nation-state"], ["Ransomware"], 0.5)
    a = sim["drivers"]["IR_FORENSICS"]
    b = sim["drivers"]["EXTERNAL_RESPONSE"]
    mask = (a + b) > 0
    assert mask.sum() > 50
    # Spearman via rank transform (no scipy dependency)
    ra = a[mask].argsort().argsort().astype(float)
    rb = b[mask].argsort().argsort().astype(float)
    corr = float(np.corrcoef(ra, rb)[0, 1])
    assert corr > 0.95
