#!/usr/bin/env python3
"""Compare temporal holdout correlations: pure-real vs backfill-mixed."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"

NEWS_LATEST = ART / "news_observation_v1_latest.jsonl"
NEWS_BALANCED = ART / "news_observation_v1_non_synthetic_date_balanced_latest.jsonl"
TMP_NEWS_PURE = ART / "news_observation_v1_non_synthetic_pure_latest.jsonl"

OUT_PURE = ART / "logos_temporal_holdout_pack_pure_real_latest.json"
OUT_MIXED = ART / "logos_temporal_holdout_pack_mixed_backfill_latest.json"
OUT_COMPARE = ART / "logos_temporal_holdout_compare_backfill_latest.json"


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    for line in path.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s:
            continue
        try:
            obj = json.loads(s)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            rows.append(obj)
    return rows


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def _run(cmd: list[str]) -> None:
    cp = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    if cp.returncode != 0:
        raise RuntimeError(f"Command failed: {' '.join(cmd)}\n{cp.stdout}\n{cp.stderr}")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _corr_ns(doc: dict[str, Any]) -> float | None:
    return (doc.get("summary") or {}).get("corr_candidate_resonance_vs_non_synthetic_hit_rate_eligible_only")


def main() -> int:
    ap = argparse.ArgumentParser(description="Compare pure-real vs backfill temporal holdout correlations.")
    ap.add_argument("--bins", type=int, default=5)
    ap.add_argument("--min-non-synth-per-bin", type=int, default=6)
    ap.add_argument("--balanced-max-per-day", type=int, default=1)
    ap.add_argument("--output-json", type=Path, default=OUT_COMPARE)
    args = ap.parse_args()

    # Build pure-real set by removing backfill rows.
    latest_rows = _load_jsonl(NEWS_LATEST)
    pure_rows = [r for r in latest_rows if "_backfill" not in str(r.get("source_id", ""))]
    _write_jsonl(TMP_NEWS_PURE, pure_rows)

    # Overwrite balanced source using pure rows path via temp copy.
    # We run temporal pack directly by swapping file content.
    _write_jsonl(NEWS_BALANCED, pure_rows)
    _run(
        [
            sys.executable,
            str(ROOT / "scripts" / "run_logos_temporal_holdout_pack_v1.py"),
            "--bins",
            str(args.bins),
            "--min-non-synth-per-bin",
            str(args.min_non_synth_per_bin),
            "--group-by-date",
            "--use-non-synthetic-date-balanced",
            "--output-json",
            str(OUT_PURE),
        ]
    )

    # Rebuild mixed balanced set from latest (includes backfill), then evaluate.
    _run(
        [
            sys.executable,
            str(ROOT / "scripts" / "build_logos_non_synthetic_date_balanced_news_v1.py"),
            "--input-jsonl",
            str(NEWS_LATEST),
            "--output-jsonl",
            str(NEWS_BALANCED),
            "--meta-json",
            str(ART / "news_observation_v1_non_synthetic_date_balanced_meta_latest.json"),
            "--max-per-day",
            str(max(1, int(args.balanced_max_per_day))),
        ]
    )
    _run(
        [
            sys.executable,
            str(ROOT / "scripts" / "run_logos_temporal_holdout_pack_v1.py"),
            "--bins",
            str(args.bins),
            "--min-non-synth-per-bin",
            str(args.min_non_synth_per_bin),
            "--group-by-date",
            "--use-non-synthetic-date-balanced",
            "--output-json",
            str(OUT_MIXED),
        ]
    )

    pure_doc = _load_json(OUT_PURE)
    mixed_doc = _load_json(OUT_MIXED)
    out = {
        "schema": "logos_temporal_holdout_compare_backfill_v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "source_track": "B",
        "research_only": True,
        "auto_bind_to_atrack_forbidden": True,
        "params": {
            "bins": int(args.bins),
            "min_non_synth_per_bin": int(args.min_non_synth_per_bin),
            "balanced_max_per_day": int(max(1, args.balanced_max_per_day)),
        },
        "pure_real": {
            "path": str(OUT_PURE).replace("\\", "/"),
            "eligible_non_synthetic_bin_count": (pure_doc.get("summary") or {}).get("eligible_non_synthetic_bin_count"),
            "corr_candidate_resonance_vs_non_synthetic_hit_rate_eligible_only": _corr_ns(pure_doc),
        },
        "mixed_backfill": {
            "path": str(OUT_MIXED).replace("\\", "/"),
            "eligible_non_synthetic_bin_count": (mixed_doc.get("summary") or {}).get("eligible_non_synthetic_bin_count"),
            "corr_candidate_resonance_vs_non_synthetic_hit_rate_eligible_only": _corr_ns(mixed_doc),
        },
    }
    a = out["pure_real"]["corr_candidate_resonance_vs_non_synthetic_hit_rate_eligible_only"]
    b = out["mixed_backfill"]["corr_candidate_resonance_vs_non_synthetic_hit_rate_eligible_only"]
    out["delta_mixed_minus_pure"] = None if a is None or b is None else round(float(b) - float(a), 6)

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "output_json": str(args.output_json), "delta_mixed_minus_pure": out["delta_mixed_minus_pure"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

