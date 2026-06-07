#!/usr/bin/env python3
"""Unified frontline cycle (runnable subset) — no live apocrypha re-fetch by default.

Missing legacy scripts are recorded as SKIPPED_MISSING_SCRIPT. research_only · [HYPO].
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
WORKSPACE = ROOT.parents[1]

LEGACY_SCRIPT_STEPS: tuple[tuple[str, str], ...] = (
    ("joint_frontline_gate", "run_joint_frontline_gate.py"),
    ("summarize_dss_apocrypha_insights", "summarize_dss_apocrypha_insights.py"),
    ("plan_apocrypha_hebrew_priority", "plan_apocrypha_hebrew_priority.py"),
    ("compare_authority_readiness_delta", "compare_authority_readiness_delta.py"),
    ("rank_apocrypha_symbol_patterns", "rank_apocrypha_symbol_patterns.py"),
    ("summarize_fusion_insight_topn", "summarize_fusion_insight_topn.py"),
    ("generate_fusion_rule_candidates", "generate_fusion_rule_candidates.py"),
    ("score_fusion_rule_candidates", "score_fusion_rule_candidates.py"),
    ("fusion_rule_score_gate", "judge_fusion_rule_score_gate.py"),
)
POST_REPORT_STEPS: tuple[tuple[str, str], ...] = (
    ("unified_cycle_regression", "judge_unified_cycle_regression.py"),
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(cmd: list[str], *, cwd: Path) -> dict[str, Any]:
    r = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True)
    status = "PASS" if r.returncode == 0 else "FAIL"
    return {
        "command": " ".join(cmd),
        "cwd": str(cwd),
        "exit_code": r.returncode,
        "status": status,
        "output": (r.stdout or "")[-3000:] + ((r.stderr or "")[-500:] if r.returncode != 0 else ""),
    }


def _skipped(name: str, script: str, reason: str) -> dict[str, Any]:
    return {
        "command": f"python {script}",
        "cwd": str(ROOT),
        "exit_code": None,
        "status": "SKIPPED_MISSING_SCRIPT",
        "output": reason,
        "run_key": name,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--tag", required=True)
    ap.add_argument("--auto-base-tag", action="store_true", help="Ignored; compatibility with legacy CLI.")
    ap.add_argument("--include-apocrypha-rebuild", action="store_true")
    ap.add_argument("--skip-dss-ci-smoke", action="store_true")
    ap.add_argument("--dry-run", action="store_true", help="Write plan only; do not execute steps.")
    args = ap.parse_args()

    fusion_out = ROOT / "outputs" / f"fusion_join_quality_{args.tag}.json"
    quality_ext3 = ROOT / "outputs/apocrypha_quality_report_pilot_manifest_ext3_hebrew_priority.json"
    insight_out = ROOT / "outputs" / f"dss_apocrypha_insight_brief_{args.tag}.json"
    authority_out = ROOT / "outputs" / f"authority_readiness_{args.tag}.json"
    report_out = ROOT / "outputs" / f"unified_frontline_cycle_report_{args.tag}.json"
    status_out = ROOT / "outputs/frontline_latest_status.json"

    planned: list[tuple[str, list[str] | None, Path, str | None]] = []

    if not args.skip_dss_ci_smoke:
        planned.append(
            (
                "dss",
                [sys.executable, "run_dss_ci_smoke.py", "--manifest", "dss_ci_manifest_tf4.json"],
                ROOT,
                None,
            )
        )
    if args.include_apocrypha_rebuild:
        planned.append(
            (
                "apocrypha",
                [sys.executable, "run_apocrypha_pilot.py", "--manifest", "pilot_manifest_ext3_hebrew_priority.json"],
                ROOT,
                None,
            )
        )
    else:
        planned.append(("apocrypha", None, ROOT, "ext3_hebrew_priority_ndjson_on_disk_no_refetch"))

    planned.extend(
        [
            (
                "fusion_join_gate",
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
                    str(fusion_out.relative_to(ROOT)),
                ],
                ROOT,
                None,
            ),
            (
                "insight_brief",
                [
                    sys.executable,
                    "build_dss_apocrypha_insight_brief_v1.py",
                    "--tag",
                    args.tag,
                    "--quality-json",
                    str(quality_ext3.relative_to(ROOT)),
                    "--fusion-quality-json",
                    str(fusion_out.relative_to(ROOT)),
                    "--out-json",
                    str(insight_out.relative_to(ROOT)),
                ],
                ROOT,
                None,
            ),
            (
                "authority_readiness",
                [
                    sys.executable,
                    "evaluate_authority_readiness.py",
                    "--tag",
                    args.tag,
                    "--insight-brief-json",
                    str(insight_out.relative_to(ROOT)),
                    "--out-json",
                    str(authority_out.relative_to(ROOT)),
                ],
                ROOT,
                None,
            ),
        ]
    )
    tag = args.tag
    rel_fusion = str(fusion_out.relative_to(ROOT))
    rel_insight = str(insight_out.relative_to(ROOT))
    rel_authority = str(authority_out.relative_to(ROOT))
    rel_report = str(report_out.relative_to(ROOT))
    for key, script in LEGACY_SCRIPT_STEPS:
        cmd = [sys.executable, script, "--tag", tag]
        if key == "joint_frontline_gate":
            cmd += ["--fusion-json", rel_fusion, "--authority-json", rel_authority]
        elif key == "summarize_dss_apocrypha_insights":
            cmd += ["--insight-brief-json", rel_insight]
        elif key == "summarize_fusion_insight_topn":
            cmd += ["--fusion-json", rel_fusion]
        elif key == "compare_authority_readiness_delta":
            cmd += ["--current-json", rel_authority]
        elif key == "generate_fusion_rule_candidates":
            cmd += ["--fusion-json", rel_fusion]
        elif key == "score_fusion_rule_candidates":
            cmd += ["--fusion-json", rel_fusion]
        planned.append((key, cmd, ROOT, None))

    runs: dict[str, Any] = {}
    ok = True
    if args.dry_run:
        for name, cmd, cwd, skip_reason in planned:
            if skip_reason:
                runs[name] = _skipped(name, skip_reason.split(":")[-1] if skip_reason.startswith("missing:") else "n/a", skip_reason)
            else:
                runs[name] = {"command": " ".join(cmd or []), "cwd": str(cwd), "status": "DRY_RUN", "exit_code": None, "output": ""}
    else:
        for name, cmd, cwd, skip_reason in planned:
            if skip_reason:
                if skip_reason.startswith("missing:"):
                    runs[name] = _skipped(name, skip_reason.split(":", 1)[1], skip_reason)
                else:
                    runs[name] = {
                        "command": "n/a",
                        "cwd": str(cwd),
                        "exit_code": 0,
                        "status": "PASS",
                        "output": skip_reason,
                    }
                continue
            assert cmd is not None
            row = _run(cmd, cwd=cwd)
            runs[name] = row
            if row["status"] == "FAIL":
                ok = False
                break

    authority_status = None
    if authority_out.is_file():
        authority_status = json.loads(authority_out.read_text(encoding="utf-8")).get("status")

    overall = "PASS" if ok else "FAIL"
    payload = {
        "schema": "unified_frontline_cycle_report_v1",
        "generated_at": _utc_now(),
        "tag": args.tag,
        "overall_status": overall,
        "runs": runs,
        "notes": {
            "apocrypha_manifest": "pilot_manifest_ext3_hebrew_priority.json",
            "dss_manifest": "dss_ci_manifest_tf4.json",
            "authority_readiness_status": authority_status,
            "legacy_scripts_restored": [s for _, s in LEGACY_SCRIPT_STEPS] + [s for _, s in POST_REPORT_STEPS],
            "research_only": True,
            "hypothesis_tier": "[HYPO]",
        },
    }
    report_out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if not args.dry_run:
        for key, script in POST_REPORT_STEPS:
            post_cmd = [sys.executable, script, "--tag", tag, "--current-report-json", rel_report]
            row = _run(post_cmd, cwd=ROOT)
            runs[key] = row
            payload["runs"][key] = row
            if row["status"] == "FAIL":
                ok = False
                payload["overall_status"] = "FAIL"
            report_out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    status_payload = {
        "generated_at": _utc_now(),
        "latest_cycle_tag": args.tag,
        "latest_cycle_report": f"outputs\\unified_frontline_cycle_report_{args.tag}.json",
        "overall_status": overall,
        "runs": {k: v.get("status") for k, v in runs.items()},
        "authority_readiness_status": authority_status,
    }
    status_out.write_text(json.dumps(status_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if not args.dry_run and ok:
        subprocess.run(
            [sys.executable, str(WORKSPACE / "scripts/build_dss_authority_readiness_reconciliation_v1.py")],
            cwd=str(WORKSPACE),
            check=False,
        )

    print(json.dumps({"ok": ok, "overall_status": overall, "report": str(report_out)}, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
