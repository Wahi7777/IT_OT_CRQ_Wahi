"""Determinism / CRN structure (no full production N)."""
import numpy as np

from it_crq.engine import _simulate


def _tiny_cells():
    return [{
        "event_rate": 0.2,
        "actor": "Nation-state",
        "scenario": "Ransomware",
        "blocks": [{"mu": 10.0, "sigma": 0.4}],
    }]


def test_fixed_seed_reproduces_it_simulation():
    cells = _tiny_cells()
    a = _simulate(cells, 2000, 20260821, 1.0, ["Nation-state"], ["Ransomware"], 0.3)
    b = _simulate(cells, 2000, 20260821, 1.0, ["Nation-state"], ["Ransomware"], 0.3)
    assert np.array_equal(a["annual"], b["annual"])


def test_different_seed_changes_draw():
    cells = _tiny_cells()
    a = _simulate(cells, 2000, 1, 1.0, ["Nation-state"], ["Ransomware"], 0.3)
    b = _simulate(cells, 2000, 2, 1.0, ["Nation-state"], ["Ransomware"], 0.3)
    assert not np.array_equal(a["annual"], b["annual"])


def test_invalid_seed_rejected_by_it_num():
    from it_crq.engine import _num
    with __import__("pytest").raises(ValueError):
        _num("not-a-seed", "seed", 0)
