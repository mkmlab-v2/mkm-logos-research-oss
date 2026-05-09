from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


def _iso_z(dt: datetime) -> str:
    return dt.isoformat().replace("+00:00", "Z")


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    for line in path.read_text(encoding="utf-8-sig").splitlines():
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


def _parse_ts(value: Any) -> datetime | None:
    if value is None:
        return None
    s = str(value).strip()
    if not s:
        return None
    try:
        if s.endswith("Z"):
            return datetime.fromisoformat(s.replace("Z", "+00:00"))
        return datetime.fromisoformat(s)
    except ValueError:
        return None


def _classify(reason: str) -> str:
    r = reason.lower()
    if "filenotfounderror" in r or "json file not found" in r or "missing" in r:
        return "missing_artifact_or_contract"
    if "timeout" in r:
        return "timeout"
    if "permission" in r or "access is denied" in r or "액세스가 거부" in r:
        return "permission_or_access"
    if "webhook" in r:
        return "webhook_dependency"
    if "traceback" in r:
        return "python_runtime_error"
    if "exit=1" in r:
        return "generic_exit_1"
    return "unknown"


def build() -> int:
    root = Path("C:/workspace")
    reports = root / "reports"
    art = root / "docs" / "final" / "artifacts"
    art.mkdir(parents=True, exist_ok=True)

    now = _utc_now()
    window_start = now - timedelta(days=7)

    core_history = _read_jsonl(reports / "core_task_health_history_v1.jsonl")
    fusion_rows = [
        r
        for r in core_history
        if str(r.get("task_name")) == "MKM-TrackC-MacroDailyFusion"
        and (_parse_ts(r.get("ts_utc")) or datetime.min.replace(tzinfo=timezone.utc)) >= window_start
    ]
    total_samples = len(fusion_rows)
    failed_rows = [r for r in fusion_rows if str(r.get("result_category")) != "OK"]

    fragility_fails = [
        r
        for r in _read_jsonl(reports / "fragility_macro_risk_daily_failures.jsonl")
        if (_parse_ts(r.get("ts_utc")) or datetime.min.replace(tzinfo=timezone.utc)) >= window_start
    ]

    latest_chain_error_path = reports / "fragility_macro_risk_chain_error_latest.log"
    latest_chain_error_text = latest_chain_error_path.read_text(encoding="utf-8-sig") if latest_chain_error_path.exists() else ""

    reason_counts: dict[str, int] = {}
    samples: list[dict[str, Any]] = []

    for r in fragility_fails:
        raw = str(r.get("error") or "")
        category = _classify(raw)
        reason_counts[category] = reason_counts.get(category, 0) + 1
        samples.append(
            {
                "ts_utc": r.get("ts_utc"),
                "source": "fragility_macro_risk_daily_failures.jsonl",
                "raw_reason": raw,
                "category": category,
            }
        )

    if latest_chain_error_text.strip():
        category = _classify(latest_chain_error_text)
        reason_counts[category] = reason_counts.get(category, 0) + 1
        samples.append(
            {
                "ts_utc": _iso_z(now),
                "source": "fragility_macro_risk_chain_error_latest.log",
                "raw_reason": latest_chain_error_text.strip(),
                "category": category,
            }
        )

    # Derive top issue
    top_category = None
    if reason_counts:
        top_category = sorted(reason_counts.items(), key=lambda x: x[1], reverse=True)[0][0]

    recommendations = []
    if top_category == "missing_artifact_or_contract":
        recommendations.append("Ensure contract/matrix artifacts are bootstrapped before policy binding.")
        recommendations.append("Keep bootstrap fallback in run_fragility_macro_risk_chain_v1.ps1.")
    if top_category == "python_runtime_error":
        recommendations.append("Capture and persist full traceback per failing step for deterministic triage.")
    if not recommendations:
        recommendations.append("Continue monitoring; no dominant failure class in last 7 days.")

    out = {
        "schema": "trackc_macro_fusion_failure_breakdown_v1",
        "generated_at_utc": _iso_z(now),
        "window": {
            "start_utc": _iso_z(window_start),
            "end_utc": _iso_z(now),
            "days": 7,
        },
        "fusion_task_stats": {
            "total_samples_7d": total_samples,
            "failed_samples_7d": len(failed_rows),
            "success_samples_7d": total_samples - len(failed_rows),
            "success_rate_percent_7d": round(((total_samples - len(failed_rows)) / total_samples) * 100.0, 2)
            if total_samples > 0
            else None,
        },
        "failure_breakdown": {
            "reason_counts": reason_counts,
            "top_category": top_category,
            "sample_count": len(samples),
            "samples": samples[-10:],
        },
        "recommendations": recommendations,
        "evidence": {
            "core_history_jsonl": "reports/core_task_health_history_v1.jsonl",
            "fragility_failures_jsonl": "reports/fragility_macro_risk_daily_failures.jsonl",
            "latest_chain_error_log": "reports/fragility_macro_risk_chain_error_latest.log",
        },
    }

    out_json = art / "trackc_macro_fusion_failure_breakdown_latest.json"
    out_md = art / "trackc_macro_fusion_failure_breakdown_latest.md"
    out_json.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    md_lines = [
        "# TrackC Macro Fusion Failure Breakdown",
        "",
        f"- generated_at_utc: `{out['generated_at_utc']}`",
        f"- success_rate_percent_7d: `{out['fusion_task_stats']['success_rate_percent_7d']}`",
        f"- failed_samples_7d: `{out['fusion_task_stats']['failed_samples_7d']}`",
        f"- top_failure_category: `{top_category}`",
        "",
        "## Reason Counts",
    ]
    for k, v in sorted(reason_counts.items(), key=lambda x: x[1], reverse=True):
        md_lines.append(f"- `{k}`: {v}")
    md_lines.append("")
    md_lines.append("## Recommendations")
    for rec in recommendations:
        md_lines.append(f"- {rec}")
    out_md.write_text("\n".join(md_lines) + "\n", encoding="utf-8")

    print(f"wrote: {out_json}")
    print(f"wrote: {out_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(build())

