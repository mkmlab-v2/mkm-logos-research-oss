#!/usr/bin/env python3
"""Build Han Vocology KM-VHI pilot final report (B-track · M19)."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CLOSURE = ROOT / "reports/han_vocology_pilot_closure_v1_latest.json"
GATE = ROOT / "reports/han_vocology_km_vhi_pilot_cohort_gate_v1_latest.json"
SUMMARY = ROOT / "reports/han_vocology_km_vhi_pilot_summary_v1_latest.json"
REGISTRY = ROOT / "docs/final/artifacts/han_vocology_multisite_registry_v1_latest.json"
COMPLETION = ROOT / "docs/final/artifacts/han_vocology_completion_status_v1_latest.json"
OUT_JSON = ROOT / "reports/han_vocology_pilot_final_report_v1_latest.json"
OUT_MD = ROOT / "reports/han_vocology_pilot_final_report_v1_latest.md"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _cohort_rows(gate: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "pseudonym_id": c.get("pseudonym_id"),
            "cb_id": c.get("cb_id"),
            "policy": c.get("clinical_policy"),
            "delta_w8": c.get("delta_pct_week8"),
            "delta_w12": c.get("delta_pct_week12"),
            "band_w8": c.get("band_week8"),
            "visit_weeks": c.get("visit_weeks"),
        }
        for c in gate.get("cohorts") or []
    ]


def build_report(
    *,
    closure: dict[str, Any],
    gate: dict[str, Any],
    summary: dict[str, Any],
    registry: dict[str, Any],
    completion: dict[str, Any],
) -> dict[str, Any]:
    policies = Counter(str(c.get("clinical_policy")) for c in gate.get("cohorts") or [])
    week12_n = int(closure.get("week12_followup_count") or 0)
    cohort_n = int(closure.get("cohort_count") or 0)

    ok = (
        bool(closure.get("ok"))
        and bool(gate.get("ok"))
        and bool(closure.get("cb_full_bank_complete"))
        and int(closure.get("row_count") or 0) >= 53
        and int(gate.get("excellent_at_week8") or 0) == int(gate.get("cohort_count") or 0)
        and closure.get("send_gate") == "HOLD"
    )

    return {
        "schema": "han_vocology_pilot_final_report_v1",
        "ok": ok,
        "track": "B",
        "send_gate": "HOLD",
        "patient_facing": "blocked",
        "generated_at_utc": _utc(),
        "executive": {
            "row_count": closure.get("row_count"),
            "cohort_count": cohort_n,
            "site_count": closure.get("site_count"),
            "cb_ids": closure.get("cb_ids"),
            "cb_full_bank_complete": closure.get("cb_full_bank_complete"),
            "gate_excellent_w8": f"{gate.get('excellent_at_week8')}/{gate.get('cohort_count')}",
            "week12_followup": f"{week12_n}/{cohort_n}",
            "policy_distribution": dict(sorted(policies.items())),
            "registry_version": registry.get("version"),
            "milestones_through": "M23",
            "appendix_cb_crosscheck": "docs/final/artifacts/han_vocology_cb_dashboard_pilot_crosscheck_v1_latest.json",
        },
        "cohorts": _cohort_rows(gate),
        "artifacts": {
            "jsonl": "reports/han_vocology_km_vhi_pilot_records.jsonl",
            "closure": str(CLOSURE.relative_to(ROOT)).replace("\\", "/"),
            "gate": str(GATE.relative_to(ROOT)).replace("\\", "/"),
            "summary": str(SUMMARY.relative_to(ROOT)).replace("\\", "/"),
            "registry": str(REGISTRY.relative_to(ROOT)).replace("\\", "/"),
            "completion": str(COMPLETION.relative_to(ROOT)).replace("\\", "/"),
        },
        "completion_milestones_pass": [
            k for k, v in (completion.get("milestones") or {}).items() if v.get("status") == "pass"
        ],
        "disclaimer_ko": (
            "교육·[HYPO] 파일럿 최종 리포트 — KM-VHI 구조·정책 일관성 증거만. "
            "임상 효능·IRB·send_gate 해제·Track A 승격을 의미하지 않음."
        ),
        "reproduce": [
            "py scripts/validate_han_vocology_km_vhi_pilot_jsonl_v1.py",
            "py scripts/build_han_vocology_km_vhi_pilot_cohort_gate_v1.py",
            "py scripts/build_han_vocology_pilot_closure_v1.py",
            "py scripts/check_han_vocology_appendix_cb_dashboard_vs_pilot_v1.py",
            "py scripts/build_han_vocology_pilot_final_report_v1.py",
        ],
    }


def render_md(report: dict[str, Any]) -> str:
    ex = report.get("executive") or {}
    lines = [
        "# 한의음성학 KM-VHI 파일럿 최종 리포트 (M23)",
        "",
        f"- **Status:** `{'PASS' if report.get('ok') else 'FAIL'}` · Track B · send_gate HOLD",
        f"- **Generated:** {report.get('generated_at_utc')}",
        "",
        "## Executive",
        "",
        f"| 항목 | 값 |",
        f"|------|-----|",
        f"| JSONL rows | {ex.get('row_count')} |",
        f"| Cohorts | {ex.get('cohort_count')} |",
        f"| Sites | {ex.get('site_count')} |",
        f"| CB full bank | {ex.get('cb_full_bank_complete')} |",
        f"| Gate w8 excellent | {ex.get('gate_excellent_w8')} |",
        f"| Week-12 follow-up | {ex.get('week12_followup')} |",
        "",
        "## Policy distribution",
        "",
    ]
    for pol, cnt in sorted((ex.get("policy_distribution") or {}).items()):
        lines.append(f"- **{pol}:** {cnt}")
    lines.extend(["", "## Cohort table (Δ% vs week-0)", "", "| cohort | CB | policy | w8 Δ% | w12 Δ% | band w8 |"])
    for c in report.get("cohorts") or []:
        w8 = c.get("delta_w8")
        w12 = c.get("delta_w12")
        lines.append(
            f"| {c.get('pseudonym_id')} | {c.get('cb_id')} | {c.get('policy')} | "
            f"{w8 if w8 is not None else '—'} | {w12 if w12 is not None else '—'} | {c.get('band_w8') or '—'} |"
        )
    lines.extend(
        [
            "",
            "## Disclaimer",
            "",
            report.get("disclaimer_ko", ""),
            "",
            "## Reproduce",
            "",
        ]
    )
    for cmd in report.get("reproduce") or []:
        lines.append(f"```text\n{cmd}\n```")
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--skip-validate", action="store_true")
    ap.add_argument("--out-json", type=Path, default=OUT_JSON)
    ap.add_argument("--out-md", type=Path, default=OUT_MD)
    args = ap.parse_args()

    if not args.skip_validate:
        for script in (
            "validate_han_vocology_km_vhi_pilot_jsonl_v1.py",
            "build_han_vocology_km_vhi_pilot_cohort_gate_v1.py",
            "build_han_vocology_pilot_closure_v1.py",
            "check_han_vocology_appendix_cb_dashboard_vs_pilot_v1.py",
        ):
            proc = subprocess.run(
                [sys.executable, str(ROOT / "scripts" / script)],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            if proc.returncode != 0:
                print(proc.stdout or proc.stderr)
                return 1
        subprocess.run(
            [sys.executable, str(ROOT / "scripts/summarize_han_vocology_km_vhi_pilot_jsonl_v1.py")],
            cwd=ROOT,
            check=False,
        )

    for path in (CLOSURE, GATE, SUMMARY):
        if not path.is_file():
            print(json.dumps({"ok": False, "error": f"missing:{path.name}"}, ensure_ascii=False))
            return 1

    report = build_report(
        closure=_load(CLOSURE),
        gate=_load(GATE),
        summary=_load(SUMMARY),
        registry=_load(REGISTRY) if REGISTRY.is_file() else {},
        completion=_load(COMPLETION) if COMPLETION.is_file() else {},
    )

    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.out_md.write_text(render_md(report), encoding="utf-8")

    print(
        json.dumps(
            {
                "ok": report["ok"],
                "row_count": report["executive"]["row_count"],
                "cohort_count": report["executive"]["cohort_count"],
                "out_json": str(args.out_json),
                "out_md": str(args.out_md),
            },
            ensure_ascii=False,
        )
    )
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
