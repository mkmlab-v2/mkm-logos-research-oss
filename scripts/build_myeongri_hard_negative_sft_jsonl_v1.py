#!/usr/bin/env python3
"""Build hard-negative SFT JSONL from recovery packet sample ids.

Purpose:
- Extract failure rows (json_parse_failed / parsed mismatch) from locked_eval golden set
- Emit stricter instruction/output pairs for targeted retry training

This is B-track data-prep only (no training launch).
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RECOVERY = ROOT / "reports/myeongri_alignment_recovery_packet_v1_latest.json"
DEFAULT_GOLDEN_LOCKED = ROOT / "data/training/myeongri_deterministic_lora_golden_bulk_v1/locked_eval.jsonl"
DEFAULT_GOLDEN_TRAIN = ROOT / "data/training/myeongri_deterministic_lora_golden_bulk_v1/train.jsonl"
DEFAULT_OUT = ROOT / "data/training/myeongri_deterministic_lora_hard_negative_sft_v1.jsonl"
DEFAULT_MANIFEST = ROOT / "reports/myeongri_hard_negative_sft_manifest_v1_latest.json"


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _load_jsonl_by_sample_id(path: Path) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    with path.open("r", encoding="utf-8-sig") as f:
        for raw in f:
            line = raw.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(row, dict):
                continue
            sid = row.get("sample_id")
            if isinstance(sid, str) and sid:
                out[sid] = row
    return out


def _row_to_strict_sft(row: dict[str, Any], reason: str) -> dict[str, Any]:
    utc = str(row.get("birth_instant_utc") or "").strip()
    tz = str(row.get("iana_tz") or "").strip()
    male = row.get("is_male")
    male_s = "unspecified (engine default false)" if male is None else ("true" if male else "false")
    exp = row.get("expected_result")
    if not isinstance(exp, dict):
        raise ValueError("expected_result must be object")

    instruction = (
        "STRICT deterministic myeongri task.\n"
        "Return ONLY one valid JSON object for schema saju_global_birth_result_v1.\n"
        "No markdown, no explanation, no extra keys, no trailing text.\n"
        "Required top-level keys: schema, version, resolution, full_saju.\n"
        "If full_saju.calculated_at exists, omit it.\n"
        f"birth_instant_utc: {utc}\n"
        f"iana_tz: {tz}\n"
        f"is_male: {male_s}"
    )
    return {
        "sample_id": row.get("sample_id"),
        "split": row.get("split"),
        "hard_negative_reason": reason,
        "instruction": instruction,
        "output": json.dumps(exp, ensure_ascii=False, separators=(",", ":")),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--recovery-json", type=Path, default=DEFAULT_RECOVERY)
    ap.add_argument("--golden-train-jsonl", type=Path, default=DEFAULT_GOLDEN_TRAIN)
    ap.add_argument("--golden-locked-jsonl", type=Path, default=DEFAULT_GOLDEN_LOCKED)
    ap.add_argument("--out-jsonl", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--manifest-json", type=Path, default=DEFAULT_MANIFEST)
    args = ap.parse_args()

    recovery = _load_json(args.recovery_json)
    by_id: dict[str, dict[str, Any]] = {}
    if args.golden_train_jsonl.is_file():
        by_id.update(_load_jsonl_by_sample_id(args.golden_train_jsonl))
    if args.golden_locked_jsonl.is_file():
        # keep train priority for duplicate ids, then fill missing from locked
        for sid, row in _load_jsonl_by_sample_id(args.golden_locked_jsonl).items():
            by_id.setdefault(sid, row)

    failed_parse_ids = [x for x in recovery.get("failed_parse_sample_ids", []) if isinstance(x, str)]
    mismatch_ids = [x for x in recovery.get("parsed_mismatch_sample_ids", []) if isinstance(x, str)]

    rows: list[dict[str, Any]] = []
    missing_ids: list[str] = []

    for sid in failed_parse_ids:
        src = by_id.get(sid)
        if not src:
            missing_ids.append(sid)
            continue
        rows.append(_row_to_strict_sft(src, "json_parse_failed"))

    for sid in mismatch_ids:
        src = by_id.get(sid)
        if not src:
            missing_ids.append(sid)
            continue
        rows.append(_row_to_strict_sft(src, "parsed_but_mismatch"))

    # Deduplicate while preserving order
    seen: set[str] = set()
    deduped: list[dict[str, Any]] = []
    for r in rows:
        sid = str(r.get("sample_id") or "")
        if not sid or sid in seen:
            continue
        seen.add(sid)
        deduped.append(r)

    args.out_jsonl.parent.mkdir(parents=True, exist_ok=True)
    with args.out_jsonl.open("w", encoding="utf-8") as f:
        for r in deduped:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    manifest = {
        "schema": "myeongri_hard_negative_sft_manifest_v1",
        "recovery_json": str(args.recovery_json).replace("\\", "/"),
        "golden_locked_jsonl": str(args.golden_locked_jsonl).replace("\\", "/"),
        "golden_train_jsonl": str(args.golden_train_jsonl).replace("\\", "/"),
        "out_jsonl": str(args.out_jsonl).replace("\\", "/"),
        "counts": {
            "failed_parse_ids": len(failed_parse_ids),
            "parsed_mismatch_ids": len(mismatch_ids),
            "written_rows": len(deduped),
            "missing_ids": len(missing_ids),
        },
        "missing_ids": missing_ids,
        "track_wall": {
            "research_only": True,
            "a_track_auto_promotion": False,
            "live_trading": False,
        },
    }
    args.manifest_json.parent.mkdir(parents=True, exist_ok=True)
    args.manifest_json.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(
        json.dumps(
            {
                "ok": True,
                "out_jsonl": str(args.out_jsonl),
                "rows": len(deduped),
                "missing_ids": len(missing_ids),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

