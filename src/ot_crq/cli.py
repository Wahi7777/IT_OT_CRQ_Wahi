"""Command-line entry point for Guided OT-CRQ v1.7 multi-sector model."""

from __future__ import annotations

import argparse
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path

from .engine import refresh

REPO_ROOT = Path(__file__).resolve().parents[2]
CANONICAL_MODEL = REPO_ROOT / "model" / "ot" / "Guided_OT_CRQ_Model_v1_8_Sector_Packs.xlsx"
ASSESSMENTS_DIR = REPO_ROOT / "assessments"


def _default_output(model: Path) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    stem = model.stem
    return Path("outputs") / f"{stem}_results_{stamp}.xlsx"


def _guard_canonical(path: Path) -> None:
    if path.resolve() == CANONICAL_MODEL.resolve():
        raise SystemExit(
            "Refusing to overwrite the canonical template under model/. "
            "Use assessments/ and write results to outputs/."
        )


def cmd_run(args: argparse.Namespace) -> int:
    model = Path(args.model).expanduser()
    if not model.is_absolute():
        model = (Path.cwd() / model).resolve()
    else:
        model = model.resolve()
    if not model.is_file():
        raise SystemExit(f"Model not found: {model}")

    out = Path(args.out).expanduser() if args.out else _default_output(model)
    if not out.is_absolute():
        out = (Path.cwd() / out).resolve()
    else:
        out = out.resolve()
    out.parent.mkdir(parents=True, exist_ok=True)

    _guard_canonical(out)
    if out == model:
        raise SystemExit(
            "Refusing to overwrite the input workbook. Pass --out under outputs/."
        )

    shutil.copy2(model, out)
    result = refresh(str(out), str(out), run_whatifs=not args.no_whatifs)

    print(f"Output: {result['output']}")
    print(
        f"Sector: {result['sector']} | Asset type: {result['asset_type']} | "
        f"Pack: {result['sector_pack_id']} ({result['sector_pack_status']})"
    )
    print(
        f"AAL — Best Estimate: ${result['BestEstimateAAL']:,.0f} | "
        f"Prudent: ${result['PrudentAAL']:,.0f}"
    )
    print(f"VaR 95: ${result['VaR95']:,.0f} | TVaR 95: ${result['TVaR95']:,.0f}")
    print(f"VaR 99: ${result['VaR99']:,.0f} | TVaR 99: ${result['TVaR99']:,.0f}")
    print(
        f"P(any successful loss event) — Best Estimate: {result['BestEstimatePAny']:.1%} | "
        f"Prudent: {result['PrudentPAny']:.1%}"
    )
    print(
        f"Validation: {result['overall']} "
        f"({result['tests_pass']}/{result['tests_total']} tests)"
    )
    return 0 if result["overall"] == "PASS" else 1


def cmd_validate(args: argparse.Namespace) -> int:
    args.out = args.out or str(_default_output(Path(args.model)))
    args.no_whatifs = getattr(args, "no_whatifs", False)
    return cmd_run(args)


def cmd_new_assessment(args: argparse.Namespace) -> int:
    if not CANONICAL_MODEL.is_file():
        raise SystemExit(f"Canonical template missing: {CANONICAL_MODEL}")

    name = re.sub(r"[^\w\-]+", "_", args.name.strip()).strip("_")
    if not name:
        raise SystemExit("--name must be a non-empty assessment/facility name")

    ASSESSMENTS_DIR.mkdir(parents=True, exist_ok=True)
    dest = ASSESSMENTS_DIR / f"{name}.xlsx"
    if dest.exists() and not args.force:
        raise SystemExit(f"Already exists: {dest} (pass --force to overwrite)")

    shutil.copy2(CANONICAL_MODEL, dest)
    print(f"Created {dest}")
    print("Edit inputs in LibreOffice/Excel, save & close, then run:")
    print(f"  python -m crq run --model assessments/{name}.xlsx --out outputs/{name}.xlsx")
    print("  (native OT-only: python -m ot_crq run --model <assessment.xlsx>)")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ot-crq",
        description="Guided OT Cyber Risk Quantification — v1.7 multi-sector",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    run_p = sub.add_parser("run", help="Run the Monte Carlo engine (what-ifs on by default)")
    run_p.add_argument(
        "--model",
        default="model/ot/Guided_OT_CRQ_Model_v1_8_Sector_Packs.xlsx",
        help="Input workbook (prefer assessments/*.xlsx for live work)",
    )
    run_p.add_argument(
        "--out",
        default=None,
        help="Output workbook path (default: outputs/<name>_results_<timestamp>.xlsx)",
    )
    run_p.add_argument(
        "--no-whatifs",
        action="store_true",
        help="Skip control what-if simulations",
    )
    run_p.set_defaults(func=cmd_run)

    val_p = sub.add_parser(
        "validate",
        help="Run the engine and require all validation tests to PASS",
    )
    val_p.add_argument(
        "--model",
        default="model/ot/Guided_OT_CRQ_Model_v1_8_Sector_Packs.xlsx",
    )
    val_p.add_argument("--out", default=None)
    val_p.add_argument("--no-whatifs", action="store_true")
    val_p.set_defaults(func=cmd_validate)

    new_p = sub.add_parser(
        "new-assessment",
        help="Copy the canonical template into assessments/",
    )
    new_p.add_argument("--name", required=True, help="Facility or assessment name")
    new_p.add_argument(
        "--force",
        action="store_true",
        help="Overwrite an existing assessments/<name>.xlsx",
    )
    new_p.set_defaults(func=cmd_new_assessment)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
