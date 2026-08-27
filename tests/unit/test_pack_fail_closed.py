"""Fail-closed external pack resolution."""
from pathlib import Path

import pytest
from crq.pack_registry import resolve_pack, validate_pack_file
from ot_crq.engine import ENGINE_VERSION


def test_registry_resolves_four_packs():
    root = Path(__file__).resolve().parents[2]
    for domain, sector, pack_id in [
        ("IT", "Financial Services", "FS-v1.1.1"),
        ("OT", "Power Generation", "PG-v1.6"),
        ("OT", "Energy Assets", "EA-v1.0"),
        ("OT", "Manufacturing", "MF-v1.0"),
    ]:
        rec = resolve_pack(domain, sector, root)
        assert rec.pack_id == pack_id
        validate_pack_file(rec, root, ENGINE_VERSION if domain == "OT" else "1.1.1", domain)


def test_missing_pack_file_fails(tmp_path, monkeypatch):
    from crq import pack_registry as pr

    rec = resolve_pack("OT", "Power Generation")
    monkeypatch.setattr(pr.PackRecord, "path", lambda self, root: tmp_path / "nope.xlsx")
    with pytest.raises(FileNotFoundError):
        pr.resolve_pack("OT", "Power Generation")


def test_it_sector_rejected_for_ot_domain():
    with pytest.raises(ValueError, match="not valid for domain"):
        resolve_pack("OT", "Financial Services")


def test_unsupported_domain():
    with pytest.raises(ValueError, match="Unsupported domain"):
        resolve_pack("HYBRID", "Financial Services")
