#!/usr/bin/env python3
"""Normalize model raw outputs into FACTS minimal prediction JSONL.

Input JSONL rows may contain heterogeneous keys. This script maps them into:
  {"id": "...", "decision": "ANSWER|HOLD", "prediction": "..."}

Use this before `run_facts_minimal_eval_v1.py`.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


PRESETS: dict[str, dict[str, list[str]]] = {
    "generic_model": {
        "id": ["id", "qid", "question_id", "example_id"],
        "decision": ["decision", "final_action", "action", "status", "label"],
        "prediction": ["prediction", "answer", "model_answer", "response", "text"],
    }
}


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            raw = line.strip()
            if not raw:
                continue
            obj = json.loads(raw)
            if not isinstance(obj, dict):
                raise ValueError(f"Row must be object: {path}:{line_no}")
            rows.append(obj)
    return rows


def _pick(row: dict[str, Any], explicit: str | None, aliases: list[str]) -> Any:
    if explicit:
        return row.get(explicit)
    for key in aliases:
        if key in row:
            return row.get(key)
    return None


def _normalize_decision(v: Any) -> str:
    if v is None:
        return "ANSWER"
    s = str(v).strip().upper()
    if s in {"HOLD", "ABSTAIN", "DEFER", "UNSURE"}:
        return "HOLD"
    return "ANSWER"


def main() -> int:
    parser = argparse.ArgumentParser(description="Normalize raw model outputs for FACTS minimal eval.")
    parser.add_argument("--raw-jsonl", type=Path, required=True)
    parser.add_argument("--out-jsonl", type=Path, required=True)
    parser.add_argument("--preset", choices=sorted(PRESETS.keys()), default="generic_model")
    parser.add_argument("--id-field", default=None)
    parser.add_argument("--decision-field", default=None)
    parser.add_argument("--prediction-field", default=None)
    args = parser.parse_args()

    rows = _read_jsonl(args.raw_jsonl)
    preset = PRESETS[args.preset]
    out_rows: list[dict[str, Any]] = []
    for i, row in enumerate(rows, start=1):
        row_id = _pick(row, args.id_field, preset["id"])
        if row_id is None:
            raise ValueError(f"Missing id at row {i}")
        decision = _normalize_decision(_pick(row, args.decision_field, preset["decision"]))
        pred_val = _pick(row, args.prediction_field, preset["prediction"])
        prediction = "" if pred_val is None else str(pred_val)
        out_rows.append({"id": str(row_id), "decision": decision, "prediction": prediction})

    args.out_jsonl.parent.mkdir(parents=True, exist_ok=True)
    with args.out_jsonl.open("w", encoding="utf-8") as f:
        for row in out_rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    print(f"[OK] wrote {len(out_rows)} rows -> {args.out_jsonl}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
