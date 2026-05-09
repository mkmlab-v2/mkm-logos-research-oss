#!/usr/bin/env python3
"""Build trend summary from darkflow ops history log."""

from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"
ART = ROOT / "docs" / "final" / "artifacts"


def _safe_json(line: str) -> dict[str, Any] | None:
    try:
        obj = json.loads(line)
        return obj if isinstance(obj, dict) else None
    except Exception:
        return None


def main() -> int:
    log_path = REPORTS / "darkflow_ops_history_log.jsonl"
    if not log_path.exists():
        raise FileNotFoundError(f"Missing history log: {log_path}")

    rows: list[dict[str, Any]] = []
    for raw in log_path.read_text(encoding="utf-8").splitlines():
        raw = raw.strip()
        if not raw:
            continue
        obj = _safe_json(raw)
        if obj:
            rows.append(obj)

    window = rows[-20:] if len(rows) > 20 else rows
    if not window:
        raise ValueError("History log is empty")

    single_decisions = [str(r.get("single_policy", "n/a")) for r in window]
    top_hyp = [str(r.get("top_hypothesis", "n/a")) for r in window]
    freshness = [bool(r.get("freshness_passed", False)) for r in window]
    overall = [str(r.get("overall_status", "n/a")) for r in window]

    def _switch_count(seq: list[str]) -> int:
        if len(seq) <= 1:
            return 0
        count = 0
        for i in range(1, len(seq)):
            if seq[i] != seq[i - 1]:
                count += 1
        return count

    trend = {
        "schema": "darkflow_ops_trend_summary_v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "window_size": len(window),
        "single_policy_distribution": dict(Counter(single_decisions)),
        "top_hypothesis_distribution": dict(Counter(top_hyp)),
        "single_policy_switch_count": _switch_count(single_decisions),
        "top_hypothesis_switch_count": _switch_count(top_hyp),
        "freshness_pass_rate": round(sum(1 for x in freshness if x) / len(freshness), 4),
        "overall_status_distribution": dict(Counter(overall)),
        "stability_grade": "STABLE"
        if _switch_count(single_decisions) <= 1 and _switch_count(top_hyp) <= 1
        else "VOLATILE",
        "source_log": str(log_path),
    }

    out_json = ART / "darkflow_ops_trend_summary_latest.json"
    out_md = ART / "darkflow_ops_trend_summary_latest.md"
    out_json.write_text(json.dumps(trend, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# Darkflow Ops Trend Summary",
        "",
        f"- generated_at_utc: `{trend['generated_at_utc']}`",
        f"- window_size: `{trend['window_size']}`",
        f"- stability_grade: `{trend['stability_grade']}`",
        f"- freshness_pass_rate: `{trend['freshness_pass_rate']}`",
        "",
        "## Switch Counts",
        "",
        f"- single_policy_switch_count: `{trend['single_policy_switch_count']}`",
        f"- top_hypothesis_switch_count: `{trend['top_hypothesis_switch_count']}`",
        "",
        "## Distributions",
        "",
        f"- single_policy_distribution: `{trend['single_policy_distribution']}`",
        f"- top_hypothesis_distribution: `{trend['top_hypothesis_distribution']}`",
        f"- overall_status_distribution: `{trend['overall_status_distribution']}`",
        "",
    ]
    out_md.write_text("\n".join(lines), encoding="utf-8")

    print(str(out_json))
    print(str(out_md))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
