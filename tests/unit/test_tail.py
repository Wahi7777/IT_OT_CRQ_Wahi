"""Independent tail-risk mathematics. Expected values are hand-calculated."""
from __future__ import annotations

import math

import numpy as np
import pytest

from it_crq.engine import _expected_shortfall as it_es
from it_crq.engine import _metrics as it_metrics
from ot_crq.engine import expected_shortfall as ot_es


def hand_es_upper_mass(arr, q):
    """Independent Expected Shortfall: mean of the upper (1-q) probability mass."""
    x = sorted(float(v) for v in arr)
    n = len(x)
    tail_mass = n * (1.0 - q)
    desc = list(reversed(x))
    whole = int(math.floor(tail_mass))
    frac = tail_mass - whole
    total = sum(desc[:whole])
    if frac > 0 and whole < n:
        total += frac * desc[whole]
    return total / tail_mass


def test_sparse_vector_var_zero_es_positive():
    arr = np.array([0.0] * 99 + [100.0])
    # n=100, q=0.95 → tail mass 5 → (100+0+0+0+0)/5 = 20
    assert hand_es_upper_mass(arr, 0.95) == pytest.approx(20.0)
    assert it_es(arr, 0.95) == pytest.approx(20.0)
    assert ot_es(arr, 0.95) == pytest.approx(20.0)
    m = it_metrics(arr)
    assert m["VaR95"] == 0.0
    assert m["TVaR95"] == pytest.approx(20.0)
    assert m["AAL"] == pytest.approx(1.0)


def test_uniform_vector_es_equals_mean_of_top_slice():
    arr = np.arange(1, 101, dtype=float)  # 1..100
    # tail mass 5 → mean of 100,99,98,97,96 = 98
    expected = (100 + 99 + 98 + 97 + 96) / 5
    assert hand_es_upper_mass(arr, 0.95) == pytest.approx(expected)
    assert it_es(arr, 0.95) == pytest.approx(expected)
    assert ot_es(arr, 0.95) == pytest.approx(expected)


def test_fractional_mass():
    arr = np.array([10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0, 100.0])
    # n=10, q=0.95, tail mass=0.5 → ES = largest = 100
    assert hand_es_upper_mass(arr, 0.95) == pytest.approx(100.0)
    assert it_es(arr, 0.95) == pytest.approx(100.0)
    assert ot_es(arr, 0.95) == pytest.approx(100.0)


def test_tvar_not_below_var():
    rng = np.random.default_rng(1)
    arr = rng.lognormal(10, 1.2, 5000)
    m = it_metrics(arr)
    assert m["TVaR95"] >= m["VaR95"]
    assert m["TVaR99"] >= m["VaR99"]
    assert ot_es(arr, 0.95) >= float(np.quantile(arr, 0.95))
    assert ot_es(arr, 0.99) >= float(np.quantile(arr, 0.99))


def test_oep_le_aep_construction():
    aep = np.array([0.0, 10.0, 30.0, 5.0])
    oep = np.array([0.0, 10.0, 20.0, 5.0])  # largest event ≤ annual aggregate
    assert all(o <= a + 1e-12 for o, a in zip(oep, aep))


def test_lec_monotonic_towards_rarer():
    arr = np.array([0.0] * 80 + [10.0, 20.0, 50.0, 80.0, 100.0] * 4)
    rps = [2, 5, 10, 20, 50, 100]
    aep = [float(np.quantile(arr, 1 - 1 / rp, method="higher")) for rp in rps]
    assert all(x <= y for x, y in zip(aep, aep[1:]))
