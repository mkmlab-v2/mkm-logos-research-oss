#!/usr/bin/env python3
"""Deterministic train/holdout JSONL split for general-rail corpus (manifest-driven)."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MANIFEST = ROOT / "docs/final/artifacts/general_compression_benchmark_manifest_v1.json"
DEFAULT_REPORT = ROOT / "docs/final/artifacts/general_compression_holdout_split_report_v1.json"


def _rel_repo(p: Path) -> str:
    try:
        return str(p.resolve().relative_to(ROOT))
    except ValueError:
        return str(p.resolve())


def _iter_jsonl_lines(path: Path) -> list[str]:
    lines: list[str] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            s = line.strip()
            if s:
                lines.append(s)
    return lines


def _assign_holdout(domain: str, line_index: int, seed: int, ratio: float) -> bool:
    payload = f"{seed}:{domain}:{line_index}".encode("utf-8")
    digest = hashlib.sha256(payload).digest()
    val = int.from_bytes(digest[:4], "big") / float(2**32)
    return val < ratio


def main() -> int:
    ap = argparse.ArgumentParser(description="Split manifest JSONL corpus into train/holdout shards.")
    ap.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    ap.add_argument(
        "--out-root",
        type=Path,
        default=None,
        help="Root directory for rXX_sYY/train|holdout (default: data/general_compression/splits_v1/rXX_sYY)",
    )
    ap.add_argument("--holdout-ratio", type=float, default=0.2)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = ap.parse_args()

    if not (0.0 < args.holdout_ratio < 1.0):
        print("holdout-ratio must be between 0 and 1")
        return 2

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    datasets = (manifest.get("corpus") or {}).get("datasets") or []

    pct = int(round(args.holdout_ratio * 100))
    split_key = f"r{pct}_s{args.seed}"
    out_root = args.out_root
    if out_root is None:
        out_root = ROOT / "data" / "general_compression" / "splits_v1" / split_key

    train_dir = out_root / "train"
    hold_dir = out_root / "holdout"
    train_dir.mkdir(parents=True, exist_ok=True)
    hold_dir.mkdir(parents=True, exist_ok=True)

    rows_out: list[dict[str, Any]] = []
    total_train = total_hold = 0

    for ds in datasets:
        source = ds.get("source_path")
        domain = str(ds.get("domain", "unknown"))
        if not isinstance(source, str):
            continue
        src = (ROOT / source).resolve()
        if not src.is_file():
            print(json.dumps({"warn": "missing_source", "path": str(src)}, ensure_ascii=False))
            continue

        raw_lines = _iter_jsonl_lines(src)
        stem = src.name
        train_lines: list[str] = []
        hold_lines: list[str] = []

        for i, line in enumerate(raw_lines):
            if _assign_holdout(domain, i, args.seed, args.holdout_ratio):
                hold_lines.append(line)
            else:
                train_lines.append(line)

        (train_dir / stem).write_text("\n".join(train_lines) + ("\n" if train_lines else ""), encoding="utf-8")
        (hold_dir / stem).write_text("\n".join(hold_lines) + ("\n" if hold_lines else ""), encoding="utf-8")

        total_train += len(train_lines)
        total_hold += len(hold_lines)
        rows_out.append(
            {
                "domain": domain,
                "dataset_id": ds.get("dataset_id"),
                "filename": stem,
                "train_count": len(train_lines),
                "holdout_count": len(hold_lines),
                "train_path": _rel_repo(train_dir / stem),
                "holdout_path": _rel_repo(hold_dir / stem),
            }
        )

    report = {
        "schema": "general_compression_holdout_split_report_v1",
        "split_key": split_key,
        "seed": args.seed,
        "holdout_ratio": args.holdout_ratio,
        "out_root": _rel_repo(out_root),
        "manifest": _rel_repo(args.manifest),
        "totals": {"train": total_train, "holdout": total_hold},
        "datasets": rows_out,
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"ok": True, "report": str(args.report.resolve()), "split_key": split_key}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
