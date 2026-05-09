#!/usr/bin/env python3
"""Emit train/holdout benchmark manifests from base manifest + holdout split report."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_BASE = ROOT / "docs/final/artifacts/general_compression_benchmark_manifest_v1.json"
DEFAULT_REPORT = ROOT / "docs/final/artifacts/general_compression_holdout_split_report_v1.json"
OUT_TRAIN = ROOT / "docs/final/artifacts/general_compression_benchmark_manifest_train_v1.json"
OUT_HOLDOUT = ROOT / "docs/final/artifacts/general_compression_benchmark_manifest_holdout_v1.json"


def _norm_rel(p: str) -> str:
    return str(Path(p)).replace("\\", "/")


def _deep_copy(doc: dict[str, Any]) -> dict[str, Any]:
    return json.loads(json.dumps(doc))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--base", type=Path, default=DEFAULT_BASE)
    ap.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    ap.add_argument("--train-out", type=Path, default=OUT_TRAIN)
    ap.add_argument("--holdout-out", type=Path, default=OUT_HOLDOUT)
    args = ap.parse_args()

    if not args.base.is_file():
        print(f"FAIL: missing base manifest {args.base}", file=sys.stderr)
        return 2
    if not args.report.is_file():
        print(f"FAIL: missing split report {args.report} (run split_general_compression_holdout_v1.py)", file=sys.stderr)
        return 2

    base = json.loads(args.base.read_text(encoding="utf-8"))
    report = json.loads(args.report.read_text(encoding="utf-8"))
    if report.get("schema") != "general_compression_holdout_split_report_v1":
        print("FAIL: report schema mismatch", file=sys.stderr)
        return 2

    by_id: dict[str, dict[str, Any]] = {}
    for row in report.get("datasets") or []:
        if isinstance(row, dict) and row.get("dataset_id"):
            by_id[str(row["dataset_id"])] = row

    split_key = str(report.get("split_key", ""))

    def patch(role: str) -> dict[str, Any]:
        doc = _deep_copy(base)
        corp = doc.setdefault("corpus", {})
        ds_list = corp.setdefault("datasets", [])
        for ds in ds_list:
            if not isinstance(ds, dict):
                continue
            did = str(ds.get("dataset_id", ""))
            row = by_id.get(did)
            if not row:
                print(f"WARN: no split row for dataset_id={did}", file=sys.stderr)
                continue
            path_key = "train_path" if role == "train" else "holdout_path"
            cnt_key = "train_count" if role == "train" else "holdout_count"
            path_val = row.get(path_key)
            cnt_val = row.get(cnt_key)
            if not isinstance(path_val, str):
                raise ValueError(f"missing {path_key} for dataset_id={did}")
            ds["source_path"] = _norm_rel(path_val)
            if isinstance(cnt_val, int):
                ds["record_count"] = cnt_val
        doc["split_role"] = role
        doc["split_key"] = split_key
        notes = list(doc.get("notes") or [])
        notes.append(
            f"Derived manifest ({role}) from split report; tuning vs reporting should use train vs holdout respectively."
        )
        doc["notes"] = notes
        return doc

    try:
        train_doc = patch("train")
        hold_doc = patch("holdout")
    except ValueError as e:
        print(f"FAIL: {e}", file=sys.stderr)
        return 2

    def rel_out(p: Path) -> str:
        try:
            return str(p.resolve().relative_to(ROOT))
        except ValueError:
            return str(p.resolve())

    for out_path, doc in ((args.train_out, train_doc), (args.holdout_out, hold_doc)):
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(
        json.dumps(
            {
                "ok": True,
                "train_out": rel_out(args.train_out),
                "holdout_out": rel_out(args.holdout_out),
                "split_key": split_key,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
