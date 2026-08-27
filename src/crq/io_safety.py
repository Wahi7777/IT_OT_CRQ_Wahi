"""Untrusted-file and untrusted-text controls for local Excel/CSV inputs."""
from __future__ import annotations

import hashlib
from pathlib import Path

FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")
MAX_CSV_BYTES = 2_000_000
MAX_CSV_ROWS = 5_000
MAX_FIELD_CHARS = 4_000
MAX_FINDINGS = 2_000


class UnsafePathError(ValueError):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sanitize_untrusted_text(value: object) -> str:
    """Neutralise spreadsheet formula injection without touching engine formulas.

    Imported scanner/evidence text is stored as a literal. A leading apostrophe
    is the Excel/openpyxl convention for a text value that looks like a formula.
    """
    if value is None:
        return ""
    text = str(value)
    if len(text) > MAX_FIELD_CHARS:
        raise ValueError(f"Untrusted field exceeds {MAX_FIELD_CHARS} characters.")
    stripped = text.lstrip("\ufeff")
    if stripped.startswith("'"):
        return stripped
    if stripped.startswith(FORMULA_PREFIXES) or stripped[:1] in {"=", "+", "-", "@"}:
        return "'" + stripped
    return stripped


def validate_user_path(path: Path, *, must_exist: bool = True, allow_create_parent: bool = False) -> Path:
    raw = Path(path)
    if ".." in raw.parts:
        raise UnsafePathError(f"Path traversal is not permitted: {path}")
    resolved = raw.expanduser().resolve()
    if must_exist and not resolved.is_file():
        raise FileNotFoundError(f"File not found: {resolved}")
    if must_exist and resolved.is_symlink():
        # resolve() already followed the link; reject if the original path was a symlink
        if raw.exists() and raw.is_symlink():
            raise UnsafePathError(f"Symlink inputs are not permitted: {path}")
    if resolved.exists() and resolved.is_symlink():
        raise UnsafePathError(f"Symlink paths are not permitted: {path}")
    return resolved


def assert_not_canonical(output: Path, canonical: Path) -> None:
    if output.resolve() == canonical.resolve():
        raise ValueError(f"Refusing to overwrite the canonical template: {canonical}")


def enforce_csv_limits(path: Path) -> None:
    size = path.stat().st_size
    if size > MAX_CSV_BYTES:
        raise ValueError(f"Outside-in CSV exceeds {MAX_CSV_BYTES} bytes ({size} bytes).")


def memory_guard_simulations(n: int, *, lo: int, hi: int, label: str) -> int:
    if n != int(n) or n < lo or n > hi:
        raise ValueError(f"{label} must be an integer in [{lo}, {hi}]; got {n}.")
    return int(n)
