#!/usr/bin/env python3
"""Run apocrypha frontline rebuild + MKM NDJSON ingest/AB/uplift chain.

research_only · [HYPO] · B-track · not Track A or live triggers.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DSS_ROOT = ROOT / "projects/dss-4d-ingest"
DEFAULT_REPORT = ROOT / "reports/dss_apocrypha_frontline_rebuild_chain_latest.json"
DRY_RUN_REPORT = ROOT / "reports/dss_apocrypha_frontline_rebuild_chain_dry_run_latest.json"
ON_DISK_EXT2 = DSS_ROOT / "outputs/apocrypha_tokens_pilot_manifest_ext2_weighted.ndjson"
ON_DISK_EXT3 = DSS_ROOT / "outputs/apocrypha_tokens_pilot_manifest_ext3_hebrew_priority.ndjson"


def _count_ndjson_lines(path: Path) -> int:
    if not path.is_file():
        return 0
    return sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run_step(name: str, cmd: list[str], *, cwd: Path | None = None) -> dict[str, Any]:
    r = subprocess.run(cmd, cwd=str(cwd or ROOT), capture_output=True, text=True)
    return {
        "step": name,
        "return_code": r.returncode,
        "stdout_tail": (r.stdout or "")[-2000:],
        "stderr_tail": (r.stderr or "")[-1000:] if r.returncode != 0 else "",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true", help="Sefaria/URL dry-run (smoke token count)")
    ap.add_argument("--max-chapters-per-work", type=int, default=None)
    ap.add_argument("--output-dir", type=Path, default=None, help="Pilot NDJSON output dir (dry-run default: reports/tmp_dss_apocrypha_dry_run)")
    ap.add_argument("--report-json", type=Path, default=None)
    args = ap.parse_args()

    if args.report_json is None:
        args.report_json = DRY_RUN_REPORT if args.dry_run else DEFAULT_REPORT

    output_dir = args.output_dir
    if output_dir is None and args.dry_run:
        output_dir = ROOT / "reports/tmp_dss_apocrypha_dry_run"

    pilot_cmd = [
        sys.executable,
        str(DSS_ROOT / "run_apocrypha_pilot.py"),
        "--manifest",
        "pilot_manifest_ext2.json",
    ]
    if output_dir is not None:
        pilot_cmd.extend(["--output-dir", str(output_dir)])
    if args.dry_run:
        pilot_cmd.append("--dry-run")
    if args.max_chapters_per_work is not None:
        pilot_cmd.extend(["--max-chapters-per-work", str(args.max_chapters_per_work)])

    downstream_steps = [
        (
            "dss_authority_readiness_reconciliation",
            [sys.executable, "scripts/build_dss_authority_readiness_reconciliation_v1.py"],
            ROOT,
        ),
        (
            "dss_ndjson_token_manifest_ingest",
            [
                sys.executable,
                "scripts/ingest_dss_ndjson_token_manifest_research_context_v1.py",
                "--merge-into",
                "docs/final/artifacts/news_observation_v1_dss_apocrypha_research_context_latest.jsonl",
            ],
            ROOT,
        ),
        (
            "biblical_resonance_research_production_ab",
            [sys.executable, "scripts/build_biblical_resonance_research_production_ab_v1.py"],
            ROOT,
        ),
        (
            "dss_ndjson_resonance_uplift_report",
            [sys.executable, "scripts/build_dss_ndjson_resonance_uplift_report_v1.py"],
            ROOT,
        ),
        (
            "dss_frontline_research_bridge",
            [sys.executable, "scripts/build_dss_frontline_research_bridge_v1.py"],
            ROOT,
        ),
    ]
    steps = [("apocrypha_pilot_rebuild", pilot_cmd, DSS_ROOT)]
    if not args.dry_run:
        steps.extend(downstream_steps)

    results: list[dict[str, Any]] = []
    ok = True
    for name, cmd, cwd in steps:
        row = _run_step(name, cmd, cwd=cwd)
        results.append(row)
        if row["return_code"] != 0:
            ok = False
            break

    ext2_base = output_dir if output_dir is not None else DSS_ROOT / "outputs"
    ext2 = ext2_base / "apocrypha_tokens_pilot_manifest_ext2_weighted.ndjson"
    line_count = _count_ndjson_lines(ext2)
    on_disk_ssot = {
        "ext2_weighted_path": str(ON_DISK_EXT2),
        "ext2_weighted_lines": _count_ndjson_lines(ON_DISK_EXT2),
        "ext3_hebrew_priority_path": str(ON_DISK_EXT3),
        "ext3_hebrew_priority_lines": _count_ndjson_lines(ON_DISK_EXT3),
        "note": "LOCK_ON_DISK_CORPUS_COUNT — pilot output_dir counts are not production SSOT when dry_run",
    }

    payload = {
        "schema": "dss_apocrypha_frontline_rebuild_chain_v1",
        "generated_at_utc": _utc_now(),
        "ok": ok,
        "dry_run": args.dry_run,
        "report_path": str(args.report_json),
        "pilot_ext2_ndjson_lines": line_count,
        "on_disk_corpus_ssot": on_disk_ssot,
        "steps": results,
        "research_rail": "B",
        "hypothesis_tier": "[HYPO]",
        "track_a_promotion": "blocked",
    }
    args.report_json.parent.mkdir(parents=True, exist_ok=True)
    args.report_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": ok, "ext2_ndjson_lines": line_count, "report": str(args.report_json)}, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
