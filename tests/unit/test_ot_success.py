"""Independent OT conditional-success product tests."""
import pytest

from ot_crq.engine import (
    campaign_conditional_success,
    facility_ttp_feasible,
    stage_barrier,
    ttp_is_relevant,
)


def test_product_of_required_stages_only():
    # Hand: 0.5 * 0.4 * 0.8 = 0.16. Unrequired stages must not be passed in.
    assert campaign_conditional_success([0.5, 0.4, 0.8]) == pytest.approx(0.16)


def test_invalid_path_is_zero_by_caller_convention():
    assert campaign_conditional_success([0.0, 0.9, 0.9]) == 0.0


def test_stage_barrier_mean_includes_unmapped_zero():
    assert stage_barrier([0.6, 0.0]) == pytest.approx(0.3)


def test_empty_stage_barrier_is_zero():
    assert stage_barrier([]) == 0.0


def test_relevance_requires_all_four_gates():
    assert ttp_is_relevant(True, True, True, True) is True
    assert ttp_is_relevant(True, True, True, False) is False
    assert ttp_is_relevant(True, False, True, True) is False


def test_unknown_facility_gate_fails_closed():
    with pytest.raises(ValueError, match="Unknown facility feasibility"):
        facility_ttp_feasible("NOT_A_GATE", {"REMOTE_ACCESS": "Yes"})


def test_internet_ot_gate():
    fac = {"INTERNET_OT": "No"}
    assert facility_ttp_feasible("INTERNET_OT", fac) is False
    fac["INTERNET_OT"] = "Yes"
    assert facility_ttp_feasible("INTERNET_OT", fac) is True
