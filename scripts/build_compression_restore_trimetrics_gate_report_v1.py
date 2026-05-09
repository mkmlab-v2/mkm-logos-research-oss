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

    weekly = _read_json(art / "compression_weekly_governance_report_latest.json")
    size_gate = _read_json(art / "compression_bridge_size_daily_gate_summary_latest.json")
    size_alert = _read_json(art / "compression_bridge_size_daily_gate_alert_latest.json")

    active_kpi = ((weekly.get("kpi_summary_embed") or {}).get("active_kpi") or {})
    literal_kpi = ((weekly.get("kpi_summary_embed") or {}).get("literal_kpi") or {})

    track_a = {
        "token_saving_rate": active_kpi.get("global_token_saving_rate"),
        "reconstruction_fidelity_jaccard": active_kpi.get("avg_reconstruction_fidelity_jaccard"),
        "sensitive_integrity": active_kpi.get("avg_sensitive_integrity"),
        "jaccard_guardrail_ok": active_kpi.get("jaccard_guardrail_ok"),
        "sensitive_integrity_ok": active_kpi.get("sensitive_integrity_ok"),
    }
    track_b_literal = {
        "token_saving_rate": literal_kpi.get("global_token_saving_rate"),
        "reconstruction_fidelity_jaccard": literal_kpi.get("avg_reconstruction_fidelity_jaccard"),
        "sensitive_integrity": literal_kpi.get("avg_sensitive_integrity"),
        "jaccard_guardrail_ok": literal_kpi.get("jaccard_guardrail_ok"),
        "sensitive_integrity_ok": literal_kpi.get("sensitive_integrity_ok"),
    }

    size_status = str(size_gate.get("status") or "UNKNOWN")
    weekly_decision = (((weekly.get("decision_snapshot") or {}).get("go_no_go")) or "UNKNOWN")
    day5_status = "PASS" if weekly_decision == "GO" and size_status in {"PASS", "GO"} else "HOLD"

    out = {
        "schema": "compression_restore_trimetrics_gate_report_v1",
        "generated_at_utc": _iso_now(),
        "status": day5_status,
        "decision_basis": {
            "weekly_go_no_go": weekly_decision,
            "size_lane_status": size_status,
            "size_lane_decision": size_gate.get("decision"),
            "size_alert_severity": size_alert.get("severity"),
        },
        "trimetrics": {
            "track_a_active": track_a,
            "track_b_literal": track_b_literal,
        },
        "recommendations": [
            "Keep Track A active KPI GO path while size-lane remains HOLD.",
            "Promote only when size-lane daily gate status flips to PASS/GO.",
            "Continue monitoring fidelity + sensitive_integrity as non-regression guardrails.",
        ],
        "evidence": {
            "compression_weekly_governance": "docs/final/artifacts/compression_weekly_governance_report_latest.json",
            "compression_size_daily_gate_summary": "docs/final/artifacts/compression_bridge_size_daily_gate_summary_latest.json",
            "compression_size_daily_gate_alert": "docs/final/artifacts/compression_bridge_size_daily_gate_alert_latest.json",
        },
    }

    out_json = art / "compression_restore_trimetrics_gate_report_latest.json"
    out_md = art / "compression_restore_trimetrics_gate_report_latest.md"
    out_json.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    out_md.write_text(
        "\n".join(
            [
                "# Compression/Restore Tri-Metrics Gate Report",
                "",
                f"- generated_at_utc: `{out['generated_at_utc']}`",
                f"- status: `{out['status']}`",
                f"- weekly_go_no_go: `{weekly_decision}`",
                f"- size_lane_status: `{size_status}`",
                f"- track_a_token_saving_rate: `{track_a.get('token_saving_rate')}`",
                f"- track_a_reconstruction_fidelity_jaccard: `{track_a.get('reconstruction_fidelity_jaccard')}`",
                f"- track_a_sensitive_integrity: `{track_a.get('sensitive_integrity')}`",
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

