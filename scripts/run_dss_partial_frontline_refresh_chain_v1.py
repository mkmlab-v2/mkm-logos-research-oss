#!/usr/bin/env python3
"""Partial frontline refresh — runnable DSS steps + ext3 fusion (no live apocrypha re-fetch).

Full `run_unified_frontline_cycle.py` is not in repo; `evaluate_authority_readiness.py` restored under
projects/dss-4d-ingest. ext3 Hebrew-priority pin JSON remains ingest SSOT. research_only · [HYPO].
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
DSS = ROOT / "projects/dss-4d-ingest"
DEFAULT_TAG = "command_center_followup_20260607_ext3_refresh"
DEFAULT_OUT = ROOT / "reports/dss_partial_frontline_refresh_chain_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(name: str, cmd: list[str], *, cwd: Path) -> dict[str, Any]:
    r = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True)
    return {
        "step": name,
        "return_code": r.returncode,
        "stdout_tail": (r.stdout or "")[-1500:],
        "stderr_tail": (r.stderr or "")[-800:] if r.returncode != 0 else "",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--tag", default=DEFAULT_TAG)
    ap.add_argument("--skip-dss-ci-smoke", action="store_true")
    ap.add_argument("--report-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    fusion_out = DSS / "outputs" / f"fusion_join_quality_{args.tag}.json"
    quality_ext3 = DSS / "outputs/apocrypha_quality_report_pilot_manifest_ext3_hebrew_priority.json"
    insight_out = DSS / "outputs" / f"dss_apocrypha_insight_brief_{args.tag}.json"
    authority_out = DSS / "outputs" / f"authority_readiness_{args.tag}.json"
    steps: list[tuple[str, list[str], Path]] = []

    if not args.skip_dss_ci_smoke:
        steps.append(
            (
                "dss_ci_smoke",
                [sys.executable, "run_dss_ci_smoke.py", "--manifest", "dss_ci_manifest_tf4.json"],
                DSS,
            )
        )
    steps.extend(
        [
            (
                "fusion_join_ext3",
                [
                    sys.executable,
                    "judge_fusion_join_quality.py",
                    "--dss-ndjson",
                    "outputs/dss_tokens_ci_smoke_manifest_tf4.ndjson",
                    "--apocrypha-ndjson",
                    "outputs/apocrypha_tokens_pilot_manifest_ext3_hebrew_priority.ndjson",
                    "--min-overlap-tokens",
                    "5",
                    "--min-overlap-ratio-dss",
                    "0.02",
                    "--out",
                    str(fusion_out.relative_to(DSS)),
                ],
                DSS,
            ),
            (
                "insight_brief_ext3",
                [
                    sys.executable,
                    "build_dss_apocrypha_insight_brief_v1.py",
                    "--tag",
                    args.tag,
                    "--quality-json",
                    str(quality_ext3.relative_to(DSS)),
                    "--fusion-quality-json",
                    str(fusion_out.relative_to(DSS)),
                    "--out-json",
                    str(insight_out.relative_to(DSS)),
                ],
                DSS,
            ),
            (
                "evaluate_authority_readiness",
                [
                    sys.executable,
                    "evaluate_authority_readiness.py",
                    "--tag",
                    args.tag,
                    "--insight-brief-json",
                    str(insight_out.relative_to(DSS)),
                    "--min-hebrew-primary-tokens",
                    "500",
                    "--max-translation-proxy-ratio",
                    "0.8",
                    "--min-fusion-overlap-ratio-dss",
                    "0.02",
                    "--out-json",
                    str(authority_out.relative_to(DSS)),
                ],
                DSS,
            ),
            (
                "evaluate_authority_ext3_pin",
                [
                    sys.executable,
                    "evaluate_authority_readiness.py",
                    "--tag",
                    args.tag,
                    "--insight-brief-json",
                    str(insight_out.relative_to(DSS)),
                    "--min-hebrew-primary-tokens",
                    "500",
                    "--max-translation-proxy-ratio",
                    "0.8",
                    "--min-fusion-overlap-ratio-dss",
                    "0.02",
                    "--out-json",
                    "outputs/authority_readiness_command_center_followup_20260327_h_ext3.json",
                ],
                DSS,
            ),
            (
                "authority_reconciliation",
                [sys.executable, "scripts/build_dss_authority_readiness_reconciliation_v1.py"],
                ROOT,
            ),
            (
                "authority_pin_policy",
                [sys.executable, "scripts/build_dss_authority_pin_policy_v1.py"],
                ROOT,
            ),
            (
                "frontline_research_bridge",
                [sys.executable, "scripts/build_dss_frontline_research_bridge_v1.py"],
                ROOT,
            ),
        ]
    )

    results: list[dict[str, Any]] = []
    ok = True
    for name, cmd, cwd in steps:
        row = _run(name, cmd, cwd=cwd)
        results.append(row)
        if row["return_code"] != 0:
            ok = False
            break

    fusion_status = None
    if fusion_out.is_file():
        fusion_status = json.loads(fusion_out.read_text(encoding="utf-8")).get("status")

    payload = {
        "schema": "dss_partial_frontline_refresh_chain_v1",
        "generated_at_utc": _utc_now(),
        "ok": ok,
        "tag": args.tag,
        "fusion_report": str(fusion_out),
        "fusion_status": fusion_status,
        "ext3_authority_pin": str(
            DSS / "outputs/authority_readiness_command_center_followup_20260327_h_ext3.json"
        ),
        "authority_readiness_refresh": str(authority_out),
        "missing_full_cycle_scripts": [
            "run_unified_frontline_cycle.py",
        ],
        "steps": results,
        "research_rail": "B",
        "hypothesis_tier": "[HYPO]",
        "track_a_promotion": "blocked",
    }
    args.report_json.parent.mkdir(parents=True, exist_ok=True)
    args.report_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": ok, "fusion_status": fusion_status, "report": str(args.report_json)}, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
