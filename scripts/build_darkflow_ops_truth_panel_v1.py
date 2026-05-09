#!/usr/bin/env python3
"""Build Dark Flow ops truth panel with freshness and consistency checks."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _safe_load(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return _load(path)
    except Exception:
        return {}


def _parse_iso(s: str | None) -> datetime | None:
    if not s:
        return None
    try:
        return datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    except Exception:
        return None


def _age_hours(ts: datetime | None, now: datetime) -> float | None:
    if ts is None:
        return None
    return round((now - ts).total_seconds() / 3600.0, 3)


def main() -> int:
    now = datetime.now(timezone.utc)
    gate = _safe_load(ART / "darkflow_btrack_gate_latest.json")
    dual = _safe_load(ART / "darkflow_btrack_dual_policy_report_latest.json")
    snap = _safe_load(ART / "darkflow_btrack_status_snapshot_latest.json")
    eval_latest = _safe_load(ART / "darkflow_btrack_eval_latest.json")

    gate_ts = _parse_iso(gate.get("checked_at_utc"))
    dual_ts = _parse_iso(dual.get("generated_at_utc"))
    snap_ts = _parse_iso(snap.get("generated_at_utc"))
    eval_ts = _parse_iso(eval_latest.get("generated_at_utc"))

    gate_age_h = _age_hours(gate_ts, now)
    dual_age_h = _age_hours(dual_ts, now)
    snap_age_h = _age_hours(snap_ts, now)
    eval_age_h = _age_hours(eval_ts, now)

    freshness_threshold_h = 36.0
    freshness_failures: list[str] = []
    for name, age in (
        ("gate_age_h", gate_age_h),
        ("dual_age_h", dual_age_h),
        ("snapshot_age_h", snap_age_h),
        ("eval_age_h", eval_age_h),
    ):
        if age is None:
            freshness_failures.append(f"missing_{name}")
        elif age > freshness_threshold_h:
            freshness_failures.append(f"stale_{name}")

    decision_single = str(gate.get("decision", "n/a"))
    decision_conservative = str((dual.get("conservative") or {}).get("decision", "n/a"))
    decision_exploratory = str((dual.get("exploratory") or {}).get("decision", "n/a"))
    top_h = (gate.get("ranked_hypotheses") or [{}])[0].get("label", "n/a") if isinstance(gate.get("ranked_hypotheses"), list) else "n/a"

    panel = {
        "schema": "darkflow_ops_truth_panel_v1",
        "generated_at_utc": now.isoformat().replace("+00:00", "Z"),
        "source_track": "B",
        "observation_mode": "RESEARCH_ONLY",
        "auto_bind_to_atrack_forbidden": True,
        "decisions": {
            "single_policy": decision_single,
            "conservative_policy": decision_conservative,
            "exploratory_policy": decision_exploratory,
            "top_hypothesis": top_h,
        },
        "freshness": {
            "threshold_hours": freshness_threshold_h,
            "gate_age_h": gate_age_h,
            "dual_age_h": dual_age_h,
            "snapshot_age_h": snap_age_h,
            "eval_age_h": eval_age_h,
            "failures": freshness_failures,
            "freshness_passed": len(freshness_failures) == 0,
        },
        "overall_status": "PASS" if len(freshness_failures) == 0 else "WARN_STALE_OR_MISSING",
        "evidence_paths": {
            "gate_json": str(ART / "darkflow_btrack_gate_latest.json"),
            "dual_json": str(ART / "darkflow_btrack_dual_policy_report_latest.json"),
            "snapshot_json": str(ART / "darkflow_btrack_status_snapshot_latest.json"),
            "eval_json": str(ART / "darkflow_btrack_eval_latest.json"),
        },
    }

    out_json = ART / "darkflow_ops_truth_panel_latest.json"
    out_md = ART / "darkflow_ops_truth_panel_latest.md"
    out_json.write_text(json.dumps(panel, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# Darkflow Ops Truth Panel",
        "",
        f"- generated_at_utc: `{panel['generated_at_utc']}`",
        f"- overall_status: `{panel['overall_status']}`",
        f"- single_policy: `{decision_single}`",
        f"- conservative_policy: `{decision_conservative}`",
        f"- exploratory_policy: `{decision_exploratory}`",
        f"- top_hypothesis: `{top_h}`",
        "",
        "## Freshness",
        "",
        f"- threshold_hours: `{freshness_threshold_h}`",
        f"- gate_age_h: `{gate_age_h}`",
        f"- dual_age_h: `{dual_age_h}`",
        f"- snapshot_age_h: `{snap_age_h}`",
        f"- eval_age_h: `{eval_age_h}`",
        f"- freshness_passed: `{len(freshness_failures) == 0}`",
        "",
        "## Failures",
        "",
    ]
    if freshness_failures:
        lines.extend([f"- `{f}`" for f in freshness_failures])
    else:
        lines.append("- none")
    lines.append("")
    out_md.write_text("\n".join(lines), encoding="utf-8")

    print(str(out_json))
    print(str(out_md))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
