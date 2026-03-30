#!/usr/bin/env python3
"""Build root-cause report for token API hydration fallback/none modes."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
MIX = ROOT / "reports" / "constitution" / "btrack_pilot" / "token_api_hydration_mix_latest.json"
LOG = ROOT / "reports" / "constitution" / "btrack_pilot" / "token_api_hydration_mix_log.jsonl"
OUT = ROOT / "reports" / "constitution" / "btrack_pilot" / "token_api_hydration_root_cause_latest.json"


def _load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s:
            continue
        rows.append(json.loads(s.lstrip("\ufeff")))
    return rows


def main() -> int:
    mix = _load_json(MIX)
    rows = mix.get("rows") or []
    if not isinstance(rows, list):
        rows = []
    by_mode = mix.get("metrics_mode_counts") or {}
    root_causes = mix.get("root_cause_counts") or {}
    log_rows = _load_jsonl(LOG)

    none_count = int(by_mode.get("none", 0))
    fallback_count = int(by_mode.get("decision_fallback", 0))
    live_count = int(by_mode.get("live", 0))
    total = int(mix.get("total_examples", 0))

    actions: list[str] = []
    if none_count > 0:
        actions.append("Set eval_context.hydrate_metrics=true on probe examples that must be counted for gate.")
    if fallback_count > 0:
        actions.append("Enable hydrate_live_eval=true for target examples, keep decision fallback for safety.")
    actions.append("Keep shadow compare enabled to collect live-path evidence without changing response path.")

    out = {
        "schema": "token_api_hydration_root_cause_v1",
        "ts_utc": datetime.now(timezone.utc).isoformat(),
        "source_mix": "reports/constitution/btrack_pilot/token_api_hydration_mix_latest.json",
        "source_log": "reports/constitution/btrack_pilot/token_api_hydration_mix_log.jsonl",
        "snapshot": {
            "total_examples": total,
            "metrics_mode_counts": by_mode,
            "root_cause_counts": root_causes,
            "live_ratio": float(mix.get("live_ratio", 0.0)),
        },
        "window": {
            "observed_rows": len(log_rows),
            "rows_required_for_arming": 10,
        },
        "top_issues": [
            {"issue": "none_mode", "count": none_count},
            {"issue": "decision_fallback_mode", "count": fallback_count},
            {"issue": "live_mode", "count": live_count},
        ],
        "recommended_actions": actions,
        "note": "Root-cause first report for shadow rollout; no gate-threshold override is performed.",
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
