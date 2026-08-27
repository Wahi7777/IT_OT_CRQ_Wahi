"""Trial-level insurance programme application on annual aggregate losses.

Risk-financing analysis only — not insurance pricing.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from crq.metrics import annual_aggregate_metrics


@dataclass
class InsuranceLayer:
    name: str
    attachment: float
    limit: float
    coinsurance: float = 1.0  # share paid by insurer in (0, 1]


@dataclass
class InsuranceProgramme:
    retention: float = 0.0
    layers: list[InsuranceLayer] = field(default_factory=list)
    aggregate_programme_limit: float | None = None

    def active(self) -> bool:
        return bool(self.layers) or float(self.retention or 0) > 0 or (
            self.aggregate_programme_limit is not None and self.aggregate_programme_limit > 0
        )


def parse_programme(raw: dict | None) -> InsuranceProgramme:
    """Parse programme from workbook/engine dict. Missing fields → inactive layer."""
    raw = raw or {}
    retention = float(raw.get("INSURANCE_RETENTION") or raw.get("retention") or 0.0)
    layers: list[InsuranceLayer] = []
    for layer in raw.get("layers") or []:
        att = float(layer.get("attachment") or 0.0)
        lim = float(layer.get("limit") or 0.0)
        if lim <= 0:
            continue
        coin = layer.get("coinsurance")
        coin_f = 1.0 if coin in (None, "") else float(coin)
        coin_f = min(max(coin_f, 0.0), 1.0)
        layers.append(
            InsuranceLayer(
                name=str(layer.get("name") or f"Layer {len(layers) + 1}"),
                attachment=att,
                limit=lim,
                coinsurance=coin_f,
            )
        )
    # Convenience: primary limit alone
    primary = raw.get("PRIMARY_LIMIT") or raw.get("primary_limit")
    if primary not in (None, "") and not layers:
        lim = float(primary)
        if lim > 0:
            layers.append(InsuranceLayer(name="Primary", attachment=retention, limit=lim, coinsurance=1.0))
    agg = raw.get("AGGREGATE_PROGRAMME_LIMIT") or raw.get("aggregate_programme_limit")
    agg_f = None if agg in (None, "") else float(agg)
    return InsuranceProgramme(retention=retention, layers=layers, aggregate_programme_limit=agg_f)


def apply_programme(ground_up: np.ndarray, programme: InsuranceProgramme) -> dict:
    """Apply retention + excess layers to each annual aggregate trial."""
    gu = np.asarray(ground_up, dtype=float)
    n = gu.size
    retained = np.minimum(gu, float(programme.retention or 0.0))
    remaining = np.maximum(gu - retained, 0.0)
    layer_pay = []
    attach_flags = []
    exhaust_flags = []
    expected_layer = []
    for layer in programme.layers:
        # Layer covers losses above attachment, up to limit, after ground-up retention structure.
        # Attachment is absolute from ground-up zero.
        above_attach = np.maximum(gu - layer.attachment, 0.0)
        raw_recover = np.minimum(above_attach, layer.limit) * layer.coinsurance
        # Cannot recover more than remaining uninsured above retention already accounted;
        # use ground-up layering: each layer independently defined by attachment/limit.
        recover = raw_recover
        layer_pay.append(recover)
        attach_flags.append(float(np.mean(gu > layer.attachment)))
        exhaust_flags.append(float(np.mean(above_attach >= layer.limit - 1e-12)))
        expected_layer.append(float(recover.mean()))

    if layer_pay:
        insured = np.sum(np.vstack(layer_pay), axis=0)
    else:
        insured = np.zeros(n)

    if programme.aggregate_programme_limit is not None and programme.aggregate_programme_limit > 0:
        insured = np.minimum(insured, float(programme.aggregate_programme_limit))

    # Residual = ground-up − insured recovery (includes retention and uncovered excess)
    residual = np.maximum(gu - insured, 0.0)
    uninsured_above = np.maximum(gu - float(programme.retention or 0.0) - insured, 0.0)

    # Reconcile: ground-up = residual + insured (by construction when residual = gu - insured)
    recon_ok = bool(np.allclose(gu, residual + insured, rtol=0, atol=1e-6))

    programme_capacity = float(programme.retention or 0.0) + sum(
        layer.limit * layer.coinsurance for layer in programme.layers
    )
    if programme.aggregate_programme_limit is not None and programme.aggregate_programme_limit > 0:
        programme_capacity = min(
            programme_capacity,
            float(programme.retention or 0.0) + float(programme.aggregate_programme_limit),
        )

    metrics_gu = annual_aggregate_metrics(gu)
    metrics_res = annual_aggregate_metrics(residual)

    return {
        "ground_up": gu,
        "retained": retained,
        "insured": insured,
        "residual": residual,
        "uninsured_above_programme": uninsured_above,
        "layer_recoveries": {programme.layers[i].name: layer_pay[i] for i in range(len(programme.layers))},
        "reconcile_ok": recon_ok,
        "metrics_ground_up": metrics_gu,
        "metrics_residual": metrics_res,
        "p_retention_exceeded": float(np.mean(gu > float(programme.retention or 0.0))) if programme.retention else 0.0,
        "p_layer_attaches": {programme.layers[i].name: attach_flags[i] for i in range(len(programme.layers))},
        "p_layer_exhausts": {programme.layers[i].name: exhaust_flags[i] for i in range(len(programme.layers))},
        "expected_loss_to_layer": {programme.layers[i].name: expected_layer[i] for i in range(len(programme.layers))},
        "p_programme_exhaustion": float(np.mean(insured >= programme_capacity - 1e-9)) if programme_capacity > 0 else 0.0,
        "expected_insured_recovery": float(insured.mean()),
        "expected_retained_loss": float(residual.mean()),
        "expected_uninsured_above_programme": float(uninsured_above.mean()),
        "programme": programme,
    }
