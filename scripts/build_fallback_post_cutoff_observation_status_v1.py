#!/usr/bin/env python3
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"

WATCH_JSON = ART / "fallback_post_cutoff_watch_report_latest.json"
DIAG_JSON = ART / "fallback_post_cutoff_diagnosis_latest.json"
OUT_JSON = ART / "fallback_post_cutoff_observation_status_latest.json"
OUT_MD = ART / "fallback_post_cutoff_observation_status_latest.md"

TARGET_POST_CUTOFF_RATE = 0.15
TARGET_SIGNAL = {"GO", "WATCH"}
MIN_OBSERVED_ROWS = 50


def _iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return {}
    return obj if isinstance(obj, dict) else {}


def main() -> int:
    watch = _read_json(WATCH_JSON)
    diag = _read_json(DIAG_JSON)

    watch_summary = watch.get("summary") or {}
    diag_summary = diag.get("summary") or {}

    signal = str(watch_summary.get("signal") or "UNKNOWN")
    trigger_rate = float(diag_summary.get("trigger_rate") or 0.0)
    rows_total = int(diag_summary.get("rows_total") or 0)

    checks = {
        "signal_not_critical": signal in TARGET_SIGNAL,
        "post_cutoff_trigger_rate_ok": trigger_rate <= TARGET_POST_CUTOFF_RATE,
        "sample_size_ok": rows_total >= MIN_OBSERVED_ROWS,
    }
    passed = all(checks.values())
    decision = "GO_OBSERVATION_COMPLETE" if passed else "HOLD_OBSERVATION_CONTINUE"

    out = {
        "schema": "fallback_post_cutoff_observation_status_v1",
        "generated_at_utc": _iso_now(),
        "inputs": {
            "watch_report": str(WATCH_JSON).replace("\\", "/"),
            "diagnosis_report": str(DIAG_JSON).replace("\\", "/"),
        },
        "targets": {
            "target_signal_allowed": sorted(TARGET_SIGNAL),
            "target_post_cutoff_trigger_rate_lte": TARGET_POST_CUTOFF_RATE,
            "minimum_observed_rows": MIN_OBSERVED_ROWS,
        },
        "observed": {
            "signal": signal,
            "post_cutoff_trigger_rate": trigger_rate,
            "rows_total": rows_total,
        },
        "checks": checks,
        "decision": decision,
    }
    OUT_JSON.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    md = [
        "# Fallback Post-Cutoff Observation Status",
        "",
        f"- decision: `{decision}`",
        f"- observed.signal: `{signal}`",
        f"- observed.post_cutoff_trigger_rate: `{trigger_rate}`",
        f"- observed.rows_total: `{rows_total}`",
        "",
        "## Checks",
        f"- signal_not_critical: `{checks['signal_not_critical']}`",
        f"- post_cutoff_trigger_rate_ok: `{checks['post_cutoff_trigger_rate_ok']}`",
        f"- sample_size_ok: `{checks['sample_size_ok']}`",
    ]
    OUT_MD.write_text("\n".join(md) + "\n", encoding="utf-8")
    print(str(OUT_JSON))
    print(str(OUT_MD))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
