# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.9, L:0.88, K:0.45, M:0.72}
# Balance: 93
# Purpose: Export LG washer golden sample records to train/holdout JSONL + split manifest.
# Keywords: LG, washer, golden dataset, jsonl, holdout, PoC
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path("C:/workspace")
ART = ROOT / "docs" / "final" / "artifacts"
DEFAULT_SRC = ART / "lg_washer_integrity_validation_report_sample_v1.json"
OUT_TRAIN = ART / "lg_washer_voice_golden_train_v1.jsonl"
OUT_HOLDOUT = ART / "lg_washer_voice_golden_holdout_v1.jsonl"
OUT_MANIFEST = ART / "lg_washer_voice_golden_split_manifest_v1.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")


def main() -> int:
    ap = argparse.ArgumentParser(description="Build LG washer golden JSONL splits from sample report.")
    ap.add_argument("--src", type=Path, default=DEFAULT_SRC, help="Source sample report JSON")
    ap.add_argument("--train-out", type=Path, default=OUT_TRAIN)
    ap.add_argument("--holdout-out", type=Path, default=OUT_HOLDOUT)
    ap.add_argument("--manifest-out", type=Path, default=OUT_MANIFEST)
    args = ap.parse_args()

    doc = _load(args.src)
    records = list(doc.get("sample_records") or [])
    if not records:
        raise SystemExit("No sample_records in source JSON.")

    # Deterministic split: first 12 train, last 8 holdout (20-sample demo pack).
    train_ids = {r["id"] for r in records[:12]}
    holdout_ids = {r["id"] for r in records[12:]}

    train_rows: list[dict[str, Any]] = []
    holdout_rows: list[dict[str, Any]] = []
    for r in records:
        rid = str(r.get("id"))
        split = "train" if rid in train_ids else "holdout"
        row = {
            "schema": "lg_washer_voice_utterance_v1",
            "split": split,
            "source_report": str(args.src.relative_to(ROOT)).replace("\\", "/"),
            **r,
        }
        if split == "train":
            train_rows.append(row)
        else:
            holdout_rows.append(row)

    _write_jsonl(args.train_out, train_rows)
    _write_jsonl(args.holdout_out, holdout_rows)

    manifest = {
        "schema": "lg_washer_voice_golden_split_manifest_v1",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "source_report": str(args.src.relative_to(ROOT)).replace("\\", "/"),
        "outputs": {
            "train_jsonl": str(args.train_out.relative_to(ROOT)).replace("\\", "/"),
            "holdout_jsonl": str(args.holdout_out.relative_to(ROOT)).replace("\\", "/"),
        },
        "split_policy": {
            "note": "Demo split for 20-sample pack: first 12 train, last 8 holdout.",
            "train_count": len(train_rows),
            "holdout_count": len(holdout_rows),
            "train_ids": [r["id"] for r in train_rows],
            "holdout_ids": [r["id"] for r in holdout_rows],
        },
    }
    args.manifest_out.parent.mkdir(parents=True, exist_ok=True)
    args.manifest_out.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(str(args.train_out))
    print(str(args.holdout_out))
    print(str(args.manifest_out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
