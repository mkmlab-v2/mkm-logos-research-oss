#!/usr/bin/env python3
"""Build weekly XAI contract operations report from daily gate logs."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LOG = ROOT / "reports" / "xai_contract_daily_gate_log.jsonl"
DEFAULT_OUT_JSON = ROOT / "docs" / "final" / "artifacts" / "xai_contract_weekly_report_latest.json"
DEFAULT_OUT_MD = ROOT / "docs" / "final" / "artifacts" / "xai_contract_weekly_report_latest.md"
DEFAULT_TOP5 = ROOT / "docs" / "final" / "artifacts" / "xai_contract_failures_top5_latest.json"
DEFAULT_MONTHLY_DRILL = ROOT / "docs" / "final" / "artifacts" / "xai_contract_monthly_governance_drill_latest.json"


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_utc(v: str) -> datetime | None:
    try:
        return datetime.fromisoformat(v.replace("Z", "+00:00")).astimezone(timezone.utc)
    except Exception:
        return None


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.is_file():
        return rows
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            rows.append(obj)
    return rows


def _load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        raw = path.read_text(encoding="utf-8")
        raw = raw.lstrip("\ufeff")
        obj = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return obj if isinstance(obj, dict) else {}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--log-jsonl", type=Path, default=DEFAULT_LOG)
    ap.add_argument("--top5-json", type=Path, default=DEFAULT_TOP5)
    ap.add_argument("--window-days", type=int, default=7)
    ap.add_argument("--monthly-drill-json", type=Path, default=DEFAULT_MONTHLY_DRILL)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT_JSON)
    ap.add_argument("--output-md", type=Path, default=DEFAULT_OUT_MD)
    ns = ap.parse_args()

    now = _utc_now()
    cutoff = now - timedelta(days=max(1, ns.window_days))
    logs = _load_jsonl(ns.log_jsonl)
    in_window: list[dict[str, Any]] = []
    for row in logs:
        ts = _parse_utc(str(row.get("ts_utc") or ""))
        if ts and ts >= cutoff:
            in_window.append(row)

    total = len(in_window)
    pass_rows = [r for r in in_window if str(r.get("status")) == "PASS"]
    hold_rows = [r for r in in_window if str(r.get("status")) == "HOLD"]
    warning_rows = [r for r in hold_rows if str(r.get("severity") or "") == "warning"]
    critical_rows = [r for r in hold_rows if str(r.get("severity") or "") == "critical"]

    pass_rate_mean = None
    if total > 0:
        vals = [float(r.get("pass_rate") or 0.0) for r in in_window]
        pass_rate_mean = round(sum(vals) / len(vals), 6)

    top5_doc = _load_json(ns.top5_json)
    action_queue = top5_doc.get("action_queue") if isinstance(top5_doc.get("action_queue"), list) else []
    repeated_question_ids = [a.get("question_id") for a in action_queue if isinstance(a, dict) and a.get("question_id")]
    monthly = _load_json(ns.monthly_drill_json)
    monthly_summary = None
    if monthly:
        m_steps = monthly.get("steps") if isinstance(monthly.get("steps"), list) else []
        monthly_summary = {
            "status": monthly.get("status"),
            "generated_at_utc": monthly.get("generated_at_utc"),
            "step_count": len(m_steps),
            "hold_detected": any(isinstance(s, dict) and s.get("step") == "verify_hold_detected" and s.get("ok") is True for s in m_steps),
            "pass_recovered": any(isinstance(s, dict) and s.get("step") == "verify_pass_recovered" and s.get("ok") is True for s in m_steps),
        }

    out = {
        "schema": "xai_contract_weekly_report_v1",
        "generated_at_utc": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "window_days": ns.window_days,
        "inputs": {
            "log_jsonl": str(ns.log_jsonl.resolve()).replace("\\", "/"),
            "top5_json": str(ns.top5_json.resolve()).replace("\\", "/"),
        },
        "metrics": {
            "total_runs": total,
            "pass_runs": len(pass_rows),
            "hold_runs": len(hold_rows),
            "warning_runs": len(warning_rows),
            "critical_runs": len(critical_rows),
            "pass_rate_mean": pass_rate_mean,
        },
        "top5_repeated_question_ids": repeated_question_ids,
        "monthly_governance_drill": monthly_summary,
    }
    ns.output_json.parent.mkdir(parents=True, exist_ok=True)
    ns.output_json.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    md_lines = [
        "# XAI Contract Weekly Report",
        "",
        f"- generated_at_utc: `{out['generated_at_utc']}`",
        f"- window_days: `{ns.window_days}`",
        "",
        "## Metrics",
        f"- total_runs: `{out['metrics']['total_runs']}`",
        f"- pass_runs: `{out['metrics']['pass_runs']}`",
        f"- hold_runs: `{out['metrics']['hold_runs']}`",
        f"- warning_runs: `{out['metrics']['warning_runs']}`",
        f"- critical_runs: `{out['metrics']['critical_runs']}`",
        f"- pass_rate_mean: `{out['metrics']['pass_rate_mean']}`",
        "",
        "## Repeated Top5 Question IDs",
    ]
    if repeated_question_ids:
        for qid in repeated_question_ids:
            md_lines.append(f"- `{qid}`")
    else:
        md_lines.append("- none")
    md_lines += [
        "",
        "## Monthly Governance Drill",
    ]
    if monthly_summary:
        md_lines += [
            f"- status: `{monthly_summary['status']}`",
            f"- generated_at_utc: `{monthly_summary['generated_at_utc']}`",
            f"- hold_detected: `{monthly_summary['hold_detected']}`",
            f"- pass_recovered: `{monthly_summary['pass_recovered']}`",
            f"- step_count: `{monthly_summary['step_count']}`",
        ]
    else:
        md_lines.append("- unavailable")
    ns.output_md.write_text("\n".join(md_lines) + "\n", encoding="utf-8")

    print(str(ns.output_json.resolve()))
    print(str(ns.output_md.resolve()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
