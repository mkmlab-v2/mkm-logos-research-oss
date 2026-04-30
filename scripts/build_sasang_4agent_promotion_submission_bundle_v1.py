#!/usr/bin/env python3
"""Build single submission bundle for sasang 4-agent promotion chain."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _safe_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return obj if isinstance(obj, dict) else {}


def _sha256(path: Path) -> str | None:
    if not path.exists() or not path.is_file():
        return None
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    art = root / "docs" / "final" / "artifacts"

    refs = {
        "protocol": art / "sasang_4agent_collision_btrack_protocol_latest.json",
        "patent_brief": art / "sasang_4agent_patent_brief_latest.json",
        "invention_disclosure": art / "sasang_4agent_invention_disclosure_latest.json",
        "promotion_gate": art / "sasang_4agent_promotion_gate_latest.json",
        "human_approval": art / "sasang_4agent_human_approval_latest.json",
        "tracka_bridge": art / "sasang_4agent_tracka_bridge_latest.json",
        "monitor_snapshot": art / "sasang_4agent_monitor_snapshot_latest.json",
        "daily_monitor_run": art / "sasang_4agent_daily_monitor_run_latest.json",
        "force_hold_recovery_drill": art / "sasang_4agent_force_hold_recovery_drill_latest.json",
        "repro_protocol_kospi": art / "sasang_4agent_collision_btrack_protocol_repro_kospi_latest.json",
    }

    docs: dict[str, dict[str, Any]] = {k: _safe_json(v) for k, v in refs.items()}

    gate = docs["promotion_gate"]
    bridge = docs["tracka_bridge"]
    monitor = docs["monitor_snapshot"]
    drill = docs["force_hold_recovery_drill"]
    repro = docs["repro_protocol_kospi"]

    final_line = "PROMOTED_WITH_HUMAN_APPROVAL + MONITORING_ACTIVE + DRILL_PASS"
    checks = {
        "gate_promoted_with_human_approval": str(gate.get("decision")) == "A_TRACK_PROMOTED_WITH_HUMAN_APPROVAL",
        "bridge_active": str(bridge.get("status")) == "ACTIVE",
        "monitor_alert_false": not bool(monitor.get("alert")),
        "recovery_drill_pass": str(drill.get("status")) == "PASS",
    }
    repro_exp = repro.get("experiment") if isinstance(repro.get("experiment"), dict) else {}
    repro_res = repro.get("results") if isinstance(repro.get("results"), dict) else {}
    repro_ticks = int(repro_exp.get("ticks") or 0)
    repro_significance = bool(repro_res.get("statistical_significance_pass_p_lt_0_05"))
    repro_mdd_reduction_positive = float(repro_res.get("mdd_reduction_abs") or 0.0) > 0.0
    repro_sample_ok = not bool(repro_res.get("sample_size_warning_low_ticks"))
    checks["repro_significance_pass"] = repro_significance
    checks["repro_mdd_reduction_positive"] = repro_mdd_reduction_positive
    checks["repro_sample_size_ok"] = repro_sample_ok
    checks["repro_check_pass"] = bool(repro_significance and repro_mdd_reduction_positive and repro_sample_ok)
    if not all(checks.values()):
        final_line = "HOLD_OR_INCOMPLETE_CHAIN"

    out_json = art / "sasang_4agent_promotion_submission_bundle_latest.json"
    out_md = art / "sasang_4agent_promotion_submission_bundle_latest.md"

    payload = {
        "schema": "sasang_4agent_promotion_submission_bundle_v1",
        "generated_at_utc": _now_utc(),
        "summary_status": final_line,
        "checks": checks,
        "artifact_refs": {k: str(v).replace("\\", "/") for k, v in refs.items()},
        "artifact_sha256": {k: _sha256(v) for k, v in refs.items()},
        "key_metrics": {
            "ticks": docs["protocol"].get("experiment", {}).get("ticks"),
            "mdd_reduction_abs": docs["protocol"].get("results", {}).get("mdd_reduction_abs"),
            "p_permutation": docs["protocol"].get("results", {}).get("mdd_reduction_p_value_permutation"),
            "promotion_decision": gate.get("decision"),
            "bridge_status": bridge.get("status"),
            "monitor_alert": monitor.get("alert"),
            "drill_status": drill.get("status"),
            "repro_ticks": repro_ticks,
            "repro_p_permutation": repro_res.get("mdd_reduction_p_value_permutation"),
            "repro_check_pass": checks["repro_check_pass"],
        },
    }
    out_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# Sasang 4-Agent Promotion Submission Bundle",
        "",
        f"- generated_at_utc: `{payload['generated_at_utc']}`",
        f"- summary_status: `{payload['summary_status']}`",
        "",
        "## Checks",
    ]
    for k, v in checks.items():
        lines.append(f"- {k}: `{v}`")
    lines.extend(["", "## Key Metrics"])
    for k, v in payload["key_metrics"].items():
        lines.append(f"- {k}: `{v}`")
    lines.extend(["", "## Artifact Hashes"])
    for k, v in payload["artifact_sha256"].items():
        lines.append(f"- {k}: `{v}`")
    lines.append("")
    out_md.write_text("\n".join(lines), encoding="utf-8")

    print(str(out_json))
    print(str(out_md))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

