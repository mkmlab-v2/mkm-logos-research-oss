#!/usr/bin/env python3
"""Export Han Vocology slide deck via vendored mdpresent (B-track · M22 PoC).

Requires: tools/vendor/mdpresent built (`pnpm install && pnpm run build`).
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
MDPRESENT_ROOT = ROOT / "tools/vendor/mdpresent"
CLI_ENTRY = MDPRESENT_ROOT / "packages/cli/dist/index.js"
DEFAULT_MD = ROOT / "docs/research/HAN_VOCOLOGY_SLIDES_M3_05_POC_V1.md"
OUT_DIR = ROOT / "reports/han_vocology_slides_m3_05_poc_v1"
REPORT = ROOT / "reports/han_vocology_slides_export_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _node() -> str:
    return os.environ.get("MKM_NODE", "node")


def _mdpresent_cli(*args: str) -> subprocess.CompletedProcess[str]:
    if not CLI_ENTRY.is_file():
        raise FileNotFoundError(f"mdpresent CLI missing: {CLI_ENTRY} (run pnpm build in vendor)")
    cmd = [_node(), str(CLI_ENTRY), *args]
    return subprocess.run(
        cmd,
        cwd=MDPRESENT_ROOT,
        capture_output=True,
        text=True,
        check=False,
        encoding="utf-8",
        errors="replace",
    )


def export_slides(
    *,
    md: Path,
    out_dir: Path,
    design: str,
    formats: list[str],
) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    plan_json = out_dir / "deck.plan.json"
    layout_json = out_dir / "layout.plan.json"

    inspect = _mdpresent_cli("inspect", str(md.resolve()), "--json")
    if inspect.returncode == 0 and inspect.stdout.strip():
        plan_json.write_text(inspect.stdout, encoding="utf-8")

    plan = _mdpresent_cli("plan", str(md.resolve()), "--json")
    if plan.returncode == 0 and plan.stdout.strip():
        layout_json.write_text(plan.stdout, encoding="utf-8")

    validate = _mdpresent_cli("validate", str(md.resolve()))

    fmt = ",".join(formats)
    build = _mdpresent_cli(
        "build",
        str(md.resolve()),
        "--to",
        fmt,
        "--out",
        str(out_dir.resolve()),
        "--design",
        design,
    )

    outputs: list[str] = []
    for ext in ("pptx", "html", "pdf"):
        for p in out_dir.rglob(f"*.{ext}"):
            outputs.append(str(p.relative_to(ROOT)).replace("\\", "/"))

    ok = build.returncode == 0 and bool(outputs)
    return {
        "ok": ok,
        "md": str(md),
        "out_dir": str(out_dir),
        "design": design,
        "formats": formats,
        "inspect_exit": inspect.returncode,
        "plan_exit": plan.returncode,
        "validate_exit": validate.returncode,
        "build_exit": build.returncode,
        "build_stdout_tail": (build.stdout or "")[-500:],
        "build_stderr_tail": (build.stderr or "")[-500:],
        "outputs": sorted(outputs),
        "plan_json": str(plan_json) if plan_json.is_file() else None,
        "layout_json": str(layout_json) if layout_json.is_file() else None,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--md", type=Path, default=DEFAULT_MD)
    ap.add_argument("--out-dir", type=Path, default=OUT_DIR)
    ap.add_argument("--design", default="executive")
    ap.add_argument("--formats", default="pptx,html")
    ap.add_argument("--clean", action="store_true", help="Remove out-dir before build")
    args = ap.parse_args()

    if not args.md.is_file():
        print(json.dumps({"ok": False, "error": "md_missing", "md": str(args.md)}, ensure_ascii=False))
        return 1

    if args.clean and args.out_dir.exists():
        shutil.rmtree(args.out_dir)

    formats = [f.strip() for f in args.formats.split(",") if f.strip()]
    try:
        result = export_slides(md=args.md, out_dir=args.out_dir, design=args.design, formats=formats)
    except FileNotFoundError as exc:
        report = {
            "schema": "han_vocology_slides_export_v1",
            "ok": False,
            "generated_at_utc": _utc(),
            "error": str(exc),
            "vendor_build": "cd tools/vendor/mdpresent && pnpm install && pnpm run build",
        }
        REPORT.parent.mkdir(parents=True, exist_ok=True)
        REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(report, ensure_ascii=False))
        return 1

    report = {
        "schema": "han_vocology_slides_export_v1",
        "generated_at_utc": _utc(),
        "track": "B",
        "send_gate": "HOLD",
        "engine": "mdpresent",
        "engine_path": str(MDPRESENT_ROOT),
        **result,
        "reproduce": f"py scripts/export_han_vocology_slides_v1.py --design {args.design}",
    }
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": result["ok"], "outputs": result["outputs"], "out": str(REPORT)}, ensure_ascii=False))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
