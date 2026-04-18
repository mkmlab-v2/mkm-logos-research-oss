# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.85, L:0.84, K:0.5, M:0.66}
# Balance: 88
# Purpose: Export combined golden train+holdout rows to a TSV for human label review (spreadsheet).
# Keywords: LG, washer, golden, review, TSV, export
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any


ROOT = Path("C:/workspace")
ART = ROOT / "docs" / "final" / "artifacts"
DEFAULT_TRAIN = ART / "lg_washer_voice_golden_train_v1.jsonl"
DEFAULT_HOLDOUT = ART / "lg_washer_voice_golden_holdout_v1.jsonl"
DEFAULT_OUT = ART / "lg_washer_voice_golden_review_sheet_v1.tsv"


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def _sort_key(row: dict[str, Any]) -> tuple[str, str]:
    rid = str(row.get("id", ""))
    if rid.startswith("utt_"):
        return ("0", rid)
    return ("1", rid)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--train", type=Path, default=DEFAULT_TRAIN)
    ap.add_argument("--holdout", type=Path, default=DEFAULT_HOLDOUT)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    rows = _load_jsonl(args.train) + _load_jsonl(args.holdout)
    rows.sort(key=_sort_key)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "id",
        "split",
        "utterance",
        "intent",
        "slots_json",
        "expected_action",
        "data_tier",
        "build_pack",
        "conflict_hint",
        "ambiguity_hint",
        "review_status",
        "reviewer_note",
    ]
    with args.out.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, delimiter="\t", extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(
                {
                    "id": r.get("id", ""),
                    "split": r.get("split", ""),
                    "utterance": r.get("utterance", ""),
                    "intent": r.get("intent", ""),
                    "slots_json": json.dumps(r.get("slots") or {}, ensure_ascii=False, separators=(",", ":")),
                    "expected_action": r.get("expected_action", ""),
                    "data_tier": r.get("data_tier", ""),
                    "build_pack": r.get("build_pack", ""),
                    "conflict_hint": r.get("conflict_hint", ""),
                    "ambiguity_hint": r.get("ambiguity_hint", ""),
                    "review_status": "",
                    "reviewer_note": "",
                }
            )

    print(str(args.out))
    print(f"rows={len(rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
