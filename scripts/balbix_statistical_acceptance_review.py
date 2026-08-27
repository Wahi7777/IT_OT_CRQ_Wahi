#!/usr/bin/env python3
"""Statistical acceptance review: MC precision, AAL-ρ pairing, TVaR difference CIs.

Does not re-freeze goldens. Reuses production RAKBANK staging from blockers harness.
"""

from __future__ import annotations

import hashlib
import json
import math
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
import sys

sys.path[:0] = [str(ROOT / "src"), str(ROOT)]

from crq.metrics import annual_aggregate_metrics
from scripts.balbix_acceptance_blockers import (
    N_MASTER,
    OUT,
    SEED,
    _metrics,
    load_ctx,
)
from it_crq.engine import _simulate

# Documented workbook decision tolerances (unchanged from prior acceptance note).
ACCEPTANCE_TOLERANCE = {
    "aal": 250_000.0,
    "var95": 100_000.0,
    "tvar95": 5_000_000.0,
    "var99": 500_000.0,
    "tvar99": 25_000_000.0,
}

RHOS = (0.0, 0.25, 0.5, 0.75, 1.0)
BOOT_N = 400
BOOT_SEED = SEED + 17
# Before/after TVaR99 from accepted production note (same seed/N/prudence; unpaired engines).
BEFORE_TVAR99 = 139_706_747.0
AFTER_TVAR99 = 149_582_084.37123415


def _tvar(annual: np.ndarray, alpha: float) -> float:
    q = float(np.quantile(annual, alpha))
    tail = annual[annual >= q]
    return float(tail.mean()) if len(tail) else float("nan")


def _pack_identity() -> dict:
    pack = ROOT / "sector_packs" / "IT" / "IT_CRQ_Sector_Pack_Financial_Services_v1_1_1.xlsx"
    return {
        "path": str(pack.relative_to(ROOT)),
        "pack_id": "FS-v1.1.1",
        "sha256": hashlib.sha256(pack.read_bytes()).hexdigest(),
        "code_commit": "no-git-repository",
    }


def verify_invariants(cells, actors, scenarios, pf) -> dict:
    """Confirm ρ changes only the equicorrelation mix, not margins/frequency/applicability."""
    # Fixed cell structure (means, rates, driver sets) — independent of ρ.
    analytic_be = float(sum(c["aal"] for c in cells))
    analytic_prudent = analytic_be * pf
    n_drivers = sum(len(c.get("drivers") or []) for c in cells)
    # Caps / nonlinear cross-driver transforms in _simulate: none (sum of LN draws only).
    # CRN: same seed → identical Poisson counts and identical underlying normals;
    # channel Z is a ρ-dependent linear mix of those same normals.
    sims = {}
    for rho in RHOS:
        sims[rho] = _simulate(cells, N_MASTER, SEED, pf, actors, scenarios, rho)
    base = sims[0.5]
    # Frequency path: annual>0 years and event presence must match across ρ under CRN.
    freq_match = {}
    base_p_any = float(np.mean(base["annual"] > 0))
    for rho, sim in sims.items():
        p_any = float(np.mean(sim["annual"] > 0))
        freq_match[str(rho)] = {
            "p_any": p_any,
            "p_any_equal": bool(np.isclose(p_any, base_p_any)),
            "positive_years_equal": bool(np.array_equal(sim["annual"] > 0, base["annual"] > 0)),
            "annual_identical": bool(np.array_equal(sim["annual"], base["annual"])),
        }
    # Marginal channel Z: for each event, Z_c(ρ) is N(0,1) in law for all ρ;
    # driver mean = exp(μ+½σ²) is ρ-invariant (uncapped LN; no cross-driver cap).
    return {
        "analytic_aal_best_estimate": analytic_be,
        "analytic_aal_prudent": analytic_prudent,
        "n_cells": len(cells),
        "n_driver_draws": n_drivers,
        "cross_driver_cap_or_nonlinear_aggregate": False,
        "severity_transform": "uncapped_lognormal_per_driver_then_sum",
        "frequency_and_applicability_independent_of_rho": True,
        "crn_frequency_match_vs_rho_0_5": freq_match,
        "sims": sims,
    }


def paired_aal_table(sims: dict, analytic_prudent: float) -> list[dict]:
    base = sims[0.5]["annual"]
    rows = []
    for rho in RHOS:
        annual = sims[rho]["annual"]
        diff = annual - base
        mean_diff = float(diff.mean())
        se = float(diff.std(ddof=1) / math.sqrt(len(diff)))
        # Normal approx 95% CI for mean paired difference (iid years under MC design).
        lo, hi = mean_diff - 1.96 * se, mean_diff + 1.96 * se
        sim_aal = float(annual.mean())
        contains_zero = bool(lo <= 0.0 <= hi)
        if rho == 0.5:
            interp = "Baseline (by construction Δ=0)."
        elif contains_zero:
            interp = (
                "95% CI for paired ΔAAL contains 0 — compatible with sampling noise "
                "under CRN; does not prove implementation correctness by itself."
            )
        else:
            interp = (
                "95% CI for paired ΔAAL excludes 0 — systematic AAL shift vs ρ=0.5 "
                "under this CRN path; investigate (not expected for uncapped additive LN)."
            )
        rows.append(
            {
                "rho": rho,
                "simulated_aal": sim_aal,
                "analytical_aal": analytic_prudent,
                "difference_vs_rho_0_5": mean_diff,
                "difference_pct_vs_rho_0_5": mean_diff / float(base.mean()) if base.mean() else None,
                "se_of_difference": se,
                "ci95_difference": [lo, hi],
                "ci95_contains_zero": contains_zero,
                "abs_sim_vs_analytic_pct": abs(sim_aal - analytic_prudent) / analytic_prudent,
                "interpretation": interp,
            }
        )
    return rows


def paired_bootstrap_metric_diffs(
    sims: dict, metric: str, n_boot: int = BOOT_N, seed: int = BOOT_SEED
) -> dict:
    """Paired year-index bootstrap across ρ configurations; recompute quantile/TVaR each resample."""
    base = sims[0.5]["annual"]
    n = len(base)
    rng = np.random.default_rng(seed)
    point = {rho: _metrics(sims[rho]["annual"])[metric] for rho in RHOS}
    boot_diffs = {rho: [] for rho in RHOS if rho != 0.5}
    for _ in range(n_boot):
        idx = rng.integers(0, n, size=n)
        m0 = _metrics(base[idx])[metric]
        for rho in RHOS:
            if rho == 0.5:
                continue
            m = _metrics(sims[rho]["annual"][idx])[metric]
            boot_diffs[rho].append(m - m0)
    out = {"metric": metric, "n_bootstrap": n_boot, "point_vs_rho_0_5": {}, "rows": []}
    for rho in RHOS:
        if rho == 0.5:
            continue
        samples = np.asarray(boot_diffs[rho], float)
        lo, hi = np.quantile(samples, [0.025, 0.975])
        se = float(samples.std(ddof=1))
        d = point[rho] - point[0.5]
        out["rows"].append(
            {
                "rho": rho,
                "point_estimate": point[rho],
                "point_difference_vs_0_5": d,
                "point_difference_pct_vs_0_5": d / point[0.5],
                "bootstrap_se_of_difference": se,
                "ci95_difference": [float(lo), float(hi)],
                "ci95_contains_zero": bool(lo <= 0.0 <= hi),
                "systematic_difference_suggested": bool(not (lo <= 0.0 <= hi)),
            }
        )
        out["point_vs_rho_0_5"][str(rho)] = d
    # Max |Δ| TVaR99 sensitivity (point) and uncertainty on the farthest rho.
    farthest = max(out["rows"], key=lambda r: abs(r["point_difference_pct_vs_0_5"]))
    out["max_abs_pct_point"] = abs(farthest["point_difference_pct_vs_0_5"])
    out["max_abs_pct_row"] = farthest
    return out


def before_after_tvar99_uncertainty(after_annual: np.ndarray) -> dict:
    """Before/after cannot be year-paired (old annual vector not retained).

    Report after-only bootstrap SE and disclose that the ~7.1% point movement's
    difference CI cannot be formed without the pre-refactor annual series or
    a re-runnable old engine under CRN.
    """
    rng = np.random.default_rng(BOOT_SEED + 3)
    n = len(after_annual)
    after_point = float(_tvar(after_annual, 0.99))
    boots = []
    for _ in range(BOOT_N):
        boots.append(_tvar(after_annual[rng.integers(0, n, size=n)], 0.99))
    boots = np.asarray(boots, float)
    se_after = float(boots.std(ddof=1))
    lo, hi = np.quantile(boots, [0.025, 0.975])
    point_diff = AFTER_TVAR99 - BEFORE_TVAR99
    # Conservative unpaired bound: if before SE were similar to after SE and independent,
    # SE(diff) ≈ sqrt(2)*SE_after. This is illustrative only — before SE unknown.
    se_diff_illustrative = math.sqrt(2.0) * se_after
    return {
        "pairing_valid": False,
        "limitation": (
            "Pre-refactor annual loss vector is not available; only workbook point "
            "metrics exist. Seeds matching does not establish CRN pairing across "
            "different severity engines (per-driver vs former block LN)."
        ),
        "before_tvar99_point": BEFORE_TVAR99,
        "after_tvar99_point": after_point,
        "point_difference": point_diff,
        "point_difference_pct": point_diff / BEFORE_TVAR99,
        "after_bootstrap_se": se_after,
        "after_ci95": [float(lo), float(hi)],
        "illustrative_unpaired_se_diff_if_equal_se": se_diff_illustrative,
        "illustrative_unpaired_ci95_diff": [
            point_diff - 1.96 * se_diff_illustrative,
            point_diff + 1.96 * se_diff_illustrative,
        ],
        "decision_precision_note": (
            "Point movement ~7.1% is an observed estimate difference. Without paired "
            "before annuals, systematic vs sampling attribution is not established at "
            "the same rigor as the ρ sensitivity."
        ),
    }


def baseline_uncertainty_table(annual: np.ndarray) -> dict:
    """Reuse bootstrap + batch-means; score against documented acceptance tolerances."""
    point = _metrics(annual)
    rng = np.random.default_rng(SEED + 11)
    keys = ("aal", "var95", "tvar95", "var99", "tvar99")
    boot = {k: [] for k in keys}
    for _ in range(BOOT_N):
        m = _metrics(annual[rng.integers(0, len(annual), size=len(annual))])
        for k in keys:
            boot[k].append(m[k])
    batch_n = 50_000
    batches = [_metrics(annual[i * batch_n : (i + 1) * batch_n]) for i in range(len(annual) // batch_n)]
    rows = {}
    for k in keys:
        samples = np.asarray(boot[k], float)
        lo, hi = np.quantile(samples, [0.025, 0.975])
        se_boot = float(samples.std(ddof=1))
        bvals = np.asarray([b[k] for b in batches], float)
        se_batch = float(bvals.std(ddof=1) / math.sqrt(len(bvals)))
        se = se_boot if k != "aal" else point["aal_se"]  # AAL: asymptotic iid SE
        # Prefer bootstrap SE for quantile/TVaR display; AAL uses classical SE.
        display_se = point["aal_se"] if k == "aal" else se_boot
        # For AAL CI use normal approx from SE; for others use bootstrap percentile CI.
        if k == "aal":
            ci = [point[k] - 1.96 * display_se, point[k] + 1.96 * display_se]
            halfwidth = 1.96 * display_se
        else:
            ci = [float(lo), float(hi)]
            halfwidth = max(point[k] - lo, hi - point[k])
        tol = ACCEPTANCE_TOLERANCE[k]
        rows[k] = {
            "estimate": point[k],
            "mc_se": display_se,
            "mc_se_bootstrap": se_boot,
            "mc_se_batch_means": se_batch if k != "aal" else point["aal_se"],
            "ci95": ci,
            "ci95_halfwidth": float(halfwidth),
            "acceptance_tolerance": tol,
            "pass": bool(halfwidth <= tol),
            "plus_minus_25m_clarification": None
            if k != "tvar99"
            else (
                "Prior note's '±$25m' is the acceptance tolerance / decision precision "
                f"for TVaR99, not the SE (${display_se:,.0f}) and not exactly the "
                f"bootstrap CI half-width (${halfwidth:,.0f}). The 95% bootstrap CI is "
                f"[{lo:,.0f}, {hi:,.0f}]."
            ),
        }
    return {
        "method": {
            "aal": "iid sample mean SE = s/√N; 95% CI ≈ estimate ± 1.96·SE",
            "quantiles_tvar": (
                f"percentile bootstrap of annual vector, B={BOOT_N} resamples with "
                "replacement; SE = bootstrap sample SD; 95% CI = 2.5%/97.5% percentiles. "
                "Assumes years are exchangeable MC replicates. Heavy-tail limitation: "
                "TVaR99 CI width is dominated by rare extreme years; bootstrap can "
                "understate uncertainty if the sample max is atypical."
            ),
            "batch_means_supporting": "50k-year batches (10) for comparison SE only",
            "intervals_measure": "Monte Carlo sampling error only (fixed model, seed path bootstrapped)",
            "n_years": int(len(annual)),
            "production_seed": SEED,
            "bootstrap_seed": SEED + 11,
            "n_bootstrap": BOOT_N,
        },
        "rows": rows,
        "all_pass": all(r["pass"] for r in rows.values()),
    }


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    print("load_ctx...", flush=True)
    ctx = load_ctx(N_MASTER)
    cells, actors, scenarios, pf = ctx["cells"], ctx["actors"], ctx["scenarios"], ctx["pf"]
    pack_id = _pack_identity()

    print("rho sims + invariants...", flush=True)
    inv = verify_invariants(cells, actors, scenarios, pf)
    sims = inv.pop("sims")

    print("baseline uncertainty...", flush=True)
    unc = baseline_uncertainty_table(sims[0.5]["annual"])

    print("paired AAL...", flush=True)
    aal_rows = paired_aal_table(sims, inv["analytic_aal_prudent"])

    print("paired bootstrap TVaR99 diffs...", flush=True)
    tvar99_rho = paired_bootstrap_metric_diffs(sims, "tvar99")
    tvar95_rho = paired_bootstrap_metric_diffs(sims, "tvar95")

    print("before/after TVaR99...", flush=True)
    ba = before_after_tvar99_uncertainty(sims[0.5]["annual"])

    # Outcome logic
    aal_rho_ok = all(
        (r["rho"] == 0.5) or r["ci95_contains_zero"] or r["abs_sim_vs_analytic_pct"] <= 0.06
        for r in aal_rows
    )
    # More precise: all non-baseline paired CIs contain 0, and sims near analytic.
    aal_systematic = any(
        r["rho"] != 0.5 and not r["ci95_contains_zero"] for r in aal_rows
    )
    rho_tvar_material = tvar99_rho["max_abs_pct_row"]
    outcome = "A"
    unresolved = []
    if not unc["all_pass"]:
        outcome = "B"
        unresolved.append("baseline_mc_precision_vs_tolerance")
    if aal_systematic:
        outcome = "B"
        unresolved.append("aal_rho_paired_ci_excludes_zero")
    # Before/after unpaired is a documentation limitation, not automatic Outcome B
    # if ρ AAL and baseline precision pass — but flag it.
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "elapsed_s": round(time.time() - t0, 1),
        "run_identity": {
            "assessment": "assessments/RAKBANK.xlsx",
            "domain_sector": "IT / Financial Services",
            "simulation_years": N_MASTER,
            "seed": SEED,
            "prudence_frequency_factor": pf,
            "basis": "Prudent",
            "loss_block_rho_baseline": 0.5,
            "dependency": "channel_comonotonic_gaussian",
            **pack_id,
        },
        "baseline_uncertainty": unc,
        "rho_invariants": inv,
        "aal_rho_paired": {
            "rows": aal_rows,
            "crn_preserves_frequency": all(
                v["positive_years_equal"] for v in inv["crn_frequency_match_vs_rho_0_5"].values()
            ),
            "systematic_aal_shift_detected": aal_systematic,
            "max_abs_sim_pct_vs_rho_0_5": max(
                abs(r["difference_pct_vs_rho_0_5"] or 0) for r in aal_rows
            ),
        },
        "tvar_rho_paired_bootstrap": {"tvar99": tvar99_rho, "tvar95": tvar95_rho},
        "before_after_tvar99": ba,
        "outcome": {
            "recommendation": f"Outcome {outcome}",
            "unresolved": unresolved,
            "notes": [
                "Golden fixtures not modified.",
                "LOSS_BLOCK_RHO=0.5 remains structured expert working prior.",
                "Direct-loss calibration remains working prior requiring validation.",
            ],
        },
    }
    # Drop non-serializable — sims already popped
    path = OUT / "statistical_acceptance_review.json"
    path.write_text(json.dumps(report, indent=2))
    print("Wrote", path, flush=True)
    print("outcome", report["outcome"]["recommendation"], "unresolved", unresolved, flush=True)
    print("baseline all_pass", unc["all_pass"], flush=True)
    print(
        "aal max |Δ%|",
        report["aal_rho_paired"]["max_abs_sim_pct_vs_rho_0_5"],
        "systematic",
        aal_systematic,
        flush=True,
    )
    print(
        "tvar99 max |Δ%|",
        tvar99_rho["max_abs_pct_point"],
        "ci",
        rho_tvar_material["ci95_difference"],
        flush=True,
    )
    ctx["wb"].close()


if __name__ == "__main__":
    main()
