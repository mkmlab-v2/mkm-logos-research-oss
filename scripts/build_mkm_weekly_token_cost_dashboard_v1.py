#!/usr/bin/env python3
"""One-page internal weekly token-cost dashboard (metering · band gate · context diet · cost sim)."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _pct(rate: float | None, digits: int = 1) -> str:
    if rate is None:
        return "n/a"
    return f"{rate * 100:.{digits}f}%"


def _status_emoji(ok: bool | None, warn: bool = False) -> str:
    if ok is True:
        return "GREEN"
    if warn:
        return "YELLOW"
    return "RED"


def build_payload(root: Path) -> dict[str, Any]:
    art = root / "docs/final/artifacts"
    reports = root / "reports"

    metering_summary = _read(art / "track_a_metering_summary_latest.json")
    metering_weekly = _read(art / "track_a_metering_weekly_report_latest.json")
    band_gate = _read(art / "track_a_metering_band_gate_latest.json")
    cost_sim = _read(art / "track_a_conversational_cost_simulation_latest.json")
    signal_light = _read(art / "track_a_signal_light_report_latest.json")
    context_diet = _read(reports / "cursor_rules_context_diet_v1_latest.json")
    active_report = _read(art / "MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json")

    bench_saving = None
    bench_jaccard = None
    if active_report:
        metrics = active_report.get("compression_metrics") or {}
        bench_saving = metrics.get("global_token_saving_rate")
        bench_jaccard = metrics.get("avg_reconstruction_fidelity_jaccard")

    min_hit = (band_gate or {}).get("min_hit_rate")
    weekly_hit = (metering_weekly or {}).get("target_band_hit_rate")
    band_ok = weekly_hit is not None and min_hit is not None and weekly_hit >= min_hit

    diet_ok = bool((context_diet or {}).get("ok"))
    diet_violations = (context_diet or {}).get("violations") or []

    cost_go = str((cost_sim or {}).get("gate_decision") or "").upper() == "GO"

    blocks = {
        "metering": {
            "status": "YELLOW" if (metering_weekly or {}).get("events_in_window", 0) < 20 else "GREEN",
            "events_total": (metering_summary or {}).get("events_total"),
            "events_in_window_7d": (metering_weekly or {}).get("events_in_window"),
            "weekly_hit_rate": weekly_hit,
            "min_hit_rate": min_hit,
            "source": (metering_weekly or {}).get("source"),
        },
        "band_gate": {
            "status": str((band_gate or {}).get("decision") or "unknown").upper(),
            "mode": (band_gate or {}).get("mode"),
            "passes_min_hit_rate": band_ok,
        },
        "context_diet": {
            "status": "GREEN" if diet_ok else "YELLOW" if (context_diet or {}).get("status") == "WARN" else "RED",
            "always_apply_count": (context_diet or {}).get("always_apply_count"),
            "always_apply_lines": (context_diet or {}).get("always_apply_lines"),
            "cursorrules_lines": ((context_diet or {}).get("inject_docs") or {}).get("cursorrules_lines"),
            "violations": diet_violations,
        },
        "cost_sim": {
            "status": "GREEN" if cost_go else "YELLOW",
            "gate_decision": (cost_sim or {}).get("gate_decision"),
            "bench_saving_rate": (cost_sim or {}).get("global_token_saving_rate") or bench_saving,
            "bench_jaccard": bench_jaccard,
            "hypothesis_monthly_baseline_tokens": (cost_sim or {}).get("hypothesis_monthly_baseline_tokens"),
            "hypothesis_monthly_after_tokens": (cost_sim or {}).get("hypothesis_monthly_after_tokens"),
            "note": (cost_sim or {}).get("note"),
        },
    }

    sl = (signal_light or {}).get("signal_light") or {}
    overall = sl.get("status") if isinstance(sl, dict) else "YELLOW"

    next_actions: list[str] = []
    if not band_ok:
        next_actions.append(
            "Metering: append real compress/eval rows to track_a_metering_log_v1.jsonl until 7d hit_rate >= 0.85."
        )
    if not diet_ok:
        next_actions.append(
            "Context diet: slim .cursorrules toward template budget (cursorrules_lines <= 70); re-run check --strict."
        )
    if (metering_weekly or {}).get("events_in_window", 0) < 20:
        next_actions.append(
            "Live traffic: wire POST /v1/compress eval_context.meter_log on internal pilot paths (not bench-only)."
        )
    if not next_actions:
        next_actions.append("Maintain weekly chain; begin B2B metered pilot ROI with run_compression_pilot_roi_chain_v1.py.")

    return {
        "schema": "mkm_weekly_token_cost_dashboard_v1",
        "generated_at_utc": _utc(),
        "overall_signal_light": overall,
        "blocks": blocks,
        "fail_comp_004_reminder": "Golden-40 ~47.5% is internal bench KPI only — not billing, live routing, or external SLA.",
        "next_actions": next_actions,
        "reproducible_commands": [
            "powershell -File scripts/run_track_a_commercialization_daily_chain.ps1",
            "py scripts/run_track_a_metering_live_wire_v1.py",
            "py scripts/run_track_a_conversational_cost_simulation.py",
            "py scripts/check_cursor_rules_context_diet_v1.py --strict",
            "py scripts/build_mkm_weekly_token_cost_dashboard_v1.py",
        ],
        "artifact_paths": {
            "metering_summary": str(art / "track_a_metering_summary_latest.json"),
            "metering_weekly": str(art / "track_a_metering_weekly_report_latest.json"),
            "band_gate": str(art / "track_a_metering_band_gate_latest.json"),
            "cost_sim": str(art / "track_a_conversational_cost_simulation_latest.json"),
            "context_diet": str(reports / "cursor_rules_context_diet_v1_latest.json"),
            "signal_light": str(art / "track_a_signal_light_report_latest.json"),
        },
    }


def render_markdown(doc: dict[str, Any]) -> str:
    b = doc["blocks"]
    m, g, d, c = b["metering"], b["band_gate"], b["context_diet"], b["cost_sim"]
    lines = [
        "# MKM 주간 토큰 비용 대시보드 (내부 1장)",
        "",
        f"**생성:** {doc['generated_at_utc']} · **종합:** {doc['overall_signal_light']}",
        "",
        "> FAIL-COMP-004: Golden-40 ~47.5% = 내부 벤치 KPI. 실청구·live routing·대외 SLA 아님.",
        "",
        "## 1. Metering (실계량)",
        "",
        f"| 항목 | 값 |",
        f"|------|-----|",
        f"| 상태 | **{m['status']}** |",
        f"| 누적 이벤트 | {m.get('events_total', 'n/a')} |",
        f"| 7일 윈도우 이벤트 | {m.get('events_in_window_7d', 'n/a')} |",
        f"| 7일 band hit rate | {_pct(m.get('weekly_hit_rate'))} (목표 ≥ {_pct(m.get('min_hit_rate'))}) |",
        f"| 소스 | `{m.get('source', 'n/a')}` |",
        "",
        "## 2. Band gate",
        "",
        f"| 항목 | 값 |",
        f"|------|-----|",
        f"| 상태 | **{g['status']}** (mode={g.get('mode')}) |",
        f"| min_hit_rate 통과 | {'YES' if g.get('passes_min_hit_rate') else 'NO'} |",
        "",
        "## 3. Context diet (에이전트 오버헤드)",
        "",
        f"| 항목 | 값 |",
        f"|------|-----|",
        f"| 상태 | **{d['status']}** |",
        f"| alwaysApply 규칙 | {d.get('always_apply_count')}개 / {d.get('always_apply_lines')}줄 |",
        f"| .cursorrules | {d.get('cursorrules_lines')}줄 (예산 ≤ 70) |",
        f"| violations | {', '.join(d.get('violations') or []) or 'none'} |",
        "",
        "## 4. Cost sim (벤치 연계 시나리오)",
        "",
        f"| 항목 | 값 |",
        f"|------|-----|",
        f"| 상태 | **{c['status']}** |",
        f"| KPI gate | {c.get('gate_decision')} |",
        f"| bench saving (Golden-40) | {_pct(c.get('bench_saving_rate'))} |",
        f"| bench Jaccard | {_pct(c.get('bench_jaccard'))} |",
        f"| 가정: 월 1M tok → 압축 후 | {c.get('hypothesis_monthly_after_tokens', 'n/a'):,} tok |",
        f"| 비고 | {c.get('note', '')} |",
        "",
        "## 다음 1타",
        "",
    ]
    for i, action in enumerate(doc.get("next_actions") or [], 1):
        lines.append(f"{i}. {action}")
    lines.extend(
        [
            "",
            "## 재현 명령",
            "",
            "```powershell",
            "powershell -File scripts\\run_track_a_commercialization_daily_chain.ps1",
            "py scripts/run_track_a_conversational_cost_simulation.py",
            "py scripts/check_cursor_rules_context_diet_v1.py --strict",
            "py scripts/build_mkm_weekly_token_cost_dashboard_v1.py",
            "```",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workspace-root", type=Path, default=Path(__file__).resolve().parents[1])
    ap.add_argument("--out-json", type=Path, default=None)
    ap.add_argument("--out-md", type=Path, default=None)
    args = ap.parse_args()
    root = args.workspace_root.resolve()
    out_json = (args.out_json or root / "reports/mkm_weekly_token_cost_dashboard_v1_latest.json").resolve()
    out_md = (args.out_md or root / "reports/mkm_weekly_token_cost_dashboard_v1_latest.md").resolve()

    doc = build_payload(root)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    out_md.write_text(render_markdown(doc), encoding="utf-8")
    print(f"Wrote {out_json}")
    print(f"Wrote {out_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
