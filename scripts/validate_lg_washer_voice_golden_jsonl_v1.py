# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.88, L:0.86, K:0.55, M:0.7}
# Balance: 92
# Purpose: Validate LG washer golden train/holdout JSONL and optional split manifest alignment.
# Keywords: LG, washer, golden, jsonl, validation, manifest
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
DEFAULT_TRAIN = ART / "lg_washer_voice_golden_train_v1.jsonl"
DEFAULT_HOLDOUT = ART / "lg_washer_voice_golden_holdout_v1.jsonl"
DEFAULT_MANIFEST = ART / "lg_washer_voice_golden_split_manifest_v1.json"

REQUIRED_KEYS = (
    "schema",
    "id",
    "utterance",
    "intent",
    "slots",
    "split",
    "expected_action",
)


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as f:
        for lineno, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise SystemExit(f"{path}: line {lineno}: JSON decode error: {exc}") from exc
    return rows


def _validate_rows(rows: list[dict[str, Any]], *, split_expected: str | None, path: Path) -> Counter[str]:
    intents: Counter[str] = Counter()
    for i, row in enumerate(rows, 1):
        for k in REQUIRED_KEYS:
            if k not in row:
                raise SystemExit(f"{path}: row {i}: missing key {k!r}")
        if row.get("schema") != "lg_washer_voice_utterance_v1":
            raise SystemExit(f"{path}: row {i}: schema must be lg_washer_voice_utterance_v1")
        if split_expected is not None and row.get("split") != split_expected:
            raise SystemExit(f"{path}: row {i}: split must be {split_expected!r}, got {row.get('split')!r}")
        if not isinstance(row.get("slots"), dict):
            raise SystemExit(f"{path}: row {i}: slots must be object")
        intents[str(row["intent"])] += 1
    return intents


def _validate_manifest_alignment(
    manifest: dict[str, Any],
    train_rows: list[dict[str, Any]],
    hold_rows: list[dict[str, Any]],
) -> None:
    sp = manifest.get("split_policy") or {}
    tc = sp.get("train_count")
    hc = sp.get("holdout_count")
    if tc is not None and tc != len(train_rows):
        raise SystemExit(f"Manifest train_count {tc} != file {len(train_rows)}")
    if hc is not None and hc != len(hold_rows):
        raise SystemExit(f"Manifest holdout_count {hc} != file {len(hold_rows)}")

    ct = sp.get("counts_total_per_intent")
    ctr = sp.get("counts_train_per_intent")
    cth = sp.get("counts_holdout_per_intent")
    if not (isinstance(ct, dict) and isinstance(ctr, dict) and isinstance(cth, dict)):
        return

    tr_i = Counter(str(r["intent"]) for r in train_rows)
    ho_i = Counter(str(r["intent"]) for r in hold_rows)
    all_i = tr_i + ho_i
    for intent, n in all_i.items():
        if ct.get(intent) != n:
            raise SystemExit(f"Intent {intent}: total count mismatch manifest {ct.get(intent)} vs files {n}")
    for intent, n in tr_i.items():
        if ctr.get(intent) != n:
            raise SystemExit(f"Intent {intent}: train count mismatch manifest {ctr.get(intent)} vs file {n}")
    for intent, n in ho_i.items():
        if cth.get(intent) != n:
            raise SystemExit(f"Intent {intent}: holdout count mismatch manifest {cth.get(intent)} vs file {n}")


AUGMENTED_REQUIRED = (
    "schema",
    "id",
    "utterance_surface",
    "intent",
    "slots",
    "lineage_seed_id",
    "data_tier",
    "usage_policy",
)


def _validate_augmented_rows(rows: list[dict[str, Any]], path: Path) -> None:
    for i, row in enumerate(rows, 1):
        for k in AUGMENTED_REQUIRED:
            if k not in row:
                raise SystemExit(f"{path}: row {i}: missing key {k!r}")
        if row.get("schema") != "lg_washer_voice_augmented_stress_v1":
            raise SystemExit(f"{path}: row {i}: schema must be lg_washer_voice_augmented_stress_v1")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--train", type=Path, default=DEFAULT_TRAIN)
    ap.add_argument("--holdout", type=Path, default=DEFAULT_HOLDOUT)
    ap.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    ap.add_argument("--skip-manifest", action="store_true", help="Only validate JSONL rows, not manifest counts")
    ap.add_argument("--jsonl", type=Path, default=None, help="If set, validate this file only (no split/manifest)")
    ap.add_argument(
        "--profile",
        choices=("golden", "augmented"),
        default="golden",
        help="When using --jsonl, which schema to enforce",
    )
    args = ap.parse_args()

    if args.jsonl is not None:
        rows = _load_jsonl(args.jsonl)
        if args.profile == "golden":
            _validate_rows(rows, split_expected=None, path=args.jsonl)
        else:
            _validate_augmented_rows(rows, args.jsonl)
        ids = [r["id"] for r in rows]
        if len(ids) != len(set(ids)):
            raise SystemExit(f"{args.jsonl}: duplicate ids")
        print(f"ok {args.jsonl} ({len(rows)} rows) profile={args.profile}")
        return 0

    train_rows = _load_jsonl(args.train)
    hold_rows = _load_jsonl(args.holdout)
    _validate_rows(train_rows, split_expected="train", path=args.train)
    _validate_rows(hold_rows, split_expected="holdout", path=args.holdout)

    ids = [r["id"] for r in train_rows] + [r["id"] for r in hold_rows]
    if len(ids) != len(set(ids)):
        raise SystemExit("Duplicate id across train and holdout")

    if not args.skip_manifest and args.manifest.exists():
        manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
        _validate_manifest_alignment(manifest, train_rows, hold_rows)

    print(f"ok train={len(train_rows)} holdout={len(hold_rows)} total={len(train_rows)+len(hold_rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
