#!/usr/bin/env python3
"""Extract MKM-UR-Bench-5K holdout split from massive 5K fixture [HYPO · HOLD]."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "tests/fixtures/nsm_41k_lexicon_crosswalk_5000_v1.json"
OUT_FIXTURE = ROOT / "tests/fixtures/universal_root_bench_5k_holdout_v1.json"
OUT_REPORT = ROOT / "reports/universal_root_bench_5k_holdout_fixture_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def build_holdout(*, source_path: Path, split: str = "holdout") -> dict[str, Any]:
    doc = json.loads(source_path.read_text(encoding="utf-8-sig"))
    all_samples = doc.get("samples") or []
    holdout = [r for r in all_samples if isinstance(r, dict) and str(r.get("split") or "") == split]
    train_count = sum(1 for r in all_samples if str(r.get("split") or "") == "train")
    return {
        "schema": "universal_root_bench_5k_holdout_v1",
        "version": "1.0.0",
        "bench_name": "MKM-UR-Bench-5K",
        "description": f"Holdout split ({split}) from nsm_41k_lexicon_crosswalk_5000_v1 — B0/B3 dual-plane eval.",
        "research_only": True,
        "send_gate": "HOLD",
        "source_fixture": str(source_path.relative_to(ROOT)).replace("\\", "/"),
        "source_pair_count": int(doc.get("pair_count") or len(all_samples)),
        "split": split,
        "pair_count": len(holdout),
        "train_pair_count": train_count,
        "holdout_pair_count": len(holdout),
        "generation_seed": (doc.get("generation") or {}).get("seed"),
        "samples": holdout,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--source", type=Path, default=SOURCE)
    ap.add_argument("--split", default="holdout")
    ap.add_argument("--out", type=Path, default=OUT_FIXTURE)
    ap.add_argument("--report", type=Path, default=OUT_REPORT)
    ap.add_argument("--min-pairs", type=int, default=500)
    args = ap.parse_args()

    if not args.source.is_file():
        print(json.dumps({"ok": False, "error": "missing_source_fixture", "path": str(args.source)}))
        return 2

    holdout_doc = build_holdout(source_path=args.source, split=args.split)
    if holdout_doc["pair_count"] < args.min_pairs:
        print(
            json.dumps(
                {
                    "ok": False,
                    "error": "holdout_below_min",
                    "pair_count": holdout_doc["pair_count"],
                    "min_pairs": args.min_pairs,
                }
            )
        )
        return 1

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(holdout_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    report = {
        "schema": "universal_root_bench_5k_holdout_fixture_report_v1",
        "generated_at_utc": _utc(),
        "ok": True,
        "bench_name": "MKM-UR-Bench-5K",
        "holdout_fixture": str(args.out.relative_to(ROOT)).replace("\\", "/"),
        "pair_count": holdout_doc["pair_count"],
        "source_sha256": _sha256(args.source),
        "reproduce": "py scripts/build_universal_root_bench_5k_holdout_fixture_v1.py",
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(
        json.dumps(
            {"ok": True, "pair_count": holdout_doc["pair_count"], "out": str(args.out), "report": str(args.report)},
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
