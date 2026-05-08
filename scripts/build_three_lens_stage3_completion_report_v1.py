#!/usr/bin/env python3
"""Build Stage-3 completion report for three-lens promotion readiness."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"

DEFAULT_HISTORY = ART / "three_lens_shadow_history_v1.jsonl"
DEFAULT_GATE = ART / "three_lens_feature_gate_v2_latest.json"
DEFAULT_PROMOTION = ART / "three_lens_shadow_promotion_v1_latest.json"
DEFAULT_OUT = ART / "three_lens_stage3_completion_report_v1_latest.json"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json_optional(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return {}


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    for raw in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(row, dict):
            rows.append(row)
    return rows


def _as_bool(v: Any) -> bool:
    return bool(v is True)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--history-jsonl", type=Path, default=DEFAULT_HISTORY)
    ap.add_argument("--gate-json", type=Path, default=DEFAULT_GATE)
    ap.add_argument("--promotion-json", type=Path, default=DEFAULT_PROMOTION)
    ap.add_argument("--required-runs", type=int, default=7)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    history_path = args.history_jsonl if args.history_jsonl.is_absolute() else ROOT / args.history_jsonl
    gate_path = args.gate_json if args.gate_json.is_absolute() else ROOT / args.gate_json
    promotion_path = args.promotion_json if args.promotion_json.is_absolute() else ROOT / args.promotion_json
    out_path = args.output_json if args.output_json.is_absolute() else ROOT / args.output_json

    history = _load_jsonl(history_path)
    gate = _read_json_optional(gate_path)
    promotion = _read_json_optional(promotion_path)
    required_runs = max(1, int(args.required_runs))
    tail = history[-required_runs:]

    action_counts = Counter(str(r.get("action") or "UNKNOWN").upper() for r in tail)
    total_tail = len(tail)
    watch_ratio = (action_counts.get("WATCH", 0) / total_tail) if total_tail else 0.0
    hold_ratio = (action_counts.get("HOLD", 0) / total_tail) if total_tail else 0.0
    go_ratio = (action_counts.get("GO", 0) / total_tail) if total_tail else 0.0
    logos_field_known_count = sum(1 for r in tail if "logos_non_gating_ok" in r)
    logos_violation_count = sum(1 for r in tail if "logos_non_gating_ok" in r and _as_bool(r.get("logos_non_gating_ok")) is False)
    cond_armed_enabled_count = sum(1 for r in tail if "conditional_go_enabled" in r and _as_bool(r.get("conditional_go_enabled")))
    cond_armed_true_count = sum(
        1
        for r in tail
        if "conditional_go_enabled" in r
        and _as_bool(r.get("conditional_go_enabled"))
        and _as_bool(r.get("conditional_go_armed"))
    )
    cond_armed_rate = (cond_armed_true_count / cond_armed_enabled_count) if cond_armed_enabled_count else 0.0

    go_to_hold_transitions = 0
    for prev, cur in zip(tail, tail[1:]):
        if str(prev.get("action") or "").upper() == "GO" and str(cur.get("action") or "").upper() == "HOLD":
            go_to_hold_transitions += 1

    tail_has_evidence = all(_as_bool(r.get("enabled_evidence_all_present")) for r in tail) if tail else False
    tail_stable_actions = all(str(r.get("action") or "").upper() in {"WATCH", "GO"} for r in tail) if tail else False
    runs_ok = total_tail >= required_runs
    promotion_ready = (
        promotion.get("decision") == "PROMOTED"
        or (
            runs_ok
            and tail_has_evidence
            and tail_stable_actions
            and logos_violation_count == 0
        )
    )

    logos_violation_gate_pass = (logos_field_known_count == 0) or (logos_violation_count == 0)
    conditional_go_gate_pass = (cond_armed_enabled_count == 0) or (cond_armed_rate >= 0.20)
    stage3_complete = bool(promotion_ready and hold_ratio <= 0.30 and conditional_go_gate_pass and logos_violation_gate_pass)
    stage3_status = "PASS" if stage3_complete else "FAIL"

    payload = {
        "schema": "three_lens_stage3_completion_report_v1",
        "generated_at_utc": _now(),
        "inputs": {
            "history_jsonl": str(history_path),
            "gate_json": str(gate_path),
            "promotion_json": str(promotion_path),
            "required_runs": required_runs,
        },
        "tail_window": {
            "sample_count": total_tail,
            "action_counts": dict(action_counts),
            "watch_ratio": round(watch_ratio, 6),
            "hold_ratio": round(hold_ratio, 6),
            "go_ratio": round(go_ratio, 6),
            "go_to_hold_transitions": go_to_hold_transitions,
            "logos_non_gating_violation_count": logos_violation_count,
            "logos_non_gating_field_known_count": logos_field_known_count,
            "conditional_go_armed_rate": round(cond_armed_rate, 6),
            "conditional_go_armed_count": cond_armed_true_count,
            "conditional_go_enabled_count": cond_armed_enabled_count,
            "enabled_evidence_all_present": tail_has_evidence,
            "tail_stable_actions": tail_stable_actions,
        },
        "latest_gate": {
            "action": (gate.get("decision") or {}).get("action"),
            "reason": (gate.get("decision") or {}).get("reason"),
            "conditional_go_armed": (gate.get("metrics") or {}).get("conditional_go_armed"),
            "logos_non_gating_ok": (gate.get("metrics") or {}).get("logos_non_gating_ok"),
        },
        "promotion": {
            "decision": promotion.get("decision"),
            "required_runs": promotion.get("required_runs"),
            "eligible_features": promotion.get("eligible_features"),
        },
        "stage3_gate": {
            "status": stage3_status,
            "checks": {
                "runs_ok": runs_ok,
                "promotion_ready": promotion_ready,
                "hold_ratio_lte_0_30": hold_ratio <= 0.30,
                "conditional_go_armed_rate_gte_0_20_or_no_enabled_samples": conditional_go_gate_pass,
                "logos_non_gating_violation_count_eq_0_or_no_known_samples": logos_violation_gate_pass,
            },
        },
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(out_path), "status": stage3_status}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
