# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.86, L:0.84, K:0.48, M:0.68}
# Balance: 90
# Purpose: Build stress-test augmented utterances from golden TRAIN only (no holdout leakage).
# Keywords: LG, washer, augmentation, robustness, jsonl
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
DEFAULT_TRAIN = ART / "lg_washer_voice_golden_train_v1.jsonl"
DEFAULT_OUT_PREVIEW = ART / "lg_washer_voice_augmented_stress_preview_v1.jsonl"
DEFAULT_OUT_FULL = ART / "lg_washer_voice_augmented_stress_full_v1.jsonl"
DEFAULT_MANIFEST = ART / "lg_washer_voice_augmented_manifest_v1.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_train(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def _pick_transform(i: int) -> tuple[str, str]:
    kinds = (
        ("prefix_please", "제발 "),
        ("suffix_polite", None),
        ("mid_space", None),
        ("prefix_filler", "어 "),
        ("dup_first_syllable", None),
    )
    name, _ = kinds[i % len(kinds)]
    return name, kinds[i % len(kinds)][1] or ""


def _perturb(utterance: str, i: int) -> tuple[str, str]:
    name, prefix = _pick_transform(i)
    u = utterance.strip()
    if not u:
        return u, "noop"
    if name == "prefix_please":
        return prefix + u, name
    if name == "suffix_polite":
        return u + " 부탁해", name
    if name == "mid_space" and len(u) > 2:
        mid = max(1, len(u) // 2)
        return u[:mid] + " " + u[mid:], name
    if name == "prefix_filler":
        return prefix + u, name
    if name == "dup_first_syllable" and len(u) >= 1:
        return u[0] + u, name
    return u, "noop"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--train", type=Path, default=DEFAULT_TRAIN)
    ap.add_argument("--count", type=int, default=2000, help="Number of augmented rows (default preview size)")
    ap.add_argument("--out", type=Path, default=None, help="Output JSONL (default: preview or full path by count)")
    ap.add_argument("--manifest-out", type=Path, default=DEFAULT_MANIFEST)
    args = ap.parse_args()

    if args.count < 1:
        raise SystemExit("--count must be >= 1")

    if args.out is None:
        args.out = DEFAULT_OUT_FULL if args.count >= 10000 else DEFAULT_OUT_PREVIEW

    seeds = _load_train(args.train)
    if not seeds:
        raise SystemExit("No train rows")

    out_rows: list[dict[str, Any]] = []
    for i in range(args.count):
        seed = seeds[i % len(seeds)]
        surface, xform = _perturb(str(seed.get("utterance", "")), i)
        rid = f"aug_{i + 1:06d}"
        out_rows.append(
            {
                "schema": "lg_washer_voice_augmented_stress_v1",
                "id": rid,
                "lineage_seed_id": seed.get("id"),
                "lineage_seed_split": "train_only",
                "utterance_surface": surface,
                "intent": seed.get("intent"),
                "slots": seed.get("slots"),
                "expected_action": seed.get("expected_action"),
                "transform_kind": xform,
                "data_tier": "augmented_stress_v1",
                "usage_policy": "stress_robustness_only",
                "note_ko": "골든 홀드아웃 지표·제출 성적서와 혼용 금지.",
            }
        )

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8", newline="\n") as f:
        for row in out_rows:
            f.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")

    manifest = {
        "schema": "lg_washer_voice_augmented_manifest_v1",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "source_train_only": str(args.train.relative_to(ROOT)).replace("\\", "/"),
        "output_jsonl": str(args.out.relative_to(ROOT)).replace("\\", "/"),
        "record_count": len(out_rows),
        "governance_ko": [
            "시드는 골든 train JSONL만 사용(홀드아웃 누수 방지).",
            "대외 제출 시 '실측 골든'·정확도 리포트에 본 말뭉치를 섞지 않는다.",
        ],
        "builder": "scripts/build_lg_washer_voice_augmented_jsonl_v1.py",
    }
    args.manifest_out.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(str(args.out))
    print(str(args.manifest_out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
