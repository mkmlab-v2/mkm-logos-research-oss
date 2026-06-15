#!/usr/bin/env python3
"""Merge zone_ko_premium_cs prospect templates into production catalog (gated).

Requires --human-approve-merge --reviewer. Default dry-run plan only.
Mask token (███) required on prospect snippets.

research_only · SEND_GATE HOLD · no ACTIVE mutation.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.merge_zone_ko_premium_cs_template_prospect_v1_lib import (  # noqa: E402
    load_catalog_rows,
    plan_prospect_merge,
    write_catalog_jsonl,
)

DEFAULT_CATALOG = ROOT / "codebook/templates/zone_ko_premium_cs_templates_v1.jsonl"
DEFAULT_PROSPECT = ROOT / "codebook/templates/zone_ko_premium_cs_templates_prospect_v1.jsonl"
DEFAULT_REPORT = ROOT / "reports/zone_ko_premium_cs_template_catalog_merge_v1_latest.json"
DEFAULT_ARTIFACT = ROOT / "docs/final/artifacts/zone_ko_premium_cs_template_catalog_merge_v1_latest.json"
GATE_BUILDER = ROOT / "scripts/build_compression_ko_premium_cs_deep_pack_gate_v1.py"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def build_merge_report(
    *,
    plan: dict[str, Any],
    reviewer: str | None,
    approved: bool,
    applied: bool,
) -> dict[str, Any]:
    return {
        "schema": "zone_ko_premium_cs_template_catalog_merge_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "send_gate": "HOLD",
        "track_a_active_untouched": True,
        "vertical_id": "zone_ko_premium_cs_v1",
        "wire_family": "CS_MASK",
        "human_approve_merge": approved,
        "reviewer": reviewer,
        "applied": applied,
        "production_catalog": _rel(DEFAULT_CATALOG),
        "prospect_catalog": _rel(DEFAULT_PROSPECT),
        "production_before_count": plan["production_before_count"],
        "prospect_input_count": plan["prospect_input_count"],
        "merge_count": plan["merge_count"],
        "skipped_count": plan["skipped_count"],
        "production_after_count": plan["production_after_count"],
        "new_template_ids": [m["new_template_id"] for m in plan["to_merge"]],
        "skipped": plan["skipped"],
        "mask_preservation_required": True,
        "apply_command": (
            "py scripts/merge_zone_ko_premium_cs_template_prospect_to_catalog_v1.py "
            "--human-approve-merge --reviewer commander --rebuild-gate"
        ),
        "forbidden_without_approve": ["automatic_production_catalog_overwrite"],
        "reproduce": "py scripts/merge_zone_ko_premium_cs_template_prospect_to_catalog_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Merge ko premium cs prospect templates into production (gated)")
    ap.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    ap.add_argument("--prospect", type=Path, default=DEFAULT_PROSPECT)
    ap.add_argument("--report-out", type=Path, default=DEFAULT_REPORT)
    ap.add_argument("--artifact-out", type=Path, default=DEFAULT_ARTIFACT)
    ap.add_argument("--human-approve-merge", action="store_true")
    ap.add_argument("--reviewer", default=None)
    ap.add_argument("--rebuild-gate", action="store_true")
    args = ap.parse_args()
    if not args.prospect.is_file():
        print(f"MISSING prospect: {args.prospect}", file=sys.stderr)
        return 1
    production_rows = load_catalog_rows(args.catalog)
    prospect_rows = load_catalog_rows(args.prospect)
    plan = plan_prospect_merge(production_rows=production_rows, prospect_rows=prospect_rows)
    approved = bool(args.human_approve_merge)
    reviewer = str(args.reviewer).strip() if args.reviewer else None
    applied = False
    if approved and not reviewer:
        print("DENIED: --human-approve-merge requires --reviewer", file=sys.stderr)
        return 2
    if approved:
        write_catalog_jsonl(args.catalog, plan["merged_rows"])
        applied = True
        if args.rebuild_gate and GATE_BUILDER.is_file():
            proc = subprocess.run(
                [sys.executable, str(GATE_BUILDER)],
                cwd=str(ROOT),
                capture_output=True,
                text=True,
                check=False,
            )
            if proc.returncode != 0:
                print(proc.stderr or proc.stdout, file=sys.stderr)
                return proc.returncode
        from scripts.compression_deep_pack_tri_vertical_human_signoff_v1_lib import (  # noqa: WPS433
            reconcile_from_tri_signoff_record,
        )

        reconcile_from_tri_signoff_record()
    report = build_merge_report(plan=plan, reviewer=reviewer, approved=approved, applied=applied)
    payload = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    args.report_out.parent.mkdir(parents=True, exist_ok=True)
    args.report_out.write_text(payload, encoding="utf-8")
    args.artifact_out.parent.mkdir(parents=True, exist_ok=True)
    args.artifact_out.write_text(payload, encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "dry_run": not applied,
                "merge_count": plan["merge_count"],
                "production_after_count": plan["production_after_count"],
                "new_template_ids": report["new_template_ids"],
                "applied": applied,
                "report_out": str(args.report_out),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
