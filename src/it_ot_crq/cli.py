from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

from crq.io_safety import assert_not_canonical, validate_user_path
from .navigation import apply_workbook_navigation
from .router import CANONICAL_COMBINED_NAMES, run_combined


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="crq",
        description="Combined IT/OT CRQ router: one workbook, governed domain-specific engines.",
    )
    sub = p.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="Run the selected IT or OT methodology from the combined workbook")
    run.add_argument("--model", default="model/Guided_IT_OT_CRQ_Model_v1_0.xlsx")
    run.add_argument("--out", default=None)
    run.add_argument("--sector-pack-dir", default="sector_packs")
    run.add_argument("--outside-in-file", default=None)
    run.add_argument("--work-dir", default="_work")
    run.add_argument("--no-whatifs", action="store_true")
    run.set_defaults(func=_run)

    prep = sub.add_parser(
        "prepare",
        help="After Sector is set, hide the other domain's fill tabs in an assessment workbook",
    )
    prep.add_argument("--model", required=True)
    prep.set_defaults(func=_prepare)

    reb = sub.add_parser("rebuild-workbook", help="Extract OT packs and rebuild combined navigation from code")
    reb.set_defaults(func=_rebuild)

    val = sub.add_parser("validate-release", help="Fast CI release suite, or --production to execute approved 500k baselines")
    val.add_argument("--production", action="store_true", help="Execute, but never regenerate, approved 500,000-year baselines")
    val.set_defaults(func=_validate_release)
    return p


def _prepare(args: argparse.Namespace) -> int:
    import openpyxl
    from .router import SECTOR_DOMAIN, _sector_from_workbook

    model = validate_user_path(args.model, must_exist=True)
    root = Path(__file__).resolve().parents[2]
    for name in CANONICAL_COMBINED_NAMES:
        candidate = root / name
        if candidate.is_file():
            assert_not_canonical(model.resolve(), candidate)
    sector = _sector_from_workbook(model)
    domain = SECTOR_DOMAIN[sector]
    wb = openpyxl.load_workbook(model)
    try:
        apply_workbook_navigation(wb, domain=domain)
        wb.save(model)
    finally:
        wb.close()
    print(f"Prepared {model} for {sector} ({domain}). Unused domain tabs are hidden.")
    return 0


def _rebuild(args: argparse.Namespace) -> int:
    from crq.pack_registry import project_root_from
    from it_ot_crq.rebuild import rebuild_release

    root = project_root_from()
    rebuild_release(root)
    print(f"Rebuilt combined workbook and external sector packs under {root}")
    return 0


def _run(args: argparse.Namespace) -> int:
    result = run_combined(
        model=Path(args.model),
        output=Path(args.out) if args.out else None,
        sector_pack_dir=Path(args.sector_pack_dir),
        outside_in_file=Path(args.outside_in_file) if args.outside_in_file else None,
        work_dir=Path(args.work_dir),
        run_whatifs=not args.no_whatifs,
    )
    print(f"Sector: {result['sector']}")
    print(f"Domain: {result['domain']}")
    print(f"Engine: {result['engine']}")
    print(f"Pack: {result['pack_id']} ({result['pack_status']})")
    print(f"Outside-In applied: {result['outside_in_applied']}")
    print(f"Output path: {result['output']}")
    aal = result.get("prudent_aal")
    tvar = result.get("tvar99")
    if aal is not None:
        print(f"AAL (Prudent): {float(aal):,.0f}")
    if tvar is not None:
        print(f"TVaR99 (Prudent): {float(tvar):,.0f}")
    print(f"Validation status: {result['validation']}")
    return 0 if str(result.get("validation")) == "PASS" else 1


def _validate_release(args: argparse.Namespace) -> int:
    root = Path(__file__).resolve().parents[2]
    env = os.environ.copy()
    env["PYTHONPATH"] = str(root / "src") + os.pathsep + str(root) + os.pathsep + env.get("PYTHONPATH", "")
    # Always run the fast suite without production cases first. Production
    # baselines are executed exactly once below and are never regenerated here.
    marker = "not production"
    cmd = [sys.executable, "-m", "pytest", "-q", str(root / "tests")]
    cmd.extend(["-m", marker])
    proc = subprocess.run(cmd, cwd=root, env=env)
    if proc.returncode != 0:
        return proc.returncode
    extras = [
        [sys.executable, "-m", "ruff", "check", "src", "tests"],
        [sys.executable, "-m", "bandit", "-q", "-r", "src", "-ll"],
    ]
    for extra in extras:
        extra_proc = subprocess.run(extra, cwd=root, env=env)
        if extra_proc.returncode != 0:
            return extra_proc.returncode
    cache = root / ".cache" / "pip-audit"
    cache.mkdir(parents=True, exist_ok=True)
    env["PIP_AUDIT_CACHE_DIR"] = str(cache)
    audit = subprocess.run(
        [sys.executable, "-m", "pip_audit", "-r", "requirements.txt", "--cache-dir", str(cache)],
        cwd=root,
        env=env,
    )
    if audit.returncode != 0:
        print("pip-audit failed; treat as a release blocker.")
        return audit.returncode
    if args.production:
        env["CRQ_REQUIRE_GOLDENS"] = "1"
        prod = subprocess.run(
            [sys.executable, "-m", "pytest", "-q", str(root / "tests"), "-m", "production"],
            cwd=root,
            env=env,
        )
        if prod.returncode != 0:
            return prod.returncode
    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)
