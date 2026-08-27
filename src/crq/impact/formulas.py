"""Generic impact formula library (sector packs supply calibration, not new engines)."""

from __future__ import annotations

from typing import Any, Callable


def unit_count_x_share_x_unit(count: float, share: float, unit_cost: float) -> float:
    return max(float(count), 0.0) * max(float(share), 0.0) * max(float(unit_cost), 0.0)


def daily_rate_x_duration(daily_rate: float, duration: float) -> float:
    return max(float(daily_rate), 0.0) * max(float(duration), 0.0)


def revenue_per_day_x_duration_x_share_x_margin(
    annual_revenue: float,
    duration_days: float,
    affected_share: float,
    margin_or_bi: float,
    *,
    operating_days: float = 365.0,
) -> float:
    days = max(float(operating_days), 1e-12)
    return (
        max(float(annual_revenue), 0.0)
        / days
        * max(float(duration_days), 0.0)
        * max(float(affected_share), 0.0)
        * max(float(margin_or_bi), 0.0)
    )


def daily_production_x_duration_x_capacity(
    daily_production_value: float,
    duration: float,
    affected_capacity: float,
) -> float:
    return (
        max(float(daily_production_value), 0.0)
        * max(float(duration), 0.0)
        * max(float(affected_capacity), 0.0)
    )


def asset_count_x_share_x_unit(count: float, share: float, replacement_cost: float) -> float:
    return unit_count_x_share_x_unit(count, share, replacement_cost)


def revenue_x_fine_percentage(revenue: float, fine_percentage: float) -> float:
    return max(float(revenue), 0.0) * max(float(fine_percentage), 0.0)


def records_x_share_x_unit(records: float, share: float, cost_per_record: float) -> float:
    return unit_count_x_share_x_unit(records, share, cost_per_record)


def records_x_share_x_takeup_x_unit(
    records: float, share: float, takeup: float, cost_per_record: float
) -> float:
    return (
        max(float(records), 0.0)
        * max(float(share), 0.0)
        * max(float(takeup), 0.0)
        * max(float(cost_per_record), 0.0)
    )


def customers_x_share_x_churn_x_value(
    customers_or_revenue: float,
    affected_share: float,
    churn_percentage: float,
    value_per_customer: float = 1.0,
) -> float:
    """When value_per_customer is 1 and customers_or_revenue is revenue, this is revenue×share×churn."""
    return (
        max(float(customers_or_revenue), 0.0)
        * max(float(affected_share), 0.0)
        * max(float(churn_percentage), 0.0)
        * max(float(value_per_customer), 0.0)
    )


def payment_value_x_compromised_x_unrecovered(
    annual_payment_value: float,
    payment_flow_days: float,
    diverted_share: float,
    unrecovered_share: float,
    *,
    year_days: float = 365.0,
) -> float:
    return (
        max(float(annual_payment_value), 0.0)
        / max(float(year_days), 1e-12)
        * max(float(payment_flow_days), 0.0)
        * max(float(diverted_share), 0.0)
        * max(float(unrecovered_share), 0.0)
    )


def direct_amount(amount: float) -> float:
    return max(float(amount), 0.0)


def employees_x_unit(employees: float, unit_cost: float) -> float:
    return max(float(employees), 0.0) * max(float(unit_cost), 0.0)


FORMULA_REGISTRY: dict[str, Callable[..., float]] = {
    "unit_count_x_share_x_unit": unit_count_x_share_x_unit,
    "daily_rate_x_duration": daily_rate_x_duration,
    "revenue_per_day_x_duration_x_share_x_margin": revenue_per_day_x_duration_x_share_x_margin,
    "daily_production_x_duration_x_capacity": daily_production_x_duration_x_capacity,
    "asset_count_x_share_x_unit": asset_count_x_share_x_unit,
    "revenue_x_fine_percentage": revenue_x_fine_percentage,
    "records_x_share_x_unit": records_x_share_x_unit,
    "records_x_share_x_takeup_x_unit": records_x_share_x_takeup_x_unit,
    "customers_x_share_x_churn_x_value": customers_x_share_x_churn_x_value,
    "customers_x_share_x_unit": unit_count_x_share_x_unit,
    "payment_value_x_compromised_x_unrecovered": payment_value_x_compromised_x_unrecovered,
    "direct_amount": direct_amount,
    "employees_x_unit": employees_x_unit,
}


def evaluate(formula_type: str, **kwargs: Any) -> float:
    if formula_type not in FORMULA_REGISTRY:
        raise ValueError(f"Unsupported impact formula type {formula_type!r}")
    return float(FORMULA_REGISTRY[formula_type](**kwargs))
