from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def build() -> int:
    root = Path("C:/workspace")
    art = root / "docs" / "final" / "artifacts"
    art.mkdir(parents=True, exist_ok=True)

    baseline = _read_json(art / "cursor_performance_baseline_weekly_latest.json")
    alert_quality = _read_json(art / "core_alert_quality_report_latest.json")
    rto = _read_json(art / "recovery_rto_drill_report_latest.json")
    trimetrics = _read_json(art / "compression_restore_trimetrics_gate_report_latest.json")

    core_success = ((baseline.get("kpi") or {}).get("core_task_success_rate_percent_7d"))
    noise_ratio = (((alert_quality.get("quality") or {}).get("global_noise_ratio_percent")))
    rto_target_met = (((rto.get("recovery_summary") or {}).get("rto_target_met")))
    compression_status = trimetrics.get("status")

    gates = {
        "core_success_rate_ge_93": bool(core_success is not None and float(core_success) >= 93.0),
        "alert_noise_ratio_le_70": bool(noise_ratio is not None and float(noise_ratio) <= 70.0),
        "rto_target_met": bool(rto_target_met is True),
        "compression_trimetrics_not_fail": bool(compression_status in {"PASS", "HOLD"}),
    }
    pass_count = sum(1 for v in gates.values() if v)
    decision = "PROMOTE_WITH_GUARDRAILS" if pass_count >= 3 else "HOLD"

    out = {
        "schema": "cursor_tuning_promotion_decision_v1",
        "generated_at_utc": _iso_now(),
        "decision": decision,
        "gates": gates,
        "gate_pass_count": pass_count,
        "inputs": {
            "core_success_rate_percent_7d": core_success,
            "alert_noise_ratio_percent_7d": noise_ratio,
            "rto_target_met": rto_target_met,
            "compression_trimetrics_status": compression_status,
        },
        "policy": {
            "mode": "guarded_promotion",
            "note": "Promotion allows continued operation with alert-cooldown and daily recheck; no destructive switch.",
        },
        "evidence": {
            "baseline": "docs/final/artifacts/cursor_performance_baseline_weekly_latest.json",
            "alert_quality": "docs/final/artifacts/core_alert_quality_report_latest.json",
            "rto_report": "docs/final/artifacts/recovery_rto_drill_report_latest.json",
            "trimetrics_report": "docs/final/artifacts/compression_restore_trimetrics_gate_report_latest.json",
        },
    }

    out_json = art / "cursor_tuning_promotion_decision_latest.json"
    out_md = art / "cursor_tuning_promotion_decision_latest.md"
    out_json.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    out_md.write_text(
        "\n".join(
            [
                "# Cursor Tuning Promotion Decision",
                "",
                f"- generated_at_utc: `{out['generated_at_utc']}`",
                f"- decision: `{decision}`",
                f"- gate_pass_count: `{pass_count}`",
                f"- core_success_rate_ge_93: `{gates['core_success_rate_ge_93']}`",
                f"- alert_noise_ratio_le_70: `{gates['alert_noise_ratio_le_70']}`",
                f"- rto_target_met: `{gates['rto_target_met']}`",
                f"- compression_trimetrics_not_fail: `{gates['compression_trimetrics_not_fail']}`",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"wrote: {out_json}")
    print(f"wrote: {out_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(build())

