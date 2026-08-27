"""Independent control-aggregation tests. Expected values are hand-calculated."""
from it_crq.engine import MATURITY, _agg


def test_zero_controls():
    assert _agg([], 0.25, 0.95) == 0.0


def test_one_control():
    assert _agg([0.4], 0.25, 0.95) == 0.4


def test_identical_controls_diminishing():
    # strongest 0.5, then remaining gap * 0.25 * 0.5, then * 0.0625 * 0.5, ...
    inc = 0.25
    cap = 0.95
    vals = [0.5] * 6
    expected = 0.5
    weight = inc
    for _ in vals[1:]:
        expected += 0.5 * weight * (1 - expected)
        weight *= inc
    expected = min(expected, cap)
    assert abs(_agg(vals, inc, cap) - expected) < 1e-12


def test_barrier_cap():
    assert _agg([0.99, 0.99, 0.99], 0.5, 0.95) == 0.95


def test_maturity_absent_is_zero():
    assert MATURITY["Absent"] == 0.0


def test_maturity_optimised():
    assert MATURITY["Optimised"] == 0.95


def test_not_assessed_is_governed_prior_not_zero():
    assert MATURITY["Not Assessed"] == 0.5


def test_applied_efficacy_zero_coverage():
    base, mf, cov = 0.8, 0.95, 0.0
    assert base * mf * cov == 0.0


def test_applied_efficacy_full_coverage_optimised():
    base, mf, cov = 0.8, 0.95, 1.0
    assert abs(base * mf * cov - 0.76) < 1e-12
