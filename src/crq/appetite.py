"""Organisational risk-appetite evaluation (independent of insurance retention)."""

from __future__ import annotations

from typing import Any

APPETITE_INPUT_KEYS = (
    "ANNUAL_LOSS_TOLERANCE",
    "MAX_ACCEPTABLE_EVENT_PROBABILITY",
    "MAX_ACCEPTABLE_TVAR_95",
    "MAX_ACCEPTABLE_TVAR_99",
    "MAX_ACCEPTABLE_DOWNTIME_DAYS",
)

STATUS_WITHIN = "Within tolerance"
STATUS_ABOVE = "Above tolerance"
STATUS_UNSET = "Tolerance not set"


def _optional_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        x = float(value)
    except (TypeError, ValueError):
        return None
    if x != x:  # NaN
        return None
    return x


def parse_appetite_inputs(raw: dict | None) -> dict[str, float | None]:
    """Parse optional appetite inputs. Blank → None (unset). No invented defaults."""
    raw = raw or {}
    return {k: _optional_float(raw.get(k)) for k in APPETITE_INPUT_KEYS}


def evaluate_appetite(
    *,
    appetite: dict[str, float | None],
    aal: float | None = None,
    p_any: float | None = None,
    tvar95: float | None = None,
    tvar99: float | None = None,
    downtime_p95_days: float | None = None,
    annual_losses=None,
) -> dict[str, Any]:
    """Return appetite status and per-threshold breach flags.

    Insurance retention must never be passed here.
    """
    checks: list[tuple[str, bool | None]] = []
    tol = appetite.get("ANNUAL_LOSS_TOLERANCE")
    p_exceed = None
    if tol is not None and annual_losses is not None:
        import numpy as np

        p_exceed = float(np.mean(np.asarray(annual_losses, dtype=float) > tol))
        checks.append(("ANNUAL_LOSS_TOLERANCE", aal is not None and float(aal) > tol))
    elif tol is not None and aal is not None:
        checks.append(("ANNUAL_LOSS_TOLERANCE", float(aal) > tol))

    max_p = appetite.get("MAX_ACCEPTABLE_EVENT_PROBABILITY")
    if max_p is not None and p_any is not None:
        checks.append(("MAX_ACCEPTABLE_EVENT_PROBABILITY", float(p_any) > max_p))

    max_t95 = appetite.get("MAX_ACCEPTABLE_TVAR_95")
    if max_t95 is not None and tvar95 is not None:
        checks.append(("MAX_ACCEPTABLE_TVAR_95", float(tvar95) > max_t95))

    max_t99 = appetite.get("MAX_ACCEPTABLE_TVAR_99")
    if max_t99 is not None and tvar99 is not None:
        checks.append(("MAX_ACCEPTABLE_TVAR_99", float(tvar99) > max_t99))

    max_down = appetite.get("MAX_ACCEPTABLE_DOWNTIME_DAYS")
    if max_down is not None and downtime_p95_days is not None:
        checks.append(("MAX_ACCEPTABLE_DOWNTIME_DAYS", float(downtime_p95_days) > max_down))

    active = [(name, breached) for name, breached in checks if breached is not None]
    if not active:
        status = STATUS_UNSET
    elif any(breached for _, breached in active):
        status = STATUS_ABOVE
    else:
        status = STATUS_WITHIN

    return {
        "appetite_status": status,
        "appetite_inputs": appetite,
        "appetite_breaches": {name: breached for name, breached in active},
        "p_exceed_tolerance": p_exceed if tol is not None else None,
        "annual_loss_tolerance": tol,
    }
