#!/usr/bin/env python3
"""Post-eval bundle: v4 human review sample, empty-insight triage, match/coerce mismatch report."""

from __future__ import annotations

import argparse
import json
import random
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_EVAL = ROOT / "reports/myeongri_interpret_lora_v4_eval_locked100_guard448_latest.json"
DEFAULT_PREDS = ROOT / "reports/myeongri_interpret_lora_v4_preds_locked100_guard448_latest.jsonl"
DEFAULT_SFT = ROOT / "data/training/myeongri_interpret_sft_v4/locked_eval.jsonl"
DEFAULT_DIVERSITY = ROOT / "reports/myeongri_interpret_v4_diversity_audit_locked100_guard448_latest.json"
DEFAULT_SAMPLE_OUT = ROOT / "reports/myeongri_interpret_v4_human_review_sample_latest.json"
DEFAULT_MISMATCH_OUT = ROOT / "reports/myeongri_interpret_v4_match_mismatch_summary_latest.json"
DEFAULT_EMPTY_OUT = ROOT / "reports/myeongri_interpret_v4_empty_insight_rows_latest.json"
DEFAULT_STATUS = ROOT / "reports/myeongri_interpret_harness_v3_v4_status_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_jsonl(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8-sig").splitlines()
        if line.strip()
    ]


def _commander_fields_from_prior(path: Path) -> tuple[dict[int, dict[str, Any]], dict[str, Any]]:
    """Return per-row commander review fields + top-level human gate metadata if signed."""
    if not path.is_file():
        return {}, {}
    try:
        prior = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}, {}
    if not prior.get("commander_signed_at_utc"):
        return {}, {}
    by_row: dict[int, dict[str, Any]] = {}
    for s in prior.get("samples") or []:
        ri = int(s.get("row_index", 0))
        if ri <= 0:
            continue
        keep = {
            k: s[k]
            for k in (
                "reviewer_verdict",
                "reviewer_verdict_source",
                "reviewer_verdict_reason",
                "reviewer_comment",
            )
            if k in s and s[k] is not None
        }
        if keep.get("reviewer_verdict_source") == "commander_v1":
            by_row[ri] = keep
    top = {
        k: prior[k]
        for k in (
            "human_verdict_counts",
            "human_verdict_applied_at_utc",
            "human_verdict_source",
            "commander_signed_at_utc",
            "population_caveats",
            "human_gate_pass",
        )
        if k in prior
    }
    return by_row, top


def _parse_envelope(
    raw: str,
    *,
    gold: dict[str, Any] | None = None,
    instruction: str = "",
) -> tuple[dict[str, Any] | None, bool]:
    from scripts.myeongri_interpret_envelope_views_v1 import extract_compact_from_interpret_instruction
    from scripts.run_myeongri_harness_v2_engine_interpret_smoke_v1 import _try_parse_envelope

    compact = extract_compact_from_interpret_instruction(instruction) if instruction else None
    sha = str((gold or {}).get("deterministic_input_sha256") or "").strip()
    parsed, _note, coerced = _try_parse_envelope(
        raw,
        gold_out=gold,
        compact=compact,
        deterministic_input_sha256=sha,
    )
    return (parsed if isinstance(parsed, dict) else None), coerced


def _insight_from_env(env: dict) -> str:
    return str(env.get("mkm_advanced_insight") or "").strip()


def _diff_keys(gold: dict, pred: dict) -> list[str]:
    keys = [
        "mkm_advanced_insight",
        "confidence_score",
        "method_id",
        "prohibition_ack",
        "hypothesis_tier",
        "boundary_ack",
        "human_review_required",
        "deterministic_input_sha256",
    ]
    out: list[str] = []
    for k in keys:
        if gold.get(k) != pred.get(k):
            out.append(k)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--eval-json", type=Path, default=DEFAULT_EVAL)
    ap.add_argument("--predictions-jsonl", type=Path, default=DEFAULT_PREDS)
    ap.add_argument("--sft-jsonl", type=Path, default=DEFAULT_SFT)
    ap.add_argument("--diversity-json", type=Path, default=DEFAULT_DIVERSITY)
    ap.add_argument("--sample-out", type=Path, default=DEFAULT_SAMPLE_OUT)
    ap.add_argument("--mismatch-out", type=Path, default=DEFAULT_MISMATCH_OUT)
    ap.add_argument("--empty-out", type=Path, default=DEFAULT_EMPTY_OUT)
    ap.add_argument("--sample-n", type=int, default=10)
    ap.add_argument("--seed", type=int, default=20260531)
    ap.add_argument(
        "--status-json",
        type=Path,
        default=DEFAULT_STATUS,
        help="Merge posteval artifact pointers into harness status JSON.",
    )
    ap.add_argument(
        "--preserve-commander-review",
        action="store_true",
        default=True,
        help="Keep commander_v1 verdicts on overlapping rows when sample-out already signed (default on).",
    )
    ap.add_argument(
        "--no-preserve-commander-review",
        action="store_false",
        dest="preserve_commander_review",
    )
    args = ap.parse_args()

    commander_by_row: dict[int, dict[str, Any]] = {}
    commander_top: dict[str, Any] = {}
    if args.preserve_commander_review:
        commander_by_row, commander_top = _commander_fields_from_prior(args.sample_out)

    for p in (args.eval_json, args.predictions_jsonl, args.sft_jsonl):
        if not p.is_file():
            print(f"missing: {p}", file=sys.stderr)
            return 2

    from scripts.audit_myeongri_interpret_narrative_diversity_v1 import _extract_insight

    eval_doc = json.loads(args.eval_json.read_text(encoding="utf-8"))
    preds = {int(p["row_index"]): p for p in _load_jsonl(args.predictions_jsonl)}
    sft_rows = _load_jsonl(args.sft_jsonl)
    per_eval = {int(r["row_index"]): r for r in eval_doc.get("per_row") or []}

    empty_rows: list[dict] = []
    mismatch_buckets: Counter[str] = Counter()
    row_details: list[dict] = []

    for i, sft_row in enumerate(sft_rows, start=1):
        gold = json.loads(str(sft_row.get("output", "{}")))
        pred_rec = preds.get(i, {})
        raw = str(pred_rec.get("prediction_raw", ""))
        parsed, _coerced = _parse_envelope(
            raw,
            gold=gold,
            instruction=str(sft_row.get("instruction", "")),
        ) if raw else (None, False)
        ev = per_eval.get(i, {})
        insight = (_extract_insight(raw) if raw else None) or ""
        if not insight:
            empty_rows.append(
                {
                    "row_index": i,
                    "parse_ok": ev.get("parse_ok"),
                    "envelope_coerced_from_template": ev.get("envelope_coerced_from_template"),
                    "prediction_raw_head": raw[:400] if raw else "",
                    "auto_note": "empty_insight_after_parse",
                }
            )
            continue
        if not parsed:
            continue
        diff = _diff_keys(gold, parsed)
        if diff:
            for k in diff:
                mismatch_buckets[k] += 1
            row_details.append(
                {
                    "row_index": i,
                    "diff_fields": diff,
                    "gold_method_id": gold.get("method_id"),
                    "pred_method_id": parsed.get("method_id"),
                    "gold_insight_head": _insight_from_env(gold)[:120],
                    "pred_insight_head": insight[:120],
                }
            )

    rng = random.Random(args.seed)
    pool: list[int] = list(per_eval.keys())
    empty_idx = {r["row_index"] for r in empty_rows}
    must = list(empty_idx)[: min(4, args.sample_n)]
    rest = [x for x in pool if x not in must]
    rng.shuffle(rest)
    pick = (must + rest)[: args.sample_n]

    samples: list[dict] = []
    for idx in pick:
        gold = json.loads(str(sft_rows[idx - 1].get("output", "{}")))
        pred_rec = preds.get(idx, {})
        raw = str(pred_rec.get("prediction_raw", ""))
        parsed, coerced = _parse_envelope(
            raw,
            gold=gold,
            instruction=str(sft_rows[idx - 1].get("instruction", "")),
        ) if raw else (None, False)
        ev = per_eval.get(idx, {})
        insight = (_extract_insight(raw) if raw else None) or ""
        auto_note = "empty_insight_after_parse" if not insight else "narrative_variant_ok"
        row_sample: dict[str, Any] = {
            "row_index": idx,
            "parse_ok": ev.get("parse_ok"),
            "envelope_match_normalized": ev.get("envelope_match_normalized"),
            "envelope_coerced_from_template": ev.get("envelope_coerced_from_template"),
            "postprocess_coerced": coerced,
            "mkm_advanced_insight": insight,
            "confidence_score": parsed.get("confidence_score") if parsed else None,
            "human_review_required": parsed.get("human_review_required") if parsed else None,
            "reviewer_prompts_ko": [
                "사주 4주·일간이 엔진 입력과 모순 없는가?",
                "가격·매매·의료 단정 표현이 없는가?",
                "[HYPO]·면책 문구가 적절한가?",
                "골드 envelope match 없이 coerce만으로 통과한 행인가?",
            ],
            "reviewer_verdict": None,
            "auto_note": auto_note,
            "gold_insight_head": _insight_from_env(gold)[:160],
        }
        if idx in commander_by_row:
            row_sample.update(commander_by_row[idx])
        samples.append(row_sample)

    div_pointer = ""
    if args.diversity_json.is_file():
        div_pointer = str(args.diversity_json.relative_to(ROOT)).replace("\\", "/")

    sample_doc = {
        "schema": "myeongri_interpret_v4_human_review_sample_v1",
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "boundary_ack": True,
        "seed": args.seed,
        "sample_n": len(samples),
        "population_eval": str(args.eval_json.relative_to(ROOT)).replace("\\", "/"),
        "adapter": eval_doc.get("adapter_path"),
        "instructions_ko": "reviewer_verdict: pass|fail|needs_edit. Track A·실매매 승격 판정 아님.",
        "diversity_audit_pointer": div_pointer,
        "samples": samples,
    }
    if commander_top:
        sample_doc.update(commander_top)
    args.sample_out.parent.mkdir(parents=True, exist_ok=True)
    args.sample_out.write_text(
        json.dumps(sample_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    mismatch_doc = {
        "schema": "myeongri_interpret_v4_match_mismatch_summary_v1",
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "boundary_ack": True,
        "eval_json": str(args.eval_json.relative_to(ROOT)).replace("\\", "/"),
        "rows": eval_doc.get("rows"),
        "parse_ok_rate": eval_doc.get("parse_ok_rate"),
        "envelope_match_rate": eval_doc.get("envelope_match_rate"),
        "envelope_coerced_rate": eval_doc.get("envelope_coerced_rate"),
        "empty_insight_row_count": len(empty_rows),
        "diff_field_counts": dict(mismatch_buckets),
        "interpretation_ko": (
            "match 0%는 모델 출력이 SFT gold envelope와 필드 단위로 다름. "
            "coerce 100%는 postprocess가 governance 필드를 맞춤. "
            "주된 diff는 insight 문구·confidence·method_id·prohibition_ack 등."
        ),
        "example_rows": row_details[:12],
    }
    args.mismatch_out.write_text(
        json.dumps(mismatch_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    empty_doc = {
        "schema": "myeongri_interpret_v4_empty_insight_rows_v1",
        "generated_at_utc": _utc_now(),
        "count": len(empty_rows),
        "rows": empty_rows,
    }
    args.empty_out.write_text(
        json.dumps(empty_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    if args.status_json.is_file():
        status = json.loads(args.status_json.read_text(encoding="utf-8"))
        v4 = status.setdefault("v4_variant_sft", {})
        v4["posteval_artifacts"] = {
            "generated_at_utc": _utc_now(),
            "human_review_sample": str(args.sample_out.relative_to(ROOT)).replace("\\", "/"),
            "match_mismatch_summary": str(args.mismatch_out.relative_to(ROOT)).replace("\\", "/"),
            "empty_insight_rows": str(args.empty_out.relative_to(ROOT)).replace("\\", "/"),
            "reparse_empty_insight_count": len(empty_rows),
            "postprocess_v2": "strip_leak+curly_quote+insight_regex_recovery+leak_truncated_fallback",
        }
        v4.setdefault("human_review_sample", {})["report"] = str(
            args.sample_out.relative_to(ROOT)
        ).replace("\\", "/")
        args.status_json.write_text(
            json.dumps(status, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )

    print(
        json.dumps(
            {
                "ok": True,
                "sample_out": str(args.sample_out),
                "mismatch_out": str(args.mismatch_out),
                "empty_count": len(empty_rows),
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
