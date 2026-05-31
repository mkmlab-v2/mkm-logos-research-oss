#!/usr/bin/env python3
"""Build stratified human-review sample from interpret LoRA eval + predictions (B-track)."""

from __future__ import annotations

import argparse
import json
import random
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.audit_myeongri_interpret_narrative_diversity_v1 import (  # noqa: E402
    V3_PREFIX,
    _extract_insight,
    insight_to_template_skeleton,
)

REVIEWER_PROMPTS_KO = [
    "사주 4주·일간이 엔진 입력과 모순 없는가?",
    "가격·매매·의료 단정 표현이 없는가?",
    "[HYPO]·면책 문구가 적절한가?",
    "서술이 template 반복만인지, 추가 해석 가치가 있는지?",
]


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rel(p: Path) -> str:
    try:
        return str(p.resolve().relative_to(ROOT.resolve())).replace("\\", "/")
    except ValueError:
        return str(p).replace("\\", "/")


def _auto_note(insight: str | None, v3_prefix: str) -> str:
    if not insight or not insight.strip():
        return "empty_insight_after_parse"
    text = insight.strip()
    if text.startswith(v3_prefix):
        return "template_pattern_likely"
    skel = insight_to_template_skeleton(text)
    if skel.count("{") >= 3:
        return "check_narrative_diversity"
    return "narrative_variant_ok"


def _parse_envelope_fields(raw: str) -> dict:
    from scripts.run_myeongri_harness_v2_engine_interpret_smoke_v1 import _try_parse_envelope

    parsed, _note, _coerced = _try_parse_envelope(raw, gold_out=None)
    if not isinstance(parsed, dict):
        return {"confidence_score": None, "human_review_required": True}
    return {
        "confidence_score": parsed.get("confidence_score"),
        "human_review_required": parsed.get("human_review_required", True),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--eval-json", type=Path, required=True)
    ap.add_argument("--predictions-jsonl", type=Path, required=True)
    ap.add_argument("--out-json", type=Path, required=True)
    ap.add_argument("--adapter-path", type=str, required=True)
    ap.add_argument("--schema", default="myeongri_interpret_human_review_sample_v1")
    ap.add_argument("--sample-n", type=int, default=10)
    ap.add_argument("--seed", type=int, default=20260531)
    ap.add_argument(
        "--ensure-empty-insight",
        type=int,
        default=2,
        help="Include up to N rows where insight extraction failed (default 2).",
    )
    ap.add_argument("--v3-template-prefix", default=V3_PREFIX)
    args = ap.parse_args()

    eval_doc = json.loads(args.eval_json.read_text(encoding="utf-8"))
    per_row = {int(r["row_index"]): r for r in eval_doc.get("per_row") or []}
    preds = [
        json.loads(line)
        for line in args.predictions_jsonl.read_text(encoding="utf-8-sig").splitlines()
        if line.strip()
    ]
    pred_by_row = {int(p["row_index"]): p for p in preds}

    empty_rows: list[int] = []
    ok_rows: list[int] = []
    for idx, p in pred_by_row.items():
        ins = _extract_insight(p.get("prediction_raw", ""))
        if ins and ins.strip():
            ok_rows.append(idx)
        else:
            empty_rows.append(idx)

    rng = random.Random(args.seed)
    chosen: list[int] = []
    for idx in sorted(empty_rows)[: max(0, args.ensure_empty_insight)]:
        chosen.append(idx)
    pool = [i for i in ok_rows if i not in chosen]
    need = max(0, args.sample_n - len(chosen))
    if need > len(pool):
        need = len(pool)
    chosen.extend(rng.sample(pool, need))
    chosen = sorted(chosen)[: args.sample_n]

    samples: list[dict] = []
    for idx in chosen:
        p = pred_by_row[idx]
        raw = p.get("prediction_raw", "")
        er = per_row.get(idx, {})
        insight = _extract_insight(raw)
        fields = _parse_envelope_fields(raw)
        samples.append(
            {
                "row_index": idx,
                "parse_ok": bool(er.get("parse_ok", True)),
                "envelope_match_normalized": bool(er.get("envelope_match_normalized")),
                "envelope_coerced_from_template": bool(er.get("envelope_coerced_from_template")),
                "mkm_advanced_insight": insight,
                "confidence_score": fields.get("confidence_score"),
                "human_review_required": fields.get("human_review_required", True),
                "reviewer_prompts_ko": list(REVIEWER_PROMPTS_KO),
                "reviewer_verdict": None,
                "auto_note": _auto_note(insight, args.v3_template_prefix),
                "prediction_raw_head": raw[:280] if isinstance(raw, str) else None,
            }
        )

    out_doc = {
        "schema": args.schema,
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "boundary_ack": True,
        "seed": args.seed,
        "sample_n": len(samples),
        "population_eval": _rel(args.eval_json),
        "predictions_jsonl": _rel(args.predictions_jsonl),
        "adapter": args.adapter_path,
        "instructions_ko": "reviewer_verdict: pass|fail|needs_edit. Track A·실매매 승격 판정 아님.",
        "empty_insight_row_indices_in_population": sorted(empty_rows),
        "samples": samples,
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(out_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "sample_n": len(samples),
                "empty_in_sample": sum(1 for s in samples if s["auto_note"] == "empty_insight_after_parse"),
                "out": str(args.out_json),
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
