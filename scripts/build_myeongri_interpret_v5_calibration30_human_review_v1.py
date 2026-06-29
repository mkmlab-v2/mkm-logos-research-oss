#!/usr/bin/env python3
"""Build v5 calibration30 human-review sample (same row indices as v4 Phase2)."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_V4_CAL30 = ROOT / "reports/myeongri_interpret_v4_human_review_calibration30_latest.json"
DEFAULT_V5_EVAL = ROOT / "reports/myeongri_interpret_lora_v5_eval_locked100_guard448_latest.json"
DEFAULT_V5_PREDS = ROOT / "reports/myeongri_interpret_lora_v5_preds_locked100_guard448_latest.jsonl"
DEFAULT_V5_SFT = ROOT / "data/training/myeongri_interpret_sft_v5/locked_eval.jsonl"
DEFAULT_V5_DIV = ROOT / "reports/myeongri_interpret_v5_diversity_audit_locked100_guard448_latest.json"
DEFAULT_OUT = ROOT / "reports/myeongri_interpret_v5_human_review_calibration30_latest.json"
DEFAULT_V4_CAL30_REF = DEFAULT_V4_CAL30


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve())).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def _load_jsonl(path: Path) -> list[dict]:
    return [json.loads(l) for l in path.read_text(encoding="utf-8-sig").splitlines() if l.strip()]


def _parse_insight(
    raw: str,
    *,
    gold: dict[str, Any],
    instruction: str,
) -> tuple[dict[str, Any] | None, bool, str]:
    from scripts.myeongri_interpret_envelope_views_v1 import extract_compact_from_interpret_instruction
    from scripts.run_myeongri_harness_v2_engine_interpret_smoke_v1 import _try_parse_envelope

    compact = extract_compact_from_interpret_instruction(instruction)
    parsed, note, coerced = _try_parse_envelope(
        raw,
        gold_out=gold,
        postprocess_v1=True,
        compact=compact,
        lang="ko",
        deterministic_input_sha256=str(gold.get("deterministic_input_sha256") or ""),
    )
    insight = str((parsed or {}).get("mkm_advanced_insight") or "")
    if not insight and raw:
        try:
            obj = json.loads(raw)
            insight = str(obj.get("mkm_advanced_insight") or "")
        except json.JSONDecodeError:
            pass
    return parsed, coerced, insight


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--v4-calibration30-json", type=Path, default=DEFAULT_V4_CAL30)
    ap.add_argument("--eval-json", type=Path, default=DEFAULT_V5_EVAL)
    ap.add_argument("--preds-jsonl", type=Path, default=DEFAULT_V5_PREDS)
    ap.add_argument("--sft-jsonl", type=Path, default=DEFAULT_V5_SFT)
    ap.add_argument("--diversity-json", type=Path, default=DEFAULT_V5_DIV)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    for p in (args.v4_calibration30_json, args.eval_json, args.preds_jsonl, args.sft_jsonl):
        if not p.is_file():
            print(json.dumps({"ok": False, "error": f"missing {p}"}))
            return 2

    v4_cal = json.loads(args.v4_calibration30_json.read_text(encoding="utf-8"))
    row_indices = [int(s["row_index"]) for s in v4_cal.get("samples") or []]
    if not row_indices:
        print(json.dumps({"ok": False, "error": "no row indices in v4 calibration30"}))
        return 1

    eval_doc = json.loads(args.eval_json.read_text(encoding="utf-8"))
    per_eval = {int(r["row_index"]): r for r in eval_doc.get("per_row") or []}
    preds_list = _load_jsonl(args.preds_jsonl)
    preds_by_row = {i + 1: preds_list[i] for i in range(len(preds_list))}
    sft_rows = _load_jsonl(args.sft_jsonl)

    v4_by_row = {int(s["row_index"]): s for s in v4_cal.get("samples") or []}

    samples: list[dict[str, Any]] = []
    for idx in row_indices:
        if idx < 1 or idx > len(sft_rows):
            continue
        sft_row = sft_rows[idx - 1]
        gold = json.loads(str(sft_row.get("output", "{}")))
        pred_rec = preds_by_row.get(idx, {})
        raw = str(pred_rec.get("prediction_raw", ""))
        parsed, coerced, insight = _parse_insight(
            raw,
            gold=gold,
            instruction=str(sft_row.get("instruction", "")),
        )
        ev = per_eval.get(idx, {})
        v4s = v4_by_row.get(idx, {})
        samples.append(
            {
                "row_index": idx,
                "parse_ok": ev.get("parse_ok"),
                "envelope_match_normalized": ev.get("envelope_match_normalized"),
                "envelope_coerced_from_template": ev.get("envelope_coerced_from_template"),
                "postprocess_coerced": coerced,
                "mkm_advanced_insight": insight,
                "confidence_score": (parsed or {}).get("confidence_score"),
                "human_review_required": (parsed or {}).get("human_review_required"),
                "reviewer_prompts_ko": [
                    "사주 4주·일간이 엔진 입력과 모순 없는가?",
                    "가격·매매·의료 단정 표현이 없는가?",
                    "[HYPO]·면책 문구가 적절한가?",
                    "v4 Phase2 대비 서술·과확신이 개선되었는가?",
                ],
                "reviewer_verdict": None,
                "auto_note": "empty_insight_after_parse" if not insight else "narrative_variant_ok",
                "gold_insight_head": str(gold.get("mkm_advanced_insight") or "")[:160],
                "v4_phase2_verdict": v4s.get("reviewer_verdict"),
                "v4_insight_head": str(v4s.get("mkm_advanced_insight") or "")[:200],
            }
        )

    doc = {
        "schema": "myeongri_interpret_v5_human_review_calibration30_v1",
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "boundary_ack": True,
        "seed": v4_cal.get("seed"),
        "sample_n": len(samples),
        "population_eval": _rel(args.eval_json),
        "adapter": eval_doc.get("adapter_path"),
        "prior_v4_calibration30": _rel(args.v4_calibration30_json),
        "instructions_ko": "reviewer_verdict: pass|fail|needs_edit. v5 LoRA B-track — Track A·운영 어댑터 승격 아님.",
        "diversity_audit_pointer": _rel(args.diversity_json) if args.diversity_json.is_file() else None,
        "calibration_policy_v1": {
            "phase": "v5_calibration30_pending",
            "prior_v4_phase": "calibration30_closed",
            "research_only": True,
            "track_a_live_trading_gate": False,
            "pending_reviewer_verdict_count": len(samples),
        },
        "samples": samples,
        "track_wall": {"track_a_live_auto_merge": False, "operational_adapter": "run_interpret_v4_variant_s100"},
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    status_path = ROOT / "reports/myeongri_interpret_harness_v3_v4_status_latest.json"
    if status_path.is_file():
        st = json.loads(status_path.read_text(encoding="utf-8"))
        block = st.setdefault("v4_variant_sft", {}).setdefault("v5_human_review_calibration30", {})
        block.update(
            {
                "status": "pending_review",
                "report": _rel(args.out_json),
                "sample_n": len(samples),
            }
        )
        st["generated_at_utc"] = _utc_now()
        status_path.write_text(json.dumps(st, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(json.dumps({"ok": True, "sample_n": len(samples), "out": _rel(args.out_json)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
