#!/usr/bin/env python3
"""Prepare Nemotron Kaggle competition CSV for data prep only (no Kaggle GPU).

MKM train GPU lane: NVIDIA Innovation Lab / Brev credits — see
docs/final/artifacts/nvidia_gpu_credit_lane_policy_v1.json (kaggle_gpu=cancelled).
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

DEFAULT_SLUG = "nvidia-nemotron-model-reasoning-challenge"
DEFAULT_BASE_MODEL = "nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-BF16"
MAX_LORA_RANK = 32


def _now_utc_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _read_csv_rows(path: Path, limit: int | None) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            raise ValueError(f"Empty CSV: {path}")
        for i, row in enumerate(reader):
            if limit is not None and i >= limit:
                break
            rows.append({k: (v or "") for k, v in row.items()})
    return rows


def _prompt_stats(rows: list[dict[str, str]]) -> dict[str, Any]:
    lengths = [len(r.get("prompt", "")) for r in rows]
    answers = [len(r.get("answer", "")) for r in rows if r.get("answer")]
    return {
        "row_count": len(rows),
        "prompt_chars_min": min(lengths) if lengths else 0,
        "prompt_chars_max": max(lengths) if lengths else 0,
        "prompt_chars_mean": (sum(lengths) / len(lengths)) if lengths else 0.0,
        "answer_chars_mean": (sum(answers) / len(answers)) if answers else 0.0,
    }


def _to_sft_record(row: dict[str, str]) -> dict[str, str]:
    return {
        "id": row["id"],
        "instruction": row["prompt"],
        "output": row.get("answer", ""),
    }


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Private Nemotron Kaggle data prep (no submit).")
    p.add_argument("--slug", default=DEFAULT_SLUG)
    p.add_argument("--workspace-root", type=Path, default=Path(__file__).resolve().parents[1])
    p.add_argument("--limit", type=int, default=0, help="0 = all train rows; else cap for smoke.")
    p.add_argument(
        "--out-report-json",
        type=Path,
        default=Path("reports/kaggle_nemotron_private_prep_latest.json"),
    )
    p.add_argument(
        "--out-train-jsonl",
        type=Path,
        default=None,
        help="Default: data/kaggle/<slug>/processed/sft_train.jsonl",
    )
    p.add_argument("--base-model", default=DEFAULT_BASE_MODEL)
    p.add_argument("--lora-rank", type=int, default=16, help=f"Competition max rank {MAX_LORA_RANK}.")
    return p


def main() -> int:
    args = build_arg_parser().parse_args()
    if args.lora_rank > MAX_LORA_RANK:
        print(f"[ERROR] lora-rank must be <= {MAX_LORA_RANK}", file=sys.stderr)
        return 1

    root = args.workspace_root
    data_dir = root / "data" / "kaggle" / args.slug
    train_csv = data_dir / "train.csv"
    test_csv = data_dir / "test.csv"
    if not train_csv.is_file():
        print(f"[ERROR] missing {train_csv}", file=sys.stderr)
        return 1
    if not test_csv.is_file():
        print(f"[ERROR] missing {test_csv}", file=sys.stderr)
        return 1

    limit = None if args.limit <= 0 else args.limit
    train_rows = _read_csv_rows(train_csv, limit)
    test_rows = _read_csv_rows(test_csv, min(8, limit or 8))

    for name, rows, required in (
        ("train", train_rows, {"id", "prompt", "answer"}),
        ("test", test_rows, {"id", "prompt"}),
    ):
        if not rows:
            print(f"[ERROR] no rows in {name}", file=sys.stderr)
            return 1
        keys = set(rows[0].keys())
        missing = required - keys
        if missing:
            print(f"[ERROR] {name} missing columns: {sorted(missing)}", file=sys.stderr)
            return 1

    processed_dir = data_dir / "processed"
    processed_dir.mkdir(parents=True, exist_ok=True)
    if args.out_train_jsonl:
        out_jsonl = args.out_train_jsonl if args.out_train_jsonl.is_absolute() else root / args.out_train_jsonl
    elif limit:
        out_jsonl = processed_dir / f"sft_train_limit{limit}.jsonl"
    else:
        out_jsonl = processed_dir / "sft_train.jsonl"

    with out_jsonl.open("w", encoding="utf-8") as f:
        for row in train_rows:
            f.write(json.dumps(_to_sft_record(row), ensure_ascii=False) + "\n")

    def _rel(p: Path) -> str:
        try:
            return str(p.relative_to(root)).replace("\\", "/")
        except ValueError:
            return str(p).replace("\\", "/")

    report: dict[str, Any] = {
        "schema": "kaggle_nemotron_private_prep_v1",
        "generated_at_utc": _now_utc_iso(),
        "lane": "private_dev_no_mkm_core",
        "competition_slug": args.slug,
        "data_dir": _rel(data_dir),
        "inputs": {
            "train_csv": _rel(train_csv),
            "train_sha256": _sha256_file(train_csv),
            "test_csv": _rel(test_csv),
            "test_sha256": _sha256_file(test_csv),
            "limit_applied": limit,
        },
        "train_stats": _prompt_stats(train_rows),
        "test_stats_preview": _prompt_stats(test_rows),
        "outputs": {
            "sft_train_jsonl": _rel(out_jsonl),
            "sft_rows_written": len(train_rows),
        },
        "lora_plan": {
            "base_model_hf_id": args.base_model,
            "lora_rank": args.lora_rank,
            "max_lora_rank_competition": MAX_LORA_RANK,
            "submit_allowed_by_policy": False,
            "next_step_local": "Run run_kaggle_nemotron_private_lora_smoke_v1.py --dry-run (config only) "
            "then full train on Kaggle GPU notebook or Azure NC when approved.",
        },
        "mkm_core_exposed": False,
    }

    out_report = args.out_report_json if args.out_report_json.is_absolute() else root / args.out_report_json
    out_report.parent.mkdir(parents=True, exist_ok=True)
    out_report.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"[OK] wrote SFT JSONL: {out_jsonl} ({len(train_rows)} rows)")
    print(f"[OK] wrote report: {out_report}")
    print(f"[SUMMARY] train_rows={len(train_rows)} lora_rank={args.lora_rank} base={args.base_model}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
