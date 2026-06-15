#!/usr/bin/env python3
"""One-click zone_ko_premium_cs template catalog pipeline: batch → coverage → merge dry-run.

research_only · SEND_GATE HOLD · merge requires --human-approve-merge.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

BATCH = ROOT / "scripts/run_zone_ko_premium_cs_template_catalog_batch_extract_v1.py"
NORMALIZE = ROOT / "scripts/normalize_zone_ko_premium_cs_prospect_mask_tokens_v1.py"
COVERAGE = ROOT / "scripts/run_zone_ko_premium_cs_template_catalog_coverage_v1.py"
MERGE = ROOT / "scripts/merge_zone_ko_premium_cs_template_prospect_to_catalog_v1.py"
DEFAULT_PIPELINE_REPORT = ROOT / "reports/zone_ko_premium_cs_template_catalog_pipeline_v1_latest.json"
DEFAULT_PIPELINE_ARTIFACT = ROOT / "docs/final/artifacts/zone_ko_premium_cs_template_catalog_pipeline_v1_latest.json"


def _run(cmd: list[str]) -> dict:
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    return {
        "cmd": cmd,
        "exit_code": proc.returncode,
        "stdout_tail": (proc.stdout or "")[-2000:],
        "stderr_tail": (proc.stderr or "")[-1000:],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="zone_ko_premium_cs template catalog pipeline")
    ap.add_argument("--write-prospect", action="store_true")
    ap.add_argument("--human-approve-merge", action="store_true")
    ap.add_argument("--reviewer", default="")
    ap.add_argument("--report-out", type=Path, default=DEFAULT_PIPELINE_REPORT)
    ap.add_argument("--artifact-out", type=Path, default=DEFAULT_PIPELINE_ARTIFACT)
    args = ap.parse_args()

    steps: list[dict] = []
    batch_cmd = [sys.executable, str(BATCH)]
    if args.write_prospect:
        batch_cmd.append("--write-prospect")
    steps.append(_run(batch_cmd))
    if args.write_prospect:
        steps.append(_run([sys.executable, str(NORMALIZE)]))
    steps.append(_run([sys.executable, str(COVERAGE)]))

    merge_cmd = [sys.executable, str(MERGE)]
    if args.human_approve_merge:
        merge_cmd.extend(["--human-approve-merge", "--reviewer", args.reviewer or "commander"])
    steps.append(_run(merge_cmd))

    ok = all(s["exit_code"] == 0 for s in steps)
    report = {
        "schema": "zone_ko_premium_cs_template_catalog_pipeline_v1",
        "vertical_id": "zone_ko_premium_cs_v1",
        "wire_family": "CS_MASK",
        "research_only": True,
        "ok": ok,
        "write_prospect": bool(args.write_prospect),
        "human_approve_merge": bool(args.human_approve_merge),
        "steps": steps,
        "reproduce": "py scripts/run_zone_ko_premium_cs_template_catalog_pipeline_v1.py",
    }
    payload = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    args.report_out.parent.mkdir(parents=True, exist_ok=True)
    args.report_out.write_text(payload, encoding="utf-8")
    args.artifact_out.parent.mkdir(parents=True, exist_ok=True)
    args.artifact_out.write_text(payload, encoding="utf-8")
    print(json.dumps({"ok": ok, "report_out": str(args.report_out)}, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
