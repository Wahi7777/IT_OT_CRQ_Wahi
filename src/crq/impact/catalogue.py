"""Unified Balbix impact-driver catalogue (version-controlled).

Domain relevance is informational only. Sector packs enable drivers and set
scenario applicability / calibration. Facility workbooks supply exposures.
"""

from __future__ import annotations

from typing import Any

CATALOGUE_VERSION = "1.0.0"

# Balbix major cost categories — reporting roll-up only (not Cost Types).
BALBIX_CATEGORIES = (
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

# Control-channel blocks used by IT/OT path factors (not reporting categories).
CONTROL_BLOCKS = ("Duration", "Exposure", "Direct")

# Stable IDs match existing Balbix-aligned pack driver IDs. Do not invent IDs
# outside the Balbix Breach Impact Model without an explicit gap review.
DRIVERS: dict[str, dict[str, Any]] = {
    "NOTIFICATION": {
        "name": "Notification costs",
        "balbix_name": "Notification costs",
        "category": "Incident & response costs",
        "formula_type": "records_x_share_x_unit",
        "required_inputs": ("SENSITIVE_RECORDS", "AFFECTED_RECORD_SHARE", "NOTIFICATION_PER_RECORD"),
        "distribution": "p50_p99",
        "domain_relevance": ("IT", "OT"),
        "default_applicability": "Informational; pack selects",
        "description": "Cost to notify affected customers or data subjects after a breach.",
        "exclusions": "Credit monitoring, legal defence, regulatory fines.",
        "evidence_requirements": "Unit notification cost and affected-record share with source grade.",
    },
    "CREDIT_MONITORING": {
        "name": "Credit monitoring costs",
        "balbix_name": "Credit monitoring costs",
        "category": "Incident & response costs",
        "formula_type": "records_x_share_x_takeup_x_unit",
        "required_inputs": ("SENSITIVE_RECORDS", "AFFECTED_RECORD_SHARE", "MONITORING_TAKEUP", "CREDIT_MONITORING_PER_RECORD"),
        "distribution": "p50_p99",
        "domain_relevance": ("IT",),
        "default_applicability": "Informational; pack selects",
        "description": "Credit-monitoring offers for participating affected records.",
        "exclusions": "Notification postage/portal costs; fraud reimbursement.",
        "evidence_requirements": "Per-record monitoring cost and take-up rate.",
    },
    "CARD_REPLACEMENT": {
        "name": "Card replacement costs",
        "balbix_name": "Card replacement costs",
        "category": "Incident & response costs",
        "formula_type": "customers_x_share_x_unit",
        "required_inputs": ("CUSTOMERS", "AFFECTED_CUSTOMER_SHARE", "CARD_REPLACEMENT_UNIT"),
        "distribution": "p50_p99",
        "domain_relevance": ("IT",),
        "default_applicability": "Informational; pack selects",
        "description": "Physical or virtual payment-card reissue after compromise.",
        "exclusions": "Fraud reimbursement of diverted funds.",
        "evidence_requirements": "Unit card cost and affected-customer share.",
    },
    "IR_FORENSICS": {
        "name": "Forensic investigation costs",
        "balbix_name": "Forensic investigation costs",
        "category": "Incident & response costs",
        "formula_type": "daily_rate_x_duration",
        "required_inputs": ("IR_DAYS", "FORENSIC_DAILY"),
        "distribution": "p50_p99",
        "domain_relevance": ("IT", "OT"),
        "default_applicability": "Informational; pack selects",
        "description": "Digital / forensic investigation team costs during response.",
        "exclusions": "External cyber retainer beyond forensics; legal defence.",
        "evidence_requirements": "Daily forensic rate and investigation duration.",
    },
    "PUBLIC_RELATIONS": {
        "name": "Public relations cost",
        "balbix_name": "Public relations cost",
        "category": "Incident & response costs",
        "formula_type": "daily_rate_x_duration",
        "required_inputs": ("PR_DAYS", "PR_DAILY"),
        "distribution": "p50_p99",
        "domain_relevance": ("IT", "OT"),
        "default_applicability": "Informational; pack selects",
        "description": "Crisis communications / PR spend during the incident window.",
        "exclusions": "Legal defence and regulatory fines.",
        "evidence_requirements": "Daily PR rate and communications duration.",
    },
    "EMPLOYEE_TRAINING": {
        "name": "Average employee training costs",
        "balbix_name": "Average employee training costs",
        "category": "Incident & response costs",
        "formula_type": "employees_x_unit",
        "required_inputs": ("EMPLOYEES", "TRAINING_PER_EMPLOYEE"),
        "distribution": "p50_p99",
        "domain_relevance": ("IT",),
        "default_applicability": "Informational; pack selects",
        "description": "Post-breach awareness / training for employees.",
        "exclusions": "Ongoing BAU security training budgets.",
        "evidence_requirements": "Per-employee training cost and headcount.",
    },
    "EXTERNAL_RESPONSE": {
        "name": "External cyber experts cost",
        "balbix_name": "External cyber experts cost",
        "category": "Incident & response costs",
        "formula_type": "daily_rate_x_duration",
        "required_inputs": ("CYBER_DAYS", "EXTERNAL_CYBER_DAILY"),
        "distribution": "p50_p99",
        "domain_relevance": ("IT", "OT"),
        "default_applicability": "Informational; pack selects",
        "description": "External incident-response / cyber specialist support.",
        "exclusions": "Forensic-only day rates when separately modelled; OEM plant engineers.",
        "evidence_requirements": "Daily external cyber rate and response duration.",
    },
    "EXTORTION": {
        "name": "Ransom payment costs",
        "balbix_name": "Ransom payment costs",
        "category": "Data Recovery & Restoration costs",
        "formula_type": "direct_amount",
        "required_inputs": ("EXTORTION_DIRECT",),
        "distribution": "p50_p99",
        "domain_relevance": ("IT", "OT"),
        "default_applicability": "Informational; pack selects",
        "description": "Extortion or ransom payment amounts.",
        "exclusions": "IR retainers and restoration labour.",
        "evidence_requirements": "Direct amount distribution with payment policy evidence.",
    },
    "RESTORATION": {
        "name": "Data restoration costs",
        "balbix_name": "Data restoration costs",
        "category": "Data Recovery & Restoration costs",
        "formula_type": "daily_rate_x_duration",
        "required_inputs": ("RESTORE_DAYS", "RESTORATION_DAILY"),
        "distribution": "p50_p99",
        "domain_relevance": ("IT", "OT"),
        "default_applicability": "Informational; pack selects",
        "description": "Data or configuration restoration labour.",
        "exclusions": "Major capital equipment replacement; OEM engineering beyond restoration.",
        "evidence_requirements": "Daily restoration rate and restore duration.",
    },
    "BUSINESS_INTERRUPTION": {
        "name": "Business downtime costs",
        "balbix_name": "Business downtime costs",
        "category": "Business Interruption costs",
        "formula_type": "revenue_per_day_x_duration_x_share_x_margin",
        "required_inputs": ("ANNUAL_REVENUE_AT_RISK", "DOWNTIME_DAYS", "AFFECTED_SERVICE_SHARE", "BI_LOSS_FACTOR"),
        "distribution": "p50_p99",
        "domain_relevance": ("IT", "OT"),
        "default_applicability": "Informational; pack selects",
        "description": "Lost contribution / margin from service or production downtime.",
        "exclusions": "Increased cost of working, safety, environmental, physical damage.",
        "evidence_requirements": "Revenue, operating days basis, downtime, affected share, margin/BI factor.",
    },
    "FRAUD_NET_RECOVERY": {
        "name": "Monetary theft / funds at risk (net of recovery)",
        "balbix_name": "Monetary Theft",
        "category": "Direct Loss of Funds costs",
        "formula_type": "payment_value_x_compromised_x_unrecovered",
        "required_inputs": ("ANNUAL_PAYMENT_VALUE", "PAYMENT_FLOW_DAYS", "DIVERTED_SHARE", "FRAUD_RECOVERY_RATE"),
        "distribution": "p50_p99",
        "domain_relevance": ("IT",),
        "default_applicability": "Informational; pack selects",
        "description": "Direct monetary diversion / theft net of recovery.",
        "exclusions": "Incident response labour; must not be classified as IR or BI.",
        "evidence_requirements": "Payment flow at risk, diversion share, recovery rate.",
    },
    "REGULATORY": {
        "name": "Regulatory fine costs",
        "balbix_name": "PCI/PHI/PII/GDPR/Other regulatory fine",
        "category": "Fines",
        "formula_type": "revenue_x_fine_percentage",
        "required_inputs": ("ANNUAL_REVENUE_AT_RISK", "REGULATORY_REVENUE_SHARE"),
        "distribution": "p50_p99",
        "domain_relevance": ("IT", "OT"),
        "default_applicability": "Informational; pack selects",
        "description": "Regulatory fines expressed as a share of revenue (or equivalent).",
        "exclusions": "Legal defence and consumer settlements.",
        "evidence_requirements": "Fine percentage / amount with regulatory basis.",
    },
    "LEGAL_RESPONSE": {
        "name": "Legal guidance & defence costs",
        "balbix_name": "Legal guidance & defence costs",
        "category": "Legal and Defence costs",
        "formula_type": "daily_rate_x_duration",
        "required_inputs": ("LEGAL_DAYS", "LEGAL_DAILY"),
        "distribution": "p50_p99",
        "domain_relevance": ("IT", "OT"),
        "default_applicability": "Informational; pack selects",
        "description": "External legal guidance and defence during / after the event.",
        "exclusions": "Regulatory fines and consumer settlements.",
        "evidence_requirements": "Daily legal rate and engagement duration.",
    },
    "CONSUMER_SETTLEMENT": {
        "name": "Consumer settlement costs",
        "balbix_name": "PCI/PHI/PII Consumer Settlement",
        "category": "Legal and Defence costs",
        "formula_type": "records_x_share_x_unit",
        "required_inputs": ("SENSITIVE_RECORDS", "SETTLEMENT_AFFECTED_SHARE", "SETTLEMENT_PER_RECORD"),
        "distribution": "p50_p99",
        "domain_relevance": ("IT",),
        "default_applicability": "Informational; pack selects",
        "description": "Consumer / class settlements per affected record.",
        "exclusions": "Regulatory fines; notification.",
        "evidence_requirements": "Settlement cost per record and affected share.",
    },
    "FRAUD_REIMBURSEMENT": {
        "name": "Fraud reimbursement costs (customer)",
        "balbix_name": "Fraud reimbursement costs (customer)",
        "category": "Financial Fraud",
        "formula_type": "direct_amount",
        "required_inputs": ("FRAUD_REIMBURSEMENT_DIRECT",),
        "distribution": "p50_p99",
        "domain_relevance": ("IT",),
        "default_applicability": "Informational; pack selects",
        "description": "Customer fraud reimbursement distinct from organisational fund diversion.",
        "exclusions": "Monetary theft already counted in FRAUD_NET_RECOVERY.",
        "evidence_requirements": "Direct reimbursement distribution.",
    },
    "ENDPOINT_RECOVERY": {
        "name": "Endpoint replacement costs",
        "balbix_name": "Endpoint replacement costs",
        "category": "Physical Damage Costs",
        "formula_type": "asset_count_x_share_x_unit",
        "required_inputs": ("CRITICAL_ENDPOINTS", "AFFECTED_ENDPOINT_SHARE", "ENDPOINT_REPAIR"),
        "distribution": "p50_p99",
        "domain_relevance": ("IT", "OT"),
        "default_applicability": "Informational; pack selects",
        "description": "Repair or replacement of compromised endpoints.",
        "exclusions": "Major OT equipment capital replacement.",
        "evidence_requirements": "Endpoint count, affected share, unit replacement cost.",
    },
    "SERVER_RECOVERY": {
        "name": "Server replacement costs",
        "balbix_name": "Server replacement costs",
        "category": "Physical Damage Costs",
        "formula_type": "asset_count_x_share_x_unit",
        "required_inputs": ("CRITICAL_SERVERS", "AFFECTED_SERVER_SHARE", "SERVER_REPAIR"),
        "distribution": "p50_p99",
        "domain_relevance": ("IT", "OT"),
        "default_applicability": "Informational; pack selects",
        "description": "Repair or replacement of compromised servers.",
        "exclusions": "Major OT equipment capital replacement.",
        "evidence_requirements": "Server count, affected share, unit replacement cost.",
    },
    "POST_EVENT_UPLIFT": {
        "name": "Cyber security investment costs",
        "balbix_name": "Cyber security investment costs",
        "category": "Indirect Losses",
        "formula_type": "revenue_x_fine_percentage",
        "required_inputs": ("ANNUAL_REVENUE_AT_RISK", "POST_EVENT_REVENUE_SHARE"),
        "distribution": "p50_p99",
        "domain_relevance": ("IT", "OT"),
        "default_applicability": "Informational; pack selects",
        "description": "Post-event security improvement / uplift expenditure.",
        "exclusions": "BAU security run-rate; IR labour already counted.",
        "evidence_requirements": "Uplift share of revenue or direct programme cost.",
    },
    "CUSTOMER_ATTRITION": {
        "name": "Customer churn costs",
        "balbix_name": "Customer churn costs",
        "category": "Indirect Losses",
        "formula_type": "customers_x_share_x_churn_x_value",
        "required_inputs": ("ANNUAL_REVENUE_AT_RISK", "CHURN_REVENUE_SHARE"),
        "distribution": "p50_p99",
        "domain_relevance": ("IT",),
        "default_applicability": "Informational; pack selects",
        "description": "Lost margin from post-event customer attrition.",
        "exclusions": "Notification and credit monitoring.",
        "evidence_requirements": "Churn share and value/margin basis.",
    },
}

# OT pack driver IDs → Balbix catalogue ID when an analogue exists.
# Drivers listed in OT_BALBIX_GAPS cannot be represented without inventing IDs.
OT_TO_BALBIX: dict[str, str] = {
    "IR-01": "IR_FORENSICS",
    "IR-02": "EXTERNAL_RESPONSE",
    "IR-03": "PUBLIC_RELATIONS",
    "RC-01": "RESTORATION",
    "RC-03": "RESTORATION",
    "BI-01": "BUSINESS_INTERRUPTION",
    "EX-01": "EXTORTION",
    "LG-01": "LEGAL_RESPONSE",
    "LG-02": "REGULATORY",
    "PD-01": "ENDPOINT_RECOVERY",
    "PD-02": "SERVER_RECOVERY",
    "IN-01": "POST_EVENT_UPLIFT",
}

OT_BALBIX_GAPS: dict[str, str] = {
    "RC-02": "OEM / specialist engineering support — not a Balbix catalogue driver",
    "OP-01": "Increased cost of working / production support — flag for Balbix review",
    "OP-02": "Alternative supply / contractual penalties — not in Balbix catalogue",
    "SF-01": "Safety / bodily-injury response — not in Balbix catalogue",
    "EN-01": "Environmental remediation — not in Balbix catalogue",
    "PD-03": "Major equipment / physical plant damage — not in Balbix catalogue",
}


def driver_category(driver_id: str) -> str:
    spec = DRIVERS.get(driver_id)
    if not spec:
        return "Indirect Losses"
    return str(spec["category"])


def driver_name(driver_id: str) -> str:
    spec = DRIVERS.get(driver_id)
    if not spec:
        return driver_id
    return str(spec["name"])


def catalogue_rows() -> list[dict[str, Any]]:
    rows = []
    for did, spec in DRIVERS.items():
        rows.append({"driver_id": did, **spec, "catalogue_version": CATALOGUE_VERSION})
    return rows


def assert_pack_drivers_are_balbix(driver_ids: set[str] | list[str]) -> list[str]:
    """Return unknown (non-catalogue) IDs. Packs must not invent drivers."""
    return sorted(did for did in driver_ids if did not in DRIVERS)
