from ot_crq.engine import REQUIRED_SIMULATIONS, _single_row, _required_multiplier
import pytest


def test_duplicate_registry_rows_fail_closed():
    rows = [["Power Generation", "PG-v1.6"], ["Power Generation", "PG-v1.6"]]
    with pytest.raises(ValueError, match="exactly one row"):
        _single_row(rows, lambda r: r[0] == "Power Generation", "Sector pack")


def test_missing_registry_row_fail_closed():
    with pytest.raises(ValueError, match="exactly one row"):
        _single_row([], lambda r: True, "Sector pack")


def test_missing_multiplier_fail_closed():
    with pytest.raises(ValueError, match="silent 1.00"):
        _required_multiplier(None, "sector multiplier")


def test_ot_requires_500000_simulations():
    assert REQUIRED_SIMULATIONS == 500_000
