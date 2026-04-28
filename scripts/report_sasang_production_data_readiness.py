#!/usr/bin/env python3
"""Report production strict data readiness from on-disk authoritative inputs."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"

DEFAULT_GT = ROOT / "data" / "constitution" / "korean_cohort" / "gt_cohort.real.latest.jsonl"
DEFAULT_PRED_DIR = ROOT / "reports" / "constitution" / "btrack_pilot"
DEFAULT_ALIGNED = ROOT / "reports" / "constitution" / "btrack_pilot" / "predictions.real.aligned.latest.jsonl"
DEFAULT_OUT = ART / "sasang_production_data_readiness_latest.json"
PARENTS = {"TY", "SY", "TE", "SE"}


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


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


def _gt_valid_ids(path: Path) -> set[str]:
    rows = _read_jsonl(path)
    out: set[str] = set()
    for r in rows:
        sid = str(r.get("sample_id") or "").strip()
        ep = str(r.get("expected_parent") or "").strip().upper()
        if sid and ep in PARENTS:
            out.add(sid)
    return out


def _pred_valid_ids(path: Path) -> set[str]:
    rows = _read_jsonl(path)
    out: set[str] = set()
    for r in rows:
        sid = str(r.get("sample_id") or "").strip()
        pp = str(r.get("predicted_parent") or "").strip().upper()
        c = r.get("confidence")
        ok_c = isinstance(c, (int, float)) and 0.0 <= float(c) <= 1.0
        if sid and pp in PARENTS and ok_c:
            out.add(sid)
    return out


def _is_shadow_or_synthetic(path: Path) -> bool:
    s = path.as_posix().lower()
    bad_tokens = ("synthetic", "proxy", "template", "blind_replay", "shadow")
    return any(t in s for t in bad_tokens)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--gt", type=Path, default=DEFAULT_GT)
    ap.add_argument("--pred-dir", type=Path, default=DEFAULT_PRED_DIR)
    ap.add_argument("--aligned-pred", type=Path, default=DEFAULT_ALIGNED)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    if not args.gt.is_file():
        print(f"ERROR: missing GT file: {args.gt}")
        return 2
    if not args.pred_dir.is_dir():
        print(f"ERROR: missing prediction directory: {args.pred_dir}")
        return 2

    gt_ids = _gt_valid_ids(args.gt)
    aligned_rows = 0
    aligned_pairs = 0
    if args.aligned_pred.is_file():
        aligned_pred_ids = _pred_valid_ids(args.aligned_pred)
        aligned_rows = len(aligned_pred_ids)
        aligned_pairs = len(gt_ids & aligned_pred_ids)
    candidates: list[dict[str, Any]] = []
    for pred in sorted(args.pred_dir.glob("*predictions*.jsonl")):
        try:
            pred_ids = _pred_valid_ids(pred)
        except Exception:
            continue
        paired = len(gt_ids & pred_ids)
        candidates.append(
            {
                "path": str(pred.resolve()),
                "valid_pred_ids": len(pred_ids),
                "paired_ids_with_gt": paired,
                "shadow_or_synthetic": _is_shadow_or_synthetic(pred),
            }
        )

    authoritative = [c for c in candidates if not c["shadow_or_synthetic"]]
    best = max(authoritative, key=lambda x: x["paired_ids_with_gt"], default=None)
    max_pairable = int(best["paired_ids_with_gt"]) if best else 0
    ready_for_strict = max_pairable >= 128

    report = {
        "schema": "sasang_production_data_readiness_v1",
        "generated_at_utc": _now(),
        "gt_path": str(args.gt.resolve()),
        "gt_valid_ids": len(gt_ids),
        "prediction_candidates": candidates,
        "best_authoritative_candidate": best,
        "max_pairable_rows_authoritative": max_pairable,
        "canonical_aligned_prediction_path": str(args.aligned_pred.resolve()) if args.aligned_pred.is_file() else None,
        "canonical_aligned_rows": aligned_rows,
        "canonical_aligned_pairs_with_gt": aligned_pairs,
        "strict_min_paired_rows_required": 128,
        "ready_for_production_strict": ready_for_strict,
        "root_cause": "insufficient_authoritative_pairable_rows" if not ready_for_strict else "NONE",
        "policy": {
            "exclude_shadow_or_synthetic_for_authoritative_strict": True,
            "track_b_to_a_autobind_forbidden": True,
        },
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.out}")
    print(f"max_pairable_rows_authoritative={max_pairable}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
