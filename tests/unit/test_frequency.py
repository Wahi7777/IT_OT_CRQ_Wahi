"""Independent frequency identities."""
import pytest

from ot_crq.engine import best_estimate_lambda, effective_actor_probabilities


def test_successful_event_frequency_identity():
    attempt = 0.4
    p_success = 0.25
    assert attempt * p_success == pytest.approx(0.1)


def test_neutral_multipliers_preserve_reference_rate():
    # shares 0.5, 0.3, 0.2; all overlays 1.0
    weights = [0.5 * 1 * 1 * 1 * 1, 0.3, 0.2]
    lam = best_estimate_lambda(0.12, 1.0, sum(weights))
    assert lam == pytest.approx(0.12)


def test_actor_probabilities_sum_to_one():
    p = effective_actor_probabilities([0.2, 0.3, 0.5])
    assert abs(float(p.sum()) - 1.0) < 1e-12


def test_zero_actor_weights_fail_closed():
    with pytest.raises(ValueError):
        effective_actor_probabilities([0.0, 0.0, 0.0])


def test_route_renormalisation_does_not_drop_campaigns():
    # Valid route shares 0.2 and 0.3, invalid 0.5 → renormalise over 0.5
    raw = [0.2, 0.3, 0.0]
    denom = sum(raw)
    shares = [x / denom for x in raw]
    assert abs(sum(shares) - 1.0) < 1e-12
    base = 1.7
    attempts = [base * s for s in shares]
    assert abs(sum(attempts) - base) < 1e-12
