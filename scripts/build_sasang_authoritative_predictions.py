#!/usr/bin/env python3
"""Build canonical authoritative Sasang predictions aligned to GT sample IDs.

Purpose:
- Enforce sample_id alignment against authoritative GT.
- Select best-confidence prediction per sample across non-shadow sources.
- Emit canonical predictions.real.aligned.latest.jsonl for strict evaluation.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PARENTS = {"TY", "SY", "TE", "SE"}

DEFAULT_GT = ROOT / "data" / "constitution" / "korean_cohort" / "gt_cohort.real.latest.jsonl"
DEFAULT_PRED_DIR = ROOT / "reports" / "constitution" / "btrack_pilot"
DEFAULT_OUT = ROOT / "reports" / "constitution" / "btrack_pilot" / "predictions.real.aligned.latest.jsonl"
DEFAULT_REPORT = ROOT / "docs" / "final" / "artifacts" / "sasang_authoritative_prediction_alignment_latest.json"


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        obj = json.loads(line)
        if isinstance(obj, dict):
            rows.append(obj)
    return rows


def _is_non_shadow_source(path: Path) -> bool:
    s = path.as_posix().lower()
    blocked = ("synthetic", "proxy", "template", "blind_replay", "shadow")
    return not any(t in s for t in blocked)


def _valid_gt_ids(path: Path) -> set[str]:
    ids: set[str] = set()
    for row in _read_jsonl(path):
        sid = str(row.get("sample_id") or "").strip()
        ep = str(row.get("expected_parent") or "").strip().upper()
        if sid and ep in PARENTS:
            ids.add(sid)
    return ids


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--gt", type=Path, default=DEFAULT_GT)
    ap.add_argument("--pred-dir", type=Path, default=DEFAULT_PRED_DIR)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = ap.parse_args()

    if not args.gt.is_file():
        print(f"ERROR: missing GT file: {args.gt}")
        return 2
    if not args.pred_dir.is_dir():
        print(f"ERROR: missing prediction directory: {args.pred_dir}")
        return 2

    gt_ids = _valid_gt_ids(args.gt)
    if not gt_ids:
        print("ERROR: no valid GT IDs found")
        return 3

    best_by_sid: dict[str, dict[str, Any]] = {}
    source_counts: dict[str, int] = {}
    scanned = 0

    for pred_path in sorted(args.pred_dir.glob("*predictions*.jsonl")):
        if not _is_non_shadow_source(pred_path):
            continue
        scanned += 1
        rows = _read_jsonl(pred_path)
        accepted = 0
        for row in rows:
            sid = str(row.get("sample_id") or "").strip()
            parent = str(row.get("predicted_parent") or "").strip().upper()
            conf_raw = row.get("confidence")
            if not sid or sid not in gt_ids or parent not in PARENTS:
                continue
            if not isinstance(conf_raw, (int, float)):
                continue
            conf = float(conf_raw)
            if conf < 0.0 or conf > 1.0:
                continue

            current = best_by_sid.get(sid)
            if current is None or conf > float(current["confidence"]):
                best_by_sid[sid] = {
                    "sample_id": sid,
                    "predicted_parent": parent,
                    "confidence": round(conf, 6),
                    "prediction_source": pred_path.name,
                }
            accepted += 1
        source_counts[pred_path.name] = accepted

    out_rows = [best_by_sid[sid] for sid in sorted(best_by_sid)]
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in out_rows) + ("\n" if out_rows else ""), encoding="utf-8")

    report = {
        "schema": "sasang_authoritative_prediction_alignment_v1",
        "gt_path": str(args.gt.resolve()),
        "pred_dir": str(args.pred_dir.resolve()),
        "scanned_sources": scanned,
        "gt_valid_ids": len(gt_ids),
        "aligned_prediction_rows": len(out_rows),
        "coverage_ratio": (len(out_rows) / len(gt_ids)) if gt_ids else 0.0,
        "source_hit_counts": source_counts,
        "output_path": str(args.out.resolve()),
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"WROTE: {args.out}")
    print(f"WROTE: {args.report}")
    print(f"aligned_prediction_rows={len(out_rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
