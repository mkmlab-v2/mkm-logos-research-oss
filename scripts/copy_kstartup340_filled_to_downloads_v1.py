#!/usr/bin/env python3
"""Copy filled 340 docx/PDF to Downloads with Korean + ASCII filenames."""
from __future__ import annotations

import argparse
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KO_BASE = "340_창업패키지_사업계획서_목소리네트워크"
EN_BASE = "kstartup340_plan_moksori"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--version", type=int, required=True)
    ap.add_argument(
        "--docx",
        default="",
        help="Source docx (default: reports/.../doyak_plan_filled_vN.docx)",
    )
    ap.add_argument("--pdf", default="")
    ap.add_argument("--hwp", default="", help="Optional HWP (same version stem as docx)")
    args = ap.parse_args()

    ver = args.version
    docx = Path(args.docx) if args.docx else ROOT / f"reports/kstartup_startup_package_ai_filled/doyak_plan_filled_v{ver}.docx"
    pdf = Path(args.pdf) if args.pdf else ROOT / f"reports/kstartup_startup_package_ai_filled/doyak_plan_filled_v{ver}.pdf"
    if not docx.is_file():
        raise SystemExit(f"docx missing: {docx}")
    if not pdf.is_file():
        raise SystemExit(f"pdf missing: {pdf}")

    hwp = Path(args.hwp) if args.hwp else ROOT / f"reports/kstartup_startup_package_ai_filled/doyak_plan_filled_v{ver}.hwp"

    dl = Path.home() / "Downloads"
    dl.mkdir(parents=True, exist_ok=True)
    targets = [
        dl / f"{KO_BASE}_v{ver}.docx",
        dl / f"{KO_BASE}_v{ver}.pdf",
        dl / f"{EN_BASE}_v{ver}.docx",
        dl / f"{EN_BASE}_v{ver}.pdf",
    ]
    shutil.copy2(docx, targets[0])
    shutil.copy2(pdf, targets[1])
    shutil.copy2(docx, targets[2])
    shutil.copy2(pdf, targets[3])
    if hwp.is_file():
        for name in (f"{KO_BASE}_v{ver}.hwp", f"{EN_BASE}_v{ver}.hwp"):
            dest = dl / name
            shutil.copy2(hwp, dest)
            targets.append(dest)
    for t in targets:
        print(t)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
