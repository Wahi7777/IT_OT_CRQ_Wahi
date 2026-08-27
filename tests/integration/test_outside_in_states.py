"""No-scan invariance of the router (engines mocked)."""
from it_ot_crq.router import run_combined


def test_no_scan_does_not_call_outside_in(tmp_path, monkeypatch):
    import openpyxl
    from tests.helpers import configure_run
    from tests.paths import COMBINED

    dest = tmp_path / "m.xlsx"
    wb = openpyxl.load_workbook(COMBINED)
    configure_run(wb, "Financial Services", "Organisation")
    wb.save(dest)
    wb.close()

    applied = []

    def boom(*_a, **_k):
        applied.append(True)
        raise AssertionError("outside-in must not run")

    monkeypatch.setattr("it_ot_crq.router._snapshot_outside_in", boom)
    monkeypatch.setattr("it_ot_crq.router._apply_approved_adjustments", boom)
    monkeypatch.setattr(
        "it_ot_crq.router._run_it",
        lambda *_a, **_k: {
            "pack_id": "FS-v1.1.1",
            "pack_status": "working",
            "engine_label": "it_crq",
            "validation": "PASS",
            "actor_aal": {},
            "scenario_aal": {},
        },
    )
    result = run_combined(dest, output=tmp_path / "out.xlsx")
    assert result["outside_in_applied"] == "No"
    assert applied == []
