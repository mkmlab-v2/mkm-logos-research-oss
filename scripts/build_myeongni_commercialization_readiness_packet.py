#!/usr/bin/env python3
"""Build commercialization-ready evidence artifacts for myeongni lane."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
from myeongni_16_state_experiment_ledger import validate_experiment_record

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
DEFAULT_EXPERIMENT = ROOT / "data" / "myeongni" / "myeongni_16_state_experiment_v1.calendar_stub_through_202604.jsonl"


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return obj if isinstance(obj, dict) else {}


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    out: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            out.append(obj)
    return out


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _to_target(mt: Any) -> str:
    v = str(mt or "").strip().lower()
    return v if v in {"bull", "bear", "sideways"} else "unknown"


def _shadow_override_stats(shadow_gate: dict[str, Any]) -> dict[str, Any]:
    history = shadow_gate.get("history") if isinstance(shadow_gate.get("history"), dict) else {}
    history_path = Path(str(history.get("history_path") or ""))
    if not history_path.is_file():
        return {
            "history_rows": 0,
            "override_rows": 0,
            "override_ratio": 0.0,
            "latest_override_ts_utc": None,
        }
    rows = _read_jsonl(history_path)
    override_rows = [r for r in rows if isinstance(r, dict) and r.get("override_label")]
    latest_override_ts = None
    if override_rows:
        latest_override_ts = sorted(str(r.get("ts_utc") or "") for r in override_rows if r.get("ts_utc"))[-1]
    total = len(rows)
    ratio = (len(override_rows) / total) if total else 0.0
    return {
        "history_rows": total,
        "override_rows": len(override_rows),
        "override_ratio": round(ratio, 6),
        "latest_override_ts_utc": latest_override_ts,
    }


def build_eval_contract(rows: list[dict[str, Any]], lens: dict[str, Any], fusion: dict[str, Any]) -> dict[str, Any]:
    ts_values = sorted(str(r.get("ts_utc") or "") for r in rows if r.get("ts_utc"))
    period_start = ts_values[0] if ts_values else ""
    period_end = ts_values[-1] if ts_values else ""
    return {
        "schema": "myeongni_eval_contract_v1",
        "ts_utc": _utc_now(),
        "mode": "observation_only",
        "scope": "Track B lane only; no Track A/live binding.",
        "window": {"period_start_utc": period_start, "period_end_utc": period_end, "sample_size": len(rows)},
        "neutral_rule": {"neutral_band_abs_direction_score": 0.05, "neutral_label": "neutral"},
        "metrics": [
            "direction_score_mean",
            "direction_score_abs_mean",
            "neutral_ratio",
            "confidence_mean",
            "agreement_rate",
            "conflict_count",
        ],
        "aligned_inputs": {
            "myeongni_independent_lens": str((ART / "myeongni_independent_lens_latest.json").resolve()),
            "independent_lens_fusion_stub": str((ART / "independent_lens_fusion_stub_latest.json").resolve()),
            "independent_lens_shadow_gate": str((ART / "independent_lens_shadow_gate_latest.json").resolve()),
            "myeongni_16state_jsonl": str(DEFAULT_EXPERIMENT.resolve()),
        },
        "latest_snapshot": {
            "lens_ts_utc": lens.get("ts_utc"),
            "fusion_ts_utc": fusion.get("ts_utc"),
            "fusion_agreement_rate": (fusion.get("consensus") or {}).get("agreement_rate"),
        },
        "policy_guardrail": {
            "auto_promotion_track_b_to_a": False,
            "auto_live_trigger": False,
            "decision_authority": "human_review_required",
        },
    }


def build_quality_report(rows: list[dict[str, Any]]) -> dict[str, Any]:
    required = ("ts_utc", "hypothesis_tier", "boundary_ack", "stub")
    violations: list[dict[str, Any]] = []
    missing_required = 0
    out_of_range = 0
    bad_time_order = 0
    last_ts = ""
    target_counts: dict[str, int] = {"bull": 0, "bear": 0, "sideways": 0, "unknown": 0}
    consistency_vals: list[float] = []
    contradiction_vals: list[float] = []

    for i, row in enumerate(rows, start=1):
        errs = validate_experiment_record(row)
        if errs:
            violations.append({"line": i, "errors": errs})
        for key in required:
            if key not in row:
                missing_required += 1
        if isinstance(row.get("consistency_rate"), (int, float)):
            consistency_vals.append(float(row["consistency_rate"]))
        if isinstance(row.get("self_contradiction_rate"), (int, float)):
            contradiction_vals.append(float(row["self_contradiction_rate"]))
        target_counts[_to_target(row.get("mapping_target"))] += 1
        cur_ts = str(row.get("ts_utc") or "")
        if cur_ts and last_ts and cur_ts < last_ts:
            bad_time_order += 1
        if cur_ts:
            last_ts = cur_ts
        sid = row.get("state_id")
        if sid is not None and (not isinstance(sid, int) or sid < 1 or sid > 16):
            out_of_range += 1

    total = len(rows)
    v_count = len(violations)
    neutral_ratio = (target_counts["sideways"] / total) if total else 0.0
    consistency_mean = (sum(consistency_vals) / len(consistency_vals)) if consistency_vals else 0.0
    contradiction_mean = (sum(contradiction_vals) / len(contradiction_vals)) if contradiction_vals else 0.0

    return {
        "schema": "myeongni_16state_data_quality_report_v1",
        "ts_utc": _utc_now(),
        "input_jsonl": str(DEFAULT_EXPERIMENT.resolve()),
        "rows_total": total,
        "contract_violations": v_count,
        "required_field_missing_count": missing_required,
        "range_violations_count": out_of_range,
        "time_order_violations_count": bad_time_order,
        "mapping_target_distribution": target_counts,
        "neutral_ratio": round(neutral_ratio, 6),
        "consistency_rate_mean": round(consistency_mean, 6),
        "self_contradiction_rate_mean": round(contradiction_mean, 6),
        "status": "PASS" if (v_count == 0 and out_of_range == 0 and bad_time_order == 0) else "WARN",
        "violations_preview": violations[:20],
    }


def build_readiness_packet(
    lens: dict[str, Any],
    fusion: dict[str, Any],
    shadow_gate: dict[str, Any],
    eval_contract: dict[str, Any],
    quality_report: dict[str, Any],
) -> dict[str, Any]:
    lens_scores = lens.get("scores") if isinstance(lens.get("scores"), dict) else {}
    consensus = fusion.get("consensus") if isinstance(fusion.get("consensus"), dict) else {}
    blockers = shadow_gate.get("blockers") if isinstance(shadow_gate.get("blockers"), list) else []
    quality_ok = quality_report.get("status") == "PASS"
    contract_ok = bool(eval_contract.get("aligned_inputs"))
    signal_non_neutral = abs(float(lens_scores.get("direction_score", 0.0))) > 0.0
    override_stats = _shadow_override_stats(shadow_gate)

    if contract_ok and quality_ok and signal_non_neutral and not blockers:
        readiness = "Ready"
    elif contract_ok and quality_ok:
        readiness = "Almost"
    else:
        readiness = "Not yet"

    return {
        "schema": "myeongni_commercialization_readiness_packet_v1",
        "ts_utc": _utc_now(),
        "readiness": readiness,
        "summary": {
            "contract_alignment_ok": contract_ok,
            "data_quality_ok": quality_ok,
            "signal_non_neutral": signal_non_neutral,
            "fusion_agreement_rate": consensus.get("agreement_rate"),
            "shadow_blockers_count": len(blockers),
            "shadow_override_ratio": override_stats.get("override_ratio"),
        },
        "inputs": {
            "myeongni_independent_lens": str((ART / "myeongni_independent_lens_latest.json").resolve()),
            "independent_lens_fusion_stub": str((ART / "independent_lens_fusion_stub_latest.json").resolve()),
            "independent_lens_shadow_gate": str((ART / "independent_lens_shadow_gate_latest.json").resolve()),
            "myeongni_eval_contract": str((ART / "myeongni_eval_contract_latest.json").resolve()),
            "myeongni_16state_data_quality_report": str((ART / "myeongni_16state_data_quality_report_latest.json").resolve()),
        },
        "guardrail": {
            "track_b_to_a_auto_bridge": False,
            "live_trigger_auto_enabled": False,
            "decision": "manual_review_required",
        },
        "shadow_history_integrity": override_stats,
        "next_gate_focus": [
            "reduce_neutral_bias_without_overfit",
            "increase_shadow_monthly_coverage",
            "maintain contract-0 conflict under same input window",
        ],
    }


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description="Build myeongni commercialization readiness artifacts.")
    ap.add_argument("--experiment-jsonl", type=Path, default=DEFAULT_EXPERIMENT)
    args = ap.parse_args()

    rows = _read_jsonl(args.experiment_jsonl)
    lens = _read_json(ART / "myeongni_independent_lens_latest.json")
    fusion = _read_json(ART / "independent_lens_fusion_stub_latest.json")
    shadow_gate = _read_json(ART / "independent_lens_shadow_gate_latest.json")

    eval_contract = build_eval_contract(rows, lens, fusion)
    quality_report = build_quality_report(rows)
    readiness_packet = build_readiness_packet(lens, fusion, shadow_gate, eval_contract, quality_report)

    _write_json(ART / "myeongni_eval_contract_latest.json", eval_contract)
    _write_json(ART / "myeongni_16state_data_quality_report_latest.json", quality_report)
    _write_json(ART / "myeongni_commercialization_readiness_packet_latest.json", readiness_packet)

    print("WROTE: docs/final/artifacts/myeongni_eval_contract_latest.json")
    print("WROTE: docs/final/artifacts/myeongni_16state_data_quality_report_latest.json")
    print("WROTE: docs/final/artifacts/myeongni_commercialization_readiness_packet_latest.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
