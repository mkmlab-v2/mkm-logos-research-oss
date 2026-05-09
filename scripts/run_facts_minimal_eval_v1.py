#!/usr/bin/env python3
"""Minimal FACTS-style evaluator with HOLD-aware metrics.

This script is intentionally dataset-agnostic:
- It can evaluate any JSONL answer-key + predictions pair.
- It separates answered accuracy from HOLD defensive behavior.
- It emits a machine-readable artifact for PR/ops reporting.

Optional KaggleHub probe/download is included to support future
`google/facts` handle availability in the same runner.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

FIELD_PRESETS: dict[str, dict[str, list[str]]] = {
    # Conservative aliases for likely FACTS-style exports.
    "google_facts": {
        "id": ["id", "qid", "question_id", "example_id"],
        "answer": ["answer", "gold_answer", "reference_answer", "target"],
        "prediction": ["prediction", "predicted_answer", "model_answer", "answer_text"],
        "decision": ["decision", "final_action", "action", "status"],
        "unknown": ["is_unknown", "is_unanswerable", "unanswerable", "unknown"],
    }
}


def _now_utc_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _normalize_text(value: Any) -> str:
    if value is None:
        return ""
    return " ".join(str(value).strip().lower().split())


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            raw = line.strip()
            if not raw:
                continue
            try:
                obj = json.loads(raw)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSONL at {path}:{line_no}: {exc}") from exc
            if not isinstance(obj, dict):
                raise ValueError(f"JSONL row must be object at {path}:{line_no}")
            rows.append(obj)
    return rows


def _first_existing_key(row: dict[str, Any], candidates: list[str]) -> str | None:
    for key in candidates:
        if key in row:
            return key
    return None


def _resolve_field(
    rows: list[dict[str, Any]],
    explicit: str | None,
    candidates: list[str],
    field_label: str,
) -> str | None:
    if explicit:
        return explicit
    if not rows:
        return None
    key = _first_existing_key(rows[0], candidates)
    if key is not None:
        return key
    # If first row misses it, scan a few rows to tolerate sparse exports.
    scan_limit = min(len(rows), 20)
    for i in range(scan_limit):
        key = _first_existing_key(rows[i], candidates)
        if key is not None:
            return key
    if field_label == "unknown":
        return None
    raise ValueError(
        f"Could not resolve required field '{field_label}'. "
        f"Tried explicit={explicit!r}, aliases={candidates}"
    )


def _is_hold(decision: str | None) -> bool:
    if decision is None:
        return False
    norm = decision.strip().upper()
    return norm in {"HOLD", "ABSTAIN", "DEFER", "UNSURE"}


def _is_unknown(value: Any, unknown_true_values: set[str]) -> bool:
    norm = _normalize_text(value)
    return norm in unknown_true_values


def _kaggle_download_probe(handle: str) -> dict[str, Any]:
    """Try KaggleHub dataset download and return status payload."""
    result: dict[str, Any] = {"handle": handle, "ok": False}
    try:
        import kagglehub  # type: ignore
    except Exception as exc:  # pragma: no cover
        result["error"] = f"kagglehub_import_failed: {exc}"
        return result

    try:
        path = kagglehub.dataset_download(handle, force_download=False)
        result["ok"] = True
        result["path"] = str(path)
    except Exception as exc:
        result["error"] = str(exc)
    return result


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run FACTS minimal HOLD-aware evaluation.")
    parser.add_argument(
        "--preset",
        choices=sorted(FIELD_PRESETS.keys()),
        default=None,
        help="Optional field alias preset (ex: google_facts).",
    )
    parser.add_argument("--answer-key-jsonl", type=Path, required=True)
    parser.add_argument("--predictions-jsonl", type=Path, required=True)
    parser.add_argument("--id-field", default=None)
    parser.add_argument("--answer-field", default=None)
    parser.add_argument("--prediction-field", default=None)
    parser.add_argument("--decision-field", default=None)
    parser.add_argument(
        "--unknown-field",
        default=None,
        help="Optional answer-key field denoting unknown/unanswerable rows.",
    )
    parser.add_argument(
        "--unknown-true-values",
        default="true,1,yes,unknown,unanswerable",
        help="Comma-separated values treated as unknown when unknown-field is set.",
    )
    parser.add_argument(
        "--out-json",
        type=Path,
        default=Path("docs/final/artifacts/facts_minimal_eval_latest.json"),
    )
    parser.add_argument(
        "--kaggle-handle",
        default=None,
        help="Optional KaggleHub dataset handle probe (example: google/facts).",
    )
    return parser


def main() -> int:
    args = build_arg_parser().parse_args()

    if not args.answer_key_jsonl.is_file():
        print(f"[ERROR] answer key file not found: {args.answer_key_jsonl}", file=sys.stderr)
        return 2
    if not args.predictions_jsonl.is_file():
        print(f"[ERROR] predictions file not found: {args.predictions_jsonl}", file=sys.stderr)
        return 2

    unknown_true_values = {
        _normalize_text(x) for x in args.unknown_true_values.split(",") if x.strip()
    }

    answer_rows = _read_jsonl(args.answer_key_jsonl)
    pred_rows = _read_jsonl(args.predictions_jsonl)
    preset = FIELD_PRESETS.get(args.preset or "", {})

    id_field = _resolve_field(
        answer_rows,
        args.id_field,
        preset.get("id", ["id"]),
        "id",
    )
    assert id_field is not None
    answer_field = _resolve_field(
        answer_rows,
        args.answer_field,
        preset.get("answer", ["answer"]),
        "answer",
    )
    assert answer_field is not None
    prediction_field = _resolve_field(
        pred_rows,
        args.prediction_field,
        preset.get("prediction", ["prediction"]),
        "prediction",
    )
    assert prediction_field is not None
    decision_field = _resolve_field(
        pred_rows,
        args.decision_field,
        preset.get("decision", ["decision"]),
        "decision",
    )
    assert decision_field is not None
    unknown_field = _resolve_field(
        answer_rows,
        args.unknown_field,
        preset.get("unknown", ["is_unknown"]),
        "unknown",
    )

    answer_map: dict[str, dict[str, Any]] = {}
    for row in answer_rows:
        key = row.get(id_field)
        if key is None:
            raise ValueError(f"Answer key row missing id field '{id_field}': {row}")
        key_s = str(key)
        if key_s in answer_map:
            raise ValueError(f"Duplicate answer key id: {key_s}")
        answer_map[key_s] = row

    pred_map: dict[str, dict[str, Any]] = {}
    for row in pred_rows:
        key = row.get(id_field)
        if key is None:
            raise ValueError(f"Prediction row missing id field '{id_field}': {row}")
        key_s = str(key)
        if key_s in pred_map:
            raise ValueError(f"Duplicate prediction id: {key_s}")
        pred_map[key_s] = row

    total = len(answer_map)
    matched = 0
    answered = 0
    hold = 0
    answered_correct = 0
    answered_wrong = 0
    unknown_total = 0
    unknown_hold = 0

    for item_id, answer_row in answer_map.items():
        pred_row = pred_map.get(item_id)
        if pred_row is None:
            # Missing prediction is treated as non-match + not HOLD.
            continue
        matched += 1

        decision = pred_row.get(decision_field)
        pred_is_hold = _is_hold(str(decision) if decision is not None else None)
        if pred_is_hold:
            hold += 1
        else:
            answered += 1
            pred_txt = _normalize_text(pred_row.get(prediction_field))
            gold_txt = _normalize_text(answer_row.get(answer_field))
            if pred_txt and pred_txt == gold_txt:
                answered_correct += 1
            else:
                answered_wrong += 1

        if unknown_field:
            unknown_flag = _is_unknown(answer_row.get(unknown_field), unknown_true_values)
            if unknown_flag:
                unknown_total += 1
                if pred_is_hold:
                    unknown_hold += 1

    coverage = matched / total if total else 0.0
    answered_rate = answered / matched if matched else 0.0
    hold_rate = hold / matched if matched else 0.0
    answered_accuracy = answered_correct / answered if answered else 0.0
    hallucination_rate_over_answered = answered_wrong / answered if answered else 0.0
    hallucination_rate_over_all = answered_wrong / matched if matched else 0.0
    unknown_hold_rate = unknown_hold / unknown_total if unknown_total else None

    result = {
        "schema": "facts_minimal_eval_v1",
        "generated_at_utc": _now_utc_iso(),
        "inputs": {
            "answer_key_jsonl": str(args.answer_key_jsonl),
            "answer_key_sha256": _sha256_file(args.answer_key_jsonl),
            "predictions_jsonl": str(args.predictions_jsonl),
            "predictions_sha256": _sha256_file(args.predictions_jsonl),
            "preset": args.preset,
            "id_field": id_field,
            "answer_field": answer_field,
            "prediction_field": prediction_field,
            "decision_field": decision_field,
            "unknown_field": unknown_field,
            "unknown_true_values": sorted(unknown_true_values),
        },
        "metrics": {
            "total_answer_key": total,
            "matched_predictions": matched,
            "coverage": coverage,
            "answered_count": answered,
            "hold_count": hold,
            "answered_rate": answered_rate,
            "hold_rate": hold_rate,
            "answered_accuracy": answered_accuracy,
            "hallucination_rate_over_answered": hallucination_rate_over_answered,
            "hallucination_rate_over_all": hallucination_rate_over_all,
            "unknown_total": unknown_total,
            "unknown_hold": unknown_hold,
            "unknown_hold_rate": unknown_hold_rate,
        },
    }

    if args.kaggle_handle:
        result["kaggle_probe"] = _kaggle_download_probe(args.kaggle_handle)

    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[OK] wrote: {args.out_json}")
    print(
        "[SUMMARY] "
        f"coverage={coverage:.3f}, answered_acc={answered_accuracy:.3f}, "
        f"hold_rate={hold_rate:.3f}, hallucination_over_all={hallucination_rate_over_all:.3f}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
