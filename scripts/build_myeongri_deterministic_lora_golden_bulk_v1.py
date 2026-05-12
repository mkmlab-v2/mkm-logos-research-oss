#!/usr/bin/env python3
"""Bulk-generate Pack 0-B golden JSONL (train + locked_eval) with seed + manifest + SHA-256.

Outputs under ``--out-dir`` (default ``data/training/myeongri_deterministic_lora_golden_bulk_v1``):
  - ``train.jsonl`` (>= ``--train-n`` rows)
  - ``locked_eval.jsonl`` (>= ``--locked-eval-n`` rows)
  - ``myeongri_deterministic_lora_golden_bulk_manifest_v1.json`` (counts, seed, file hashes)

Rows match ``myeongri_deterministic_lora_golden_set_v1`` schema; engine path matches
``prep_myeongri_deterministic_lora_golden_v1.build_golden_row_dict``.

JSONL files are gitignored via ``data/training/*.jsonl`` — regenerate on each host as needed.

Example::

  py scripts/build_myeongri_deterministic_lora_golden_bulk_v1.py \\
    --seed 42 --train-n 1000 --locked-eval-n 100 \\
    --dataset-version v1-2026-05-13 --iana-tz Asia/Seoul
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

_WS = Path(__file__).resolve().parent.parent
if str(_WS) not in sys.path:
    sys.path.insert(0, str(_WS))

from scripts.prep_myeongri_deterministic_lora_golden_v1 import build_golden_row_dict  # noqa: E402

_DEFAULT_START = datetime(1955, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
_DEFAULT_END = datetime(2005, 12, 31, 23, 59, 0, tzinfo=timezone.utc)


def _random_utc_instant(rng: random.Random, start: datetime, end: datetime) -> str:
    span = int((end - start).total_seconds())
    if span <= 0:
        raise ValueError("end must be after start")
    off = rng.randint(0, span)
    dt = start + timedelta(seconds=off)
    dt = dt.replace(second=0, microsecond=0)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _try_one_row(
    rng: random.Random,
    seen: set[tuple[str, str, bool]],
    iana_tz: str,
    is_male: bool,
    sample_id: str,
    split: str,
    start: datetime,
    end: datetime,
    max_attempts: int,
) -> dict[str, Any]:
    for _ in range(max_attempts):
        utc = _random_utc_instant(rng, start, end)
        key = (utc, iana_tz, is_male)
        if key in seen:
            continue
        try:
            row = build_golden_row_dict(utc, iana_tz, is_male, sample_id, split)
        except Exception:
            continue
        seen.add(key)
        return row
    raise RuntimeError(
        f"Could not materialize row sample_id={sample_id} split={split} after {max_attempts} attempts"
    )


def _sha256_file(path: Path) -> tuple[str, int]:
    h = hashlib.sha256()
    n = 0
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
            n += len(chunk)
    return h.hexdigest(), n


def build_bulk(
    out_dir: Path,
    seed: int,
    train_n: int,
    locked_n: int,
    iana_tz: str,
    dataset_version: str,
    start: datetime,
    end: datetime,
    max_attempts_per_row: int,
) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    train_path = out_dir / "train.jsonl"
    locked_path = out_dir / "locked_eval.jsonl"
    rng = random.Random(seed)
    seen: set[tuple[str, str, bool]] = set()

    with train_path.open("w", encoding="utf-8") as ft:
        for i in range(1, train_n + 1):
            sid = f"mdl-gs-v1-{i:04d}"
            is_male = bool(rng.randint(0, 1))
            row = _try_one_row(
                rng, seen, iana_tz, is_male, sid, "train", start, end, max_attempts_per_row
            )
            ft.write(json.dumps(row, ensure_ascii=False) + "\n")

    with locked_path.open("w", encoding="utf-8") as fl:
        for j in range(1, locked_n + 1):
            sid = f"mdl-gs-v1-{5000 + j:04d}"
            is_male = bool(rng.randint(0, 1))
            row = _try_one_row(
                rng, seen, iana_tz, is_male, sid, "locked_eval", start, end, max_attempts_per_row
            )
            fl.write(json.dumps(row, ensure_ascii=False) + "\n")

    th, tb = _sha256_file(train_path)
    lh, lb = _sha256_file(locked_path)
    manifest = {
        "schema": "myeongri_deterministic_lora_golden_bulk_manifest_v1",
        "dataset_version": dataset_version,
        "seed": seed,
        "iana_tz": iana_tz,
        "train_rows": train_n,
        "locked_eval_rows": locked_n,
        "utc_range_start": start.isoformat().replace("+00:00", "Z"),
        "utc_range_end": end.isoformat().replace("+00:00", "Z"),
        "files": [
            {"name": "train.jsonl", "sha256": th, "bytes": tb, "lines": train_n},
            {"name": "locked_eval.jsonl", "sha256": lh, "bytes": lb, "lines": locked_n},
        ],
    }
    man_path = out_dir / "myeongri_deterministic_lora_golden_bulk_manifest_v1.json"
    man_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return manifest


def main() -> int:
    ap = argparse.ArgumentParser(description="Bulk golden JSONL for Pack 0-B (seeded).")
    ap.add_argument(
        "--out-dir",
        type=Path,
        default=_WS / "data/training/myeongri_deterministic_lora_golden_bulk_v1",
    )
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--train-n", type=int, default=1000)
    ap.add_argument("--locked-eval-n", type=int, default=100)
    ap.add_argument("--dataset-version", type=str, required=True)
    ap.add_argument("--iana-tz", type=str, default="Asia/Seoul")
    ap.add_argument("--max-attempts-per-row", type=int, default=400)
    args = ap.parse_args()

    manifest = build_bulk(
        args.out_dir.resolve(),
        args.seed,
        args.train_n,
        args.locked_eval_n,
        args.iana_tz,
        args.dataset_version.strip(),
        _DEFAULT_START,
        _DEFAULT_END,
        args.max_attempts_per_row,
    )
    print(json.dumps({"ok": True, "out_dir": str(args.out_dir), "manifest": manifest["files"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
