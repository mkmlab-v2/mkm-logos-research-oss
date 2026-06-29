#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Read-only triage: tier_a real Swarm PIT JSONL readiness for Stage 1 re-eval.

Counts schema-valid rows with non-synthetic engine_name and seed_cutoff_time.
Exit 0 always unless --strict (then 1 when tier_a gate not met).
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "reports/btrack_swarm_tier_a_prereqs_v1_latest.json"
SYNTHETIC_ENGINES = frozenset(
    {"synthetic_date_hash_v1", "manual_dummy", "hypo_smoke", "date_hash_only"}
)
DEFAULT_CANDIDATES = (
    ROOT / "data/btrack/swarm_sentiment_real_pit_v1.jsonl",
    ROOT / "memory/v2/btrack/raw_feeds/swarm_sentiment_daily_v1.jsonl",
    ROOT / "docs/final/dummy_swarm_score.jsonl",
    ROOT / "data/btrack/swarm_sentiment_synthetic_krx_hypo_v1.jsonl",
    ROOT / "data/btrack/swarm_sentiment_daily_hypo_v1.jsonl",
)


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rel(p: Path) -> str:
    try:
        return str(p.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(p).replace("\\", "/")


def _parse_date_from_row(row: dict[str, Any]) -> date | None:
    for key in ("timestamp_utc", "seed_cutoff_time"):
        raw = row.get(key)
        if not isinstance(raw, str) or len(raw) < 10:
            continue
        try:
            return date.fromisoformat(raw[:10])
        except ValueError:
            continue
    return None


def _classify_jsonl(path: Path, min_krx_weekdays: int) -> dict[str, Any]:
    if not path.is_file():
        return {
            "path": _rel(path),
            "exists": False,
            "tier": "missing",
            "krx_weekday_rows": 0,
            "real_pit_rows": 0,
            "tier_a_ready": False,
        }

    krx = 0
    real = 0
    engines: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(row, dict):
            continue
        meta = row.get("simulation_meta") if isinstance(row.get("simulation_meta"), dict) else {}
        engine = str(meta.get("engine_name") or "")
        if engine:
            engines.add(engine)
        d = _parse_date_from_row(row)
        if d is None:
            continue
        if d.weekday() < 5:
            krx += 1
        if engine and engine not in SYNTHETIC_ENGINES and row.get("seed_cutoff_time"):
            real += 1

    tier = "tier_b_synthetic"
    if real >= min_krx_weekdays:
        tier = "tier_a_real_pit"
    elif real > 0 and not any(e in SYNTHETIC_ENGINES for e in engines):
        tier = "tier_a_partial"
    elif path.name.endswith("synthetic") or any(e in SYNTHETIC_ENGINES for e in engines):
        tier = "tier_b_synthetic"

    return {
        "path": _rel(path),
        "exists": True,
        "tier": tier,
        "krx_weekday_rows": krx,
        "real_pit_rows": real,
        "engine_names": sorted(engines),
        "tier_a_ready": real >= min_krx_weekdays,
    }


def build_report(
    *,
    candidates: list[Path],
    min_krx_weekdays: int,
    extra_paths: list[Path] | None = None,
) -> dict[str, Any]:
    paths = list(candidates)
    if extra_paths:
        for p in extra_paths:
            if p not in paths:
                paths.append(p)

    files = [_classify_jsonl(p, min_krx_weekdays) for p in paths]
    tier_a_files = [f for f in files if f.get("tier_a_ready")]
    best_real = max((f.get("real_pit_rows") or 0 for f in files), default=0)

    return {
        "schema": "btrack_swarm_tier_a_prereqs_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "min_krx_weekday_rows_tier_a": min_krx_weekdays,
        "tier_a_ready": bool(tier_a_files),
        "best_real_pit_rows": best_real,
        "recommended_next": (
            "run_btrack_session_panel_swarm_corr_chain_v1.py with tier_a JSONL"
            if tier_a_files
            else "py scripts/build_swarm_sentiment_from_atproto_v1.py then collect more ATProto raw"
        ),
        "candidate_files": files,
        "scripts": {
            "chain": "scripts/run_btrack_session_panel_swarm_corr_chain_v1.py",
            "validate": "scripts/validate_swarm_sentiment_dummy.py",
            "atproto_ingest": "scripts/build_swarm_sentiment_from_atproto_v1.py",
            "stage1_bundle": "scripts/run_btrack_swarm_sasang_stage1_bundle_v1.py",
            "synthetic_volume_only": "scripts/build_swarm_sentiment_synthetic_krx_jsonl_v1.py",
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--min-krx-weekdays", type=int, default=30)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--stdout-only", action="store_true")
    ap.add_argument("--strict", action="store_true", help="Exit 1 if tier_a not ready")
    ap.add_argument("--jsonl", type=Path, action="append", default=[], help="Extra candidate JSONL")
    args = ap.parse_args()

    extra = [p.resolve() for p in args.jsonl]
    payload = build_report(
        candidates=[p.resolve() for p in DEFAULT_CANDIDATES],
        min_krx_weekdays=max(1, args.min_krx_weekdays),
        extra_paths=extra,
    )

    if not args.stdout_only:
        args.out_json.parent.mkdir(parents=True, exist_ok=True)
        args.out_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(str(args.out_json.resolve()))

    print(
        f"tier_a_ready={payload['tier_a_ready']} best_real_pit_rows={payload['best_real_pit_rows']}"
    )
    if args.strict and not payload["tier_a_ready"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
