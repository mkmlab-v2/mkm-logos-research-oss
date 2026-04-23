#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_md(path: Path, data: dict[str, Any]) -> None:
    g = data.get("go_no_go") or {}
    o = data.get("ops_alert_summary") or {}
    f = data.get("freeze_vfinal") or {}
    s = data.get("observation_streak") or {}
    lines = [
        "# Canon Promotion Approval Pack v1",
        "",
        f"- generated_at_utc: {data.get('generated_at_utc')}",
        f"- verdict: {data.get('verdict')}",
        "",
        "## Core Snapshot",
        f"- go_no_go_verdict: {g.get('verdict')}",
        f"- ops_alert: {o.get('ops_alert')}",
        f"- ops_severity: {o.get('severity')}",
        f"- freeze_vfinal_decision: {f.get('freeze_decision')}",
        f"- observation_streak_verdict: {s.get('verdict')}",
        f"- three_day_unattended_pass: {s.get('three_day_unattended_pass')}",
        "",
        "## Included Artifacts",
    ]
    for a in list(data.get("included_artifacts") or []):
        lines.append(f"- {a}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description="Build one-page promotion approval pack from finalized operational artifacts.")
    ap.add_argument(
        "--go-no-go-json",
        default="docs/final/artifacts/original_corpus_regime_singularity_canon_promotion_go_no_go_v1.json",
    )
    ap.add_argument(
        "--rehearsal-latest-json",
        default="docs/final/artifacts/original_corpus_regime_singularity_canon_rehearsal_status_latest.json",
    )
    ap.add_argument(
        "--ops-alert-runbook-json",
        default="docs/final/artifacts/original_corpus_regime_singularity_canon_ops_alert_runbook_latest.json",
    )
    ap.add_argument(
        "--freeze-vfinal-json",
        default="docs/final/artifacts/original_corpus_regime_singularity_canon_strict_baseline_freeze_vfinal_v1.json",
    )
    ap.add_argument(
        "--freeze-generation-diff-json",
        default="docs/final/artifacts/original_corpus_regime_singularity_canon_strict_baseline_freeze_generation_diff_vfinal_v1.json",
    )
    ap.add_argument(
        "--observation-streak-json",
        default="docs/final/artifacts/original_corpus_regime_singularity_canon_observation_streak_report_v1.json",
    )
    ap.add_argument(
        "--output-json",
        default="docs/final/artifacts/original_corpus_regime_singularity_canon_promotion_approval_pack_v1.json",
    )
    ap.add_argument(
        "--output-md",
        default="docs/final/artifacts/original_corpus_regime_singularity_canon_promotion_approval_pack_v1.md",
    )
    args = ap.parse_args()

    go_no_go = _read_json(Path(args.go_no_go_json))
    rehearsal = _read_json(Path(args.rehearsal_latest_json))
    runbook = _read_json(Path(args.ops_alert_runbook_json))
    freeze_vfinal = _read_json(Path(args.freeze_vfinal_json))
    gen_diff = _read_json(Path(args.freeze_generation_diff_json))
    streak = _read_json(Path(args.observation_streak_json))
    streak_metrics = dict(streak.get("metrics") or {})
    three_day_unattended_pass = (
        str(streak.get("verdict") or "") == "pass"
        and int(streak_metrics.get("window") or 0) >= 3
        and int(streak_metrics.get("pass_count") or 0) >= 3
        and str(streak_metrics.get("latest_verdict") or "") == "pass"
    )

    verdict = "approved" if str(go_no_go.get("verdict") or "") == "go" else "hold"
    out = {
        "schema": "original_corpus_regime_singularity_canon_promotion_approval_pack_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "verdict": verdict,
        "go_no_go": {
            "verdict": str(go_no_go.get("verdict") or "missing"),
            "hold_reasons": list(go_no_go.get("hold_reasons") or []),
            "generated_at_utc": str(go_no_go.get("generated_at_utc") or ""),
        },
        "ops_alert_summary": dict((rehearsal.get("ops_alert_summary") or runbook.get("ops_alert_summary") or {})),
        "freeze_vfinal": {
            "freeze_decision": str(freeze_vfinal.get("freeze_decision") or "missing"),
            "generated_at_utc": str(freeze_vfinal.get("generated_at_utc") or ""),
        },
        "freeze_generation_diff": {
            "total_change_count": int(gen_diff.get("total_change_count") or 0),
            "generated_at_utc": str(gen_diff.get("generated_at_utc") or ""),
        },
        "observation_streak": {
            "verdict": str(streak.get("verdict") or "missing"),
            "metrics": streak_metrics,
            "three_day_unattended_pass": three_day_unattended_pass,
            "generated_at_utc": str(streak.get("generated_at_utc") or ""),
        },
        "included_artifacts": [
            str(args.go_no_go_json),
            str(args.rehearsal_latest_json),
            str(args.ops_alert_runbook_json),
            str(args.freeze_vfinal_json),
            str(args.freeze_generation_diff_json),
            str(args.observation_streak_json),
        ],
    }
    _write_json(Path(args.output_json), out)
    _write_md(Path(args.output_md), out)
    print(str(args.output_json))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

