#!/usr/bin/env python3
"""Re-score interpret LoRA preds with postprocess_v1 (no GPU). B-track only."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.myeongri_interpret_envelope_views_v1 import extract_compact_from_interpret_instruction  # noqa: E402
from scripts.run_myeongri_harness_v2_engine_interpret_smoke_v1 import _try_parse_envelope  # noqa: E402


def _load_jsonl(path: Path) -> list[dict]:
    rows: list[dict] = []
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def _canonical_envelope(obj: dict) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--preds-jsonl",
        type=Path,
        default=ROOT / "reports/myeongri_interpret_pivot_a_preds_full_latest.jsonl",
    )
    ap.add_argument(
        "--sft-jsonl",
        type=Path,
        default=ROOT / "data/training/myeongri_interpret_sft_v2/locked_eval.jsonl",
    )
    ap.add_argument(
        "--report-json",
        type=Path,
        default=ROOT / "reports/myeongri_interpret_pivot_a_eval_postprocess_v1_latest.json",
    )
    args = ap.parse_args()

    preds = _load_jsonl(args.preds_jsonl)
    gold_rows = _load_jsonl(args.sft_jsonl)
    n = min(len(preds), len(gold_rows))
    if n == 0:
        print("no rows", file=sys.stderr)
        return 2

    raw_match = post_match = parse_ok = 0
    per_row: list[dict[str, Any]] = []
    for i in range(n):
        raw = str(preds[i].get("prediction_raw", ""))
        gold_out = json.loads(str(gold_rows[i].get("output", "{}")))
        compact = extract_compact_from_interpret_instruction(str(gold_rows[i].get("instruction", "")))
        gold_sha = str(gold_out.get("deterministic_input_sha256") or "")
        p0, n0, _ = _try_parse_envelope(
            raw,
            gold_out=gold_out,
            postprocess_v1=False,
            compact=compact,
            deterministic_input_sha256=gold_sha,
        )
        p1, n1, coerced = _try_parse_envelope(
            raw,
            gold_out=gold_out,
            postprocess_v1=True,
            compact=compact,
            deterministic_input_sha256=gold_sha,
        )
        ok0 = p0 is not None and n0 == "" and _canonical_envelope(p0) == _canonical_envelope(gold_out)
        ok1 = p1 is not None and n1 == "" and _canonical_envelope(p1) == _canonical_envelope(gold_out)
        if p1 is not None and n1 == "":
            parse_ok += 1
        if ok0:
            raw_match += 1
        if ok1:
            post_match += 1
        per_row.append(
            {
                "row_index": i + 1,
                "parse_ok_postprocess": p1 is not None and n1 == "",
                "envelope_match_raw": ok0,
                "envelope_match_postprocess_v1": ok1,
                "gained_by_postprocess": (not ok0) and ok1,
            }
        )

    report = {
        "schema": "myeongri_interpret_postprocess_replay_v1",
        "preds_jsonl": str(args.preds_jsonl).replace("\\", "/"),
        "rows": n,
        "parse_ok_rate_postprocess": round(parse_ok / n, 6),
        "envelope_match_rate_raw": round(raw_match / n, 6),
        "envelope_match_rate_postprocess_v1": round(post_match / n, 6),
        "rows_gained": sum(1 for r in per_row if r["gained_by_postprocess"]),
        "per_row": per_row,
        "track": "B-track",
        "hypothesis_tier": "B",
    }
    args.report_json.parent.mkdir(parents=True, exist_ok=True)
    args.report_json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "envelope_match_raw": report["envelope_match_rate_raw"],
                "envelope_match_postprocess_v1": report["envelope_match_rate_postprocess_v1"],
                "rows_gained": report["rows_gained"],
                "out": str(args.report_json),
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
