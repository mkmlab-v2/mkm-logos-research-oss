#!/usr/bin/env python3
"""Build Pack0B alignment recovery packet (B-track, non-destructive).

Inputs:
- locked eval report (Qwen compact eval)
- triage summary
- harness v2 smoke report
- predictions jsonl

Output:
- reports/myeongri_alignment_recovery_packet_v1_latest.json
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

DEFAULT_EVAL = ROOT / "reports/myeongri_deterministic_lora_locked_eval_inference_eval_qwen_compact_v1.json"
DEFAULT_TRIAGE = ROOT / "reports/myeongri_pack0b_adapter_locked_triage_latest.json"
DEFAULT_HARNESS = ROOT / "reports/myeongri_harness_v2_engine_interpret_smoke_v1_latest.json"
DEFAULT_PRED = ROOT / "reports/myeongri_deterministic_lora_locked_eval_predictions_qwen_compact_v1.jsonl"
DEFAULT_OUT = ROOT / "reports/myeongri_alignment_recovery_packet_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _load_jsonl(path: Path, limit: int = 0) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.is_file():
        return rows
    with path.open("r", encoding="utf-8-sig") as f:
        for raw in f:
            line = raw.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(row, dict):
                rows.append(row)
            if limit > 0 and len(rows) >= limit:
                break
    return rows


def _safe_float(v: Any, default: float = 0.0) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--eval-json", type=Path, default=DEFAULT_EVAL)
    ap.add_argument("--triage-json", type=Path, default=DEFAULT_TRIAGE)
    ap.add_argument("--harness-json", type=Path, default=DEFAULT_HARNESS)
    ap.add_argument("--predictions-jsonl", type=Path, default=DEFAULT_PRED)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--parse-floor", type=float, default=0.95)
    ap.add_argument("--alignment-floor", type=float, default=0.2)
    ap.add_argument("--sample-failed-limit", type=int, default=20)
    args = ap.parse_args()

    eval_doc = _load_json(args.eval_json) if args.eval_json.is_file() else {}
    triage_doc = _load_json(args.triage_json) if args.triage_json.is_file() else {}
    harness_doc = _load_json(args.harness_json) if args.harness_json.is_file() else {}
    pred_rows = _load_jsonl(args.predictions_jsonl)

    parse_ok_rate = _safe_float(eval_doc.get("parse_ok_rate"), 0.0)
    alignment_pass_rate = _safe_float(eval_doc.get("alignment_pass_rate"), 0.0)
    rows = int(eval_doc.get("rows", 0) or 0)
    harness_engine_rate = _safe_float(harness_doc.get("engine_pillars_pass_rate"), 0.0)

    mismatch_hist = triage_doc.get("mismatch_notes_qwen_compact_locked25")
    if not isinstance(mismatch_hist, dict):
        mismatch_hist = {}

    failed_parse_ids: list[str] = []
    parsed_but_mismatch_ids: list[str] = []
    for r in pred_rows:
        sid = str(r.get("id") or "")
        parse_ok = bool(r.get("parse_ok"))
        exact = bool(r.get("exact_match"))
        if not sid:
            continue
        if not parse_ok:
            failed_parse_ids.append(sid)
        elif not exact:
            parsed_but_mismatch_ids.append(sid)

    route_mode = "pack0b_qwen_compact_only"
    if alignment_pass_rate < args.alignment_floor and harness_engine_rate >= 1.0:
        route_mode = "harness_v2_engine_plus_interpret"
    elif parse_ok_rate < args.parse_floor:
        route_mode = "pack0b_qwen_with_strict_json_repair"

    severity = "green"
    if alignment_pass_rate <= 0.0:
        severity = "red"
    elif alignment_pass_rate < args.alignment_floor:
        severity = "amber"

    out = {
        "schema": "myeongri_alignment_recovery_packet_v1",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "inputs": {
            "eval_report": str(args.eval_json).replace("\\", "/"),
            "triage_report": str(args.triage_json).replace("\\", "/"),
            "harness_report": str(args.harness_json).replace("\\", "/"),
            "predictions_jsonl": str(args.predictions_jsonl).replace("\\", "/"),
        },
        "metrics": {
            "rows": rows,
            "parse_ok_rate": parse_ok_rate,
            "alignment_pass_rate": alignment_pass_rate,
            "harness_engine_pillars_pass_rate": harness_engine_rate,
            "mismatch_histogram": mismatch_hist,
            "failed_parse_count": len(failed_parse_ids),
            "parsed_but_mismatch_count": len(parsed_but_mismatch_ids),
        },
        "router_decision": {
            "severity": severity,
            "route_mode": route_mode,
            "rationale": (
                "alignment below floor with engine-pillar pass=1.0 -> prefer harness v2"
                if route_mode == "harness_v2_engine_plus_interpret"
                else "parse below floor -> keep qwen lane with strict repair"
                if route_mode == "pack0b_qwen_with_strict_json_repair"
                else "qwen compact lane stays primary"
            ),
        },
        "recovery_actions": [
            "A1: Use harness_v2_engine_plus_interpret when route_mode selects it (non-gating, B-track).",
            "A2: Prioritize SFT v2 rows from failed_parse sample ids.",
            "A3: Re-run locked_eval expanded and compare parse_ok_rate/alignment_pass_rate deltas.",
            "A4: Keep Track A promotion and live-trading OFF until alignment floor is met.",
        ],
        "failed_parse_sample_ids": failed_parse_ids[: args.sample_failed_limit],
        "parsed_mismatch_sample_ids": parsed_but_mismatch_ids[: args.sample_failed_limit],
        "track_wall": {
            "a_track_auto_promotion": False,
            "ready_for_external_send": False,
            "live_trading": False,
        },
    }

    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(args.out_json), "route_mode": route_mode}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

