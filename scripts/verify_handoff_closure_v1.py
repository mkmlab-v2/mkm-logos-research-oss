#!/usr/bin/env python3
"""Verify media handoff worker closure after human GUI export [HYPO]."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_WORKERS = ROOT / "reports/handoff_workers"
REPORT_SCHEMA = ROOT / "docs/final/schemas/media_handoff_worker_report_v1.schema.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def _check_layer_c_mdl(
    *,
    md_path: Path,
    report_path: Path,
    require: bool,
) -> tuple[list[str], dict[str, Any]]:
    checks: dict[str, Any] = {"required": require, "present": False}
    if not require:
        return [], checks
    if not report_path.is_file():
        checks["skipped"] = "report_missing"
        return [], checks

    try:
        report = json.loads(report_path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return ["invalid_report_json"], checks

    lanes = report.get("layer_c_mdl")
    if not isinstance(lanes, dict):
        checks["skipped"] = "layer_c_mdl_absent_in_report"
        return [], checks

    checks["present"] = True
    errors: list[str] = []
    if not md_path.is_file():
        return ["missing_markdown_for_layer_c_check"], checks

    md_text = md_path.read_text(encoding="utf-8")
    if "2c. Layer C MDL" not in md_text:
        errors.append("missing_layer_c_mdl_section_in_markdown")

    scholarly = lanes.get("scholarly_top1")
    if isinstance(scholarly, dict) and scholarly.get("segment_id"):
        sid = str(scholarly["segment_id"])
        checks["scholarly_segment_id"] = sid
        if sid not in md_text:
            errors.append(f"missing_scholarly_segment_in_markdown:{sid}")
        saving = scholarly.get("char_saving_rate")
        if saving is not None:
            checks["scholarly_char_saving_rate"] = saving

    multilens = list(lanes.get("multilens_top3") or [])
    checks["multilens_count"] = len(multilens)
    if multilens and "Multilens Top clips" not in md_text:
        errors.append("missing_multilens_mdl_table_in_markdown")

    checks["ok"] = len(errors) == 0
    return errors, checks


def verify_closure(
    *,
    task_id: str,
    workers_dir: Path,
    expect_output: Path | None,
    dry_run: bool,
    require_layer_c_mdl: bool | None = None,
) -> dict[str, Any]:
    md_path = workers_dir / f"HW-{task_id}-LOGOS_CLIP.md"
    report_path = workers_dir / f"HW-{task_id}-report.json"
    errors: list[str] = []

    if not md_path.is_file():
        errors.append(f"missing_markdown:{_rel(md_path)}")
    if not report_path.is_file():
        errors.append(f"missing_report:{_rel(report_path)}")

    layer_c_require = require_layer_c_mdl
    if layer_c_require is None and report_path.is_file():
        try:
            report_probe = json.loads(report_path.read_text(encoding="utf-8-sig"))
            layer_c_require = isinstance(report_probe.get("layer_c_mdl"), dict)
        except json.JSONDecodeError:
            layer_c_require = False
    elif layer_c_require is None:
        layer_c_require = False

    layer_c_errors, layer_c_checks = _check_layer_c_mdl(
        md_path=md_path,
        report_path=report_path,
        require=bool(layer_c_require),
    )
    errors.extend(layer_c_errors)

    output_ok = None
    if expect_output is not None:
        output_ok = expect_output.is_file() and expect_output.stat().st_size > 0
        if not output_ok:
            errors.append(f"missing_output:{_rel(expect_output)}")

    doc: dict[str, Any] = {
        "schema": "media_handoff_closure_v1",
        "generated_at_utc": _utc_now(),
        "task_id": task_id,
        "research_only": True,
        "send_gate": "HOLD",
        "dry_run": dry_run,
        "markdown_path": _rel(md_path),
        "report_json": _rel(report_path),
        "expect_output": _rel(expect_output) if expect_output else None,
        "output_present": output_ok,
        "layer_c_mdl_checks": layer_c_checks,
        "ok": len(errors) == 0,
        "errors": errors,
        "reproduce": f"py scripts/verify_handoff_closure_v1.py --task-id {task_id}",
    }
    return doc


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--task-id", required=True)
    ap.add_argument("--workers-dir", type=Path, default=DEFAULT_WORKERS)
    ap.add_argument("--expect-output", type=Path, default=None)
    ap.add_argument("--dry-run", action="store_true", help="Require markdown+report only (default)")
    ap.add_argument(
        "--require-layer-c-mdl",
        action="store_true",
        help="Require §2c Layer C MDL in markdown (auto when report has layer_c_mdl)",
    )
    ap.add_argument(
        "--skip-layer-c-mdl",
        action="store_true",
        help="Skip Layer C MDL section checks",
    )
    args = ap.parse_args()

    workers_dir = args.workers_dir if args.workers_dir.is_absolute() else ROOT / args.workers_dir
    expect = None
    if args.expect_output:
        expect = args.expect_output if args.expect_output.is_absolute() else ROOT / args.expect_output
    elif not args.dry_run:
        expect = ROOT / "data/media/output" / f"{args.task_id}_final.mp4"

    doc = verify_closure(
        task_id=args.task_id,
        workers_dir=workers_dir,
        expect_output=expect if not args.dry_run else None,
        dry_run=args.dry_run or expect is None,
        require_layer_c_mdl=False if args.skip_layer_c_mdl else (True if args.require_layer_c_mdl else None),
    )

    out_path = workers_dir / f"HW-{args.task_id}-closure.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc["ok"], "closure_json": _rel(out_path), "errors": doc["errors"]}, ensure_ascii=False))
    return 0 if doc["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
