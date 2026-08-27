from __future__ import annotations

import argparse
import shutil
from datetime import datetime, timezone
from pathlib import Path

from .engine import prepare, refresh


def _default_output(model: Path) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    return Path("outputs") / f"{model.stem}_results_{stamp}.xlsx"


def cmd_run(args: argparse.Namespace) -> int:
    model = Path(args.model).expanduser().resolve()
    if not model.is_file():
        raise SystemExit(f"Model not found: {model}")
    out = Path(args.out).expanduser().resolve() if args.out else _default_output(model).resolve()
    if out == model:
        raise SystemExit("Refusing to overwrite the input template. Select a separate output path.")
    out.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(model, out)
    pack_dir = Path(args.sector_pack_dir).expanduser().resolve() if args.sector_pack_dir else (model.parent.parent / "sector_packs").resolve()
    result = refresh(out, out, sector_pack_dir=pack_dir)
    print(f"Output: {result['output']}")
    print(f"Sector pack: {result['pack_id']} ({result['pack_status']})")
    print(f"Exposure adjustments: {result['use_exposure_model']}")
    print(f"AAL — Best Estimate: {result['best_aal']:,.0f} | Prudent: {result['prudent_aal']:,.0f}")
    print(f"VaR 95 — Best Estimate: {result['best_var95']:,.0f} | Prudent: {result['prudent_var95']:,.0f}")
    print(f"TVaR 95 — Best Estimate: {result['best_tvar95']:,.0f} | Prudent: {result['prudent_tvar95']:,.0f}")
    print(f"VaR 99 — Best Estimate: {result['best_var99']:,.0f} | Prudent: {result['prudent_var99']:,.0f}")
    print(f"TVaR 99 — Best Estimate: {result['best_tvar99']:,.0f} | Prudent: {result['prudent_tvar99']:,.0f}")
    print(f"Validation: {result['validation']} ({result['tests_pass']}/{result['tests_total']} tests)")
    return 0 if result["validation"] == "PASS" else 1


def cmd_prepare(args: argparse.Namespace) -> int:
    model = Path(args.model).expanduser().resolve()
    out = Path(args.out).expanduser().resolve() if args.out else model
    pack_dir = Path(args.sector_pack_dir).expanduser().resolve() if args.sector_pack_dir else (model.parent.parent / "sector_packs").resolve()
    result = prepare(model, out, sector_pack_dir=pack_dir)
    print(f"Prepared: {result['output']}")
    print(f"Sector pack: {result['pack_id']} | {result['routes']} routes | {result['controls']} controls")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="it-crq", description="Guided organisation-level IT Cyber Risk Quantification")
    sub = p.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run", help="Run the model and write a separate results workbook")
    run.add_argument("--model", default="model/it/Guided_IT_CRQ_Model_v1_1_1_Dashboard.xlsx")
    run.add_argument("--out", default=None)
    run.add_argument("--sector-pack-dir", default=None, help="Directory containing schema-conformant sector-pack workbooks")
    run.set_defaults(func=cmd_run)
    prep = sub.add_parser("prepare", help="Resize and populate pack-driven main-workbook input tables")
    prep.add_argument("--model", default="model/it/Guided_IT_CRQ_Model_v1_1_1_Dashboard.xlsx")
    prep.add_argument("--out", default=None)
    prep.add_argument("--sector-pack-dir", default=None)
    prep.set_defaults(func=cmd_prepare)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)
