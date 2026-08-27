"""Fail if high-entropy secrets appear in source (not in .venv)."""
import re

from tests.paths import ROOT

SKIP = {".venv", "_work", ".git", "__pycache__", ".pytest_cache", ".ruff_cache", ".cache", "outputs", "assessments"}
PATTERNS = [
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"-----BEGIN (RSA |OPENSSH |EC )?PRIVATE KEY-----"),
    re.compile(r"sk_live_[0-9a-zA-Z]{20,}"),
]


def test_no_embedded_cloud_secrets():
    hits = []
    for path in ROOT.rglob("*"):
        if any(part in SKIP for part in path.parts):
            continue
        if path.suffix.lower() not in {".py", ".md", ".json", ".txt", ".toml", ".yml", ".yaml", ".csv", ".env"}:
            continue
        if path.is_dir():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for pat in PATTERNS:
            if pat.search(text):
                hits.append(f"{path}:{pat.pattern}")
    assert hits == []
