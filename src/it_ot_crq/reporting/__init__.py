"""Seven presentation views for the combined IT/OT CRQ workbook."""

from __future__ import annotations

REPORTING_SHEETS = (
    "01 Executive Risk Story",
    "02 Risk Formation",
    "03 Scenario Analysis",
    "04 Business Impact",
    "05 Risk Treatment",
    "06 Appetite & Insurance",
    "07 Uncertainty & Evidence",
)

# Legacy operator sheets retained but no longer the primary suite.
LEGACY_DASHBOARD_SHEETS = (
    "00 Dashboard",
    "00 Risk Drivers",
    "00 Loss Analysis",
    "00 What-If",
    "00 Risk Transfer",
)

APPETITE_INPUT_LABELS = (
    ("ANNUAL_LOSS_TOLERANCE", "Annual aggregate loss tolerance ($)"),
    ("MAX_ACCEPTABLE_EVENT_PROBABILITY", "Max acceptable annual event probability"),
    ("MAX_ACCEPTABLE_TVAR_95", "Max acceptable TVaR 95 ($)"),
    ("MAX_ACCEPTABLE_TVAR_99", "Max acceptable TVaR 99 ($)"),
    ("MAX_ACCEPTABLE_DOWNTIME_DAYS", "Max acceptable downtime P95 (days)"),
)

PACKAGE_NAMES = ("Foundation", "Priority", "Target", "User-defined")
