"""Shared helpers for control packages, treatment costs, and loss-component taxonomy."""

from __future__ import annotations

from typing import Any

import numpy as np

from crq.metrics import annual_aggregate_metrics, tvar_tail_contributions

# Canonical Balbix major cost categories (reporting roll-up).
# Control-channel blocks (Duration/Exposure/Direct) must never be used as category labels.
COMPONENT_TAXONOMY = (
    "Incident & response costs",
    "Data Recovery & Restoration costs",
    "Business Interruption costs",
    "Direct Loss of Funds costs",
    "Fines",
    "Legal and Defence costs",
    "Financial Fraud",
    "Physical Damage Costs",
    "Indirect Losses",
)

# IT impact-driver ID → Balbix major category (must match crq.impact.catalogue).
IT_DRIVER_TO_COMPONENT = {
    "NOTIFICATION": "Incident & response costs",
    "CREDIT_MONITORING": "Incident & response costs",
    "CARD_REPLACEMENT": "Incident & response costs",
    "IR_FORENSICS": "Incident & response costs",
    "PUBLIC_RELATIONS": "Incident & response costs",
    "EMPLOYEE_TRAINING": "Incident & response costs",
    "EXTERNAL_RESPONSE": "Incident & response costs",
    "EXTORTION": "Data Recovery & Restoration costs",
    "RESTORATION": "Data Recovery & Restoration costs",
    "BUSINESS_INTERRUPTION": "Business Interruption costs",
    "FRAUD_NET_RECOVERY": "Direct Loss of Funds costs",
    "REGULATORY": "Fines",
    "LEGAL_RESPONSE": "Legal and Defence costs",
    "CONSUMER_SETTLEMENT": "Legal and Defence costs",
    "FRAUD_REIMBURSEMENT": "Financial Fraud",
    "ENDPOINT_RECOVERY": "Physical Damage Costs",
    "SERVER_RECOVERY": "Physical Damage Costs",
    "POST_EVENT_UPLIFT": "Indirect Losses",
    "CUSTOMER_ATTRITION": "Indirect Losses",
}

# Deprecated: Loss blocks are control channels, not economic categories.
# Kept only for diagnostic sensitivity scaling; do not use for Business Impact labels.
IT_BLOCK_TO_COMPONENT = {
    "Duration": "Control channel: Duration",
    "Exposure": "Control channel: Exposure",
    "Direct": "Control channel: Direct",
}

# OT driver category / name heuristics → taxonomy.
OT_CATEGORY_TO_COMPONENT = {
    "Business interruption": "Business interruption",
    "BI": "Business interruption",
    "Additional operating": "Additional operating expense",
    "Incident response": "Incident response",
    "Restoration": "Restoration/rebuild",
    "Rebuild": "Restoration/rebuild",
    "Physical": "Physical damage",
    "Safety": "Safety/bodily injury",
    "Environmental": "Environmental remediation",
    "Third-party": "Third-party liability",
    "Liability": "Third-party liability",
    "Regulatory": "Regulatory/legal costs",
    "Legal": "Regulatory/legal costs",
}


def map_ot_driver_to_component(category: str | None, name: str | None) -> str:
    text = f"{category or ''} {name or ''}".strip()
    for key, label in OT_CATEGORY_TO_COMPONENT.items():
        if key.lower() in text.lower():
            return label
    return "Other sector-specific costs"


def component_rows_from_trials(
    total_annual: np.ndarray,
    component_annuals: dict[str, np.ndarray],
) -> list[dict[str, Any]]:
    """Build applicable component contribution rows; omit empty components."""
    total_aal = float(np.asarray(total_annual).mean())
    t95 = tvar_tail_contributions(total_annual, component_annuals, 0.95)
    t99 = tvar_tail_contributions(total_annual, component_annuals, 0.99)
    tvar99 = annual_aggregate_metrics(total_annual)["TVaR99"]
    rows = []
    for name, arr in component_annuals.items():
        aal = float(np.asarray(arr).mean())
        if aal <= 0 and float(np.asarray(arr).max()) <= 0:
            continue
        rows.append(
            {
                "name": name,
                "aal": aal,
                "contrib_tvar95": t95.get(name, 0.0),
                "contrib_tvar99": t99.get(name, 0.0),
                "pct_aal": (aal / total_aal) if total_aal else None,
                "pct_tvar99": (t99.get(name, 0.0) / tvar99) if tvar99 else None,
            }
        )
    rows.sort(key=lambda r: -(r["aal"] or 0))
    return rows


def leading_tvar99_component(loss_components: list[dict[str, Any]] | None) -> dict[str, Any] | None:
    """Return the component with the largest portfolio TVaR 99 contribution (not AAL)."""
    rows = [
        r for r in (loss_components or [])
        if r.get("name") and r.get("contrib_tvar99") is not None
    ]
    if not rows:
        return None
    top = max(rows, key=lambda r: float(r.get("contrib_tvar99") or 0.0))
    amt = float(top.get("contrib_tvar99") or 0.0)
    pct = top.get("pct_tvar99")
    label = f"{top['name']} — ${amt:,.0f}"
    if pct is not None:
        label += f" ({100.0 * float(pct):.1f}% of TVaR 99)"
    return {
        "name": top["name"],
        "contrib_tvar99": amt,
        "pct_tvar99": None if pct is None else float(pct),
        "label": label,
    }


def portfolio_tail_reconcile(
    contributions: dict[str, float] | list[dict[str, Any]],
    aggregate_tvar: float,
    *,
    value_key: str = "contrib_tvar99",
    rtol: float = 1e-6,
    atol: float = 1.0,
) -> dict[str, Any]:
    """Check that portfolio-tail contributions sum to aggregate TVaR within tolerance."""
    if isinstance(contributions, dict):
        total = float(sum(float(v) for v in contributions.values()))
    else:
        total = float(sum(float(r.get(value_key) or 0.0) for r in contributions))
    agg = float(aggregate_tvar)
    diff = total - agg
    ok = abs(diff) <= max(atol, abs(agg) * rtol)
    return {"sum": total, "aggregate": agg, "diff": diff, "ok": ok}


def treatment_cost_metrics(
    *,
    aal_reduction: float | None,
    one_off_cost: float | None,
    annual_cost: float | None,
    evaluation_years: float | None,
) -> dict[str, Any]:
    """Optional BCR / payback. Missing costs → Cost not provided."""
    if one_off_cost is None and annual_cost is None:
        return {
            "one_off_cost": None,
            "annual_cost": None,
            "evaluation_years": evaluation_years,
            "annual_risk_reduction": aal_reduction,
            "net_benefit": None,
            "benefit_cost_ratio": None,
            "payback_years": None,
            "cost_status": "Cost not provided",
        }
    years = float(evaluation_years) if evaluation_years not in (None, "") else 1.0
    years = max(years, 1e-9)
    one = float(one_off_cost or 0.0)
    ann = float(annual_cost or 0.0)
    total_cost = one + ann * years
    reduction = float(aal_reduction or 0.0)
    total_benefit = reduction * years
    net = total_benefit - total_cost
    bcr = (total_benefit / total_cost) if total_cost > 0 else None
    payback = None
    if reduction > 0 and (one + ann) > 0:
        # Simple undiscounted payback against annual net of recurring cost.
        net_annual = reduction - ann
        payback = (one / net_annual) if net_annual > 0 else None
    return {
        "one_off_cost": one_off_cost,
        "annual_cost": annual_cost,
        "evaluation_years": years,
        "annual_risk_reduction": reduction,
        "net_benefit": net,
        "benefit_cost_ratio": bcr,
        "payback_years": payback,
        "cost_status": "Cost provided",
    }


def package_maturity_overrides(
    controls: dict,
    *,
    package: str,
    levels: list[str],
    effective_level,
    next_level,
    whatifs: list | None = None,
) -> dict[str, str]:
    """Build multi-control maturity overrides for named packages."""
    if package == "Foundation":
        return {cid: "Developing" for cid in controls}
    # Target = full ladder top (Optimised). Mapping Target→Managed left Target identical to
    # typical OT baselines already at Managed, so Current vs Target showed zero change.
    if package in ("Target", "Target/Optimised", "Optimised"):
        return {cid: "Optimised" for cid in controls}
    if package == "Priority":
        ranked = [x for x in (whatifs or []) if x.get("mapped") and (x.get("whatif") or x.get("next")) != x.get("current")]
        return {x["cid"]: (x.get("whatif") or x.get("next")) for x in ranked[:8]}
    if package == "User-defined":
        out = {}
        for cid, c in controls.items():
            cur = effective_level(c)
            out[cid] = "Managed" if cur in ("Absent", "Initial", "Developing", "Not Assessed") else cur
        return out
    return {}


def metric_bundle_from_sim(sim: dict, baseline_metrics: dict, event_freq: float, freq_base: float) -> dict:
    """Fill residual/baseline five-metric what-if fields from a simulation result."""
    m = sim["metrics"]
    out = {
        "aal": m["AAL"],
        "baseline": baseline_metrics["AAL"],
        "reduction": baseline_metrics["AAL"] - m["AAL"],
        "pct": (baseline_metrics["AAL"] - m["AAL"]) / baseline_metrics["AAL"] if baseline_metrics["AAL"] else 0.0,
        "event_freq": event_freq,
        "freq_base": freq_base,
        "freq_change": freq_base - event_freq,
        "var95": m["VaR95"],
        "var99": m["VaR99"],
        "tvar95": m["TVaR95"],
        "tvar99": m["TVaR99"],
        "var95_base": baseline_metrics["VaR95"],
        "var99_base": baseline_metrics["VaR99"],
        "tvar95_base": baseline_metrics["TVaR95"],
        "tvar99_base": baseline_metrics["TVaR99"],
        "var95_change": baseline_metrics["VaR95"] - m["VaR95"],
        "var99_change": baseline_metrics["VaR99"] - m["VaR99"],
        "tvar95_change": baseline_metrics["TVaR95"] - m["TVaR95"],
        "tvar99_change": baseline_metrics["TVaR99"] - m["TVaR99"],
        "var95_pct": (baseline_metrics["VaR95"] - m["VaR95"]) / baseline_metrics["VaR95"] if baseline_metrics["VaR95"] else None,
        "tvar95_pct": (baseline_metrics["TVaR95"] - m["TVaR95"]) / baseline_metrics["TVaR95"] if baseline_metrics["TVaR95"] else None,
        "var99_pct": (baseline_metrics["VaR99"] - m["VaR99"]) / baseline_metrics["VaR99"] if baseline_metrics["VaR99"] else None,
        "tvar99_pct": (baseline_metrics["TVaR99"] - m["TVaR99"]) / baseline_metrics["TVaR99"] if baseline_metrics["TVaR99"] else None,
    }
    return out
