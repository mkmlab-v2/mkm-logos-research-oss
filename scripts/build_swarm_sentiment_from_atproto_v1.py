#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Normalize ATProto raw JSONL → Swarm sentiment daily JSONL (tier_a path).

Reads ``projects/bitcoin-trading/memory/v2/btrack/raw_feeds/atproto/*_atproto_sentiment_raw.jsonl``,
aggregates per calendar day, writes schema-valid rows to ``data/btrack/swarm_sentiment_real_pit_v1.jsonl``.

B-track only · [HYPO] · no KPI/trinity merge · PIT cutoff = session day 09:00 UTC (KRX open proxy).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ATPROTO_DIR = (
    ROOT / "projects" / "bitcoin-trading" / "memory" / "v2" / "btrack" / "raw_feeds" / "atproto"
)
DEFAULT_OUT = ROOT / "data" / "btrack" / "swarm_sentiment_real_pit_v1.jsonl"
DEFAULT_SCHEMA = ROOT / "docs" / "final" / "SWARM_SENTIMENT_METRIC_SCHEMA_DRAFT.json"

PANIC_TERMS = ("panic", "fear", "crash", "plunge", "dump", "sell pressure", "투매", "공포", "급락")
FOMO_TERMS = ("fomo", "euphoria", "surge", "all-time high", "bullish", "매수", "급등", "상승")
NOISE_TERMS = ("onlyfans", "cammodels", "live sex", "#nsfw", "fucky.mom")


def _iter_jsonl(path: Path) -> Iterable[dict]:
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(row, dict):
            yield row


def _file_day(path: Path) -> str | None:
    m = re.match(r"(\d{8})_atproto_sentiment_raw\.jsonl$", path.name)
    return m.group(1) if m else None


def _score_text(text: str) -> str:
    t = text.lower()
    has_panic = any(k in t for k in PANIC_TERMS)
    has_fomo = any(k in t for k in FOMO_TERMS)
    if has_panic and not has_fomo:
        return "panic"
    if has_fomo and not has_panic:
        return "fomo"
    return "neutral"


def _is_noise(text: str) -> bool:
    t = text.lower()
    if any(k in t for k in NOISE_TERMS):
        return True
    if t.count("#bitcoin") >= 3 and len(t) < 120:
        return True
    return False


def _pit_cutoff_iso(day_yyyymmdd: str, hour: int, minute: int) -> str:
    return f"{day_yyyymmdd[:4]}-{day_yyyymmdd[4:6]}-{day_yyyymmdd[6:8]}T{hour:02d}:{minute:02d}:00Z"


def build_rows(
    paths: list[Path],
    *,
    pit_hour: int = 9,
    pit_minute: int = 0,
) -> list[dict]:
    rows: list[dict] = []
    for p in sorted(paths):
        day = _file_day(p)
        if not day:
            continue
        panic = fomo = neutral = total = 0
        for item in _iter_jsonl(p):
            text = str(item.get("text", "")).strip()
            if not text or _is_noise(text):
                continue
            cls = _score_text(text)
            total += 1
            if cls == "panic":
                panic += 1
            elif cls == "fomo":
                fomo += 1
            else:
                neutral += 1
        if total == 0:
            continue
        panic_ratio = panic / total
        fomo_index = fomo / total
        consensus_strength = max(panic_ratio, fomo_index, neutral / total)
        iso_day = f"{day[:4]}-{day[4:6]}-{day[6:8]}"
        rows.append(
            {
                "timestamp_utc": f"{iso_day}T00:00:00Z",
                "seed_event_id": f"atproto_day_{day}",
                "seed_cutoff_time": _pit_cutoff_iso(day, pit_hour, pit_minute),
                "metrics": {
                    "panic_ratio": round(panic_ratio, 6),
                    "fomo_index": round(fomo_index, 6),
                    "consensus_strength": round(consensus_strength, 6),
                },
                "simulation_meta": {
                    "engine_name": "atproto_operational_heuristic_v1",
                    "agent_count": total,
                    "prompt_hash": "sha256:operational-atproto-v1",
                },
            }
        )
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--atproto-dir", type=Path, default=DEFAULT_ATPROTO_DIR)
    ap.add_argument("--out-jsonl", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--pit-hour", type=int, default=9)
    ap.add_argument("--pit-minute", type=int, default=0)
    ap.add_argument("--validate", action="store_true", default=True)
    ap.add_argument("--no-validate", action="store_false", dest="validate")
    args = ap.parse_args()

    if not args.atproto_dir.is_dir():
        print(f"atproto dir missing: {args.atproto_dir}", file=sys.stderr)
        return 2

    paths = sorted(args.atproto_dir.glob("*_atproto_sentiment_raw.jsonl"))
    rows = build_rows(paths, pit_hour=args.pit_hour, pit_minute=args.pit_minute)
    args.out_jsonl.parent.mkdir(parents=True, exist_ok=True)
    with args.out_jsonl.open("w", encoding="utf-8") as fp:
        for row in rows:
            fp.write(json.dumps(row, ensure_ascii=False) + "\n")

    if args.validate and rows:
        try:
            from jsonschema import Draft7Validator
        except ImportError:
            print("jsonschema missing; skip validate", file=sys.stderr)
        else:
            schema = json.loads(DEFAULT_SCHEMA.read_text(encoding="utf-8"))
            v = Draft7Validator(schema)
            for i, row in enumerate(rows, start=1):
                errs = list(v.iter_errors(row))
                if errs:
                    print(f"line {i}: {errs[0].message}", file=sys.stderr)
                    return 1

    meta = {
        "schema": "swarm_sentiment_from_atproto_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "tier": "tier_a_real_pit",
        "n_rows": len(rows),
        "n_source_files": len(paths),
        "out_jsonl": str(args.out_jsonl.resolve()),
        "atproto_dir": str(args.atproto_dir.resolve()),
    }
    meta_path = args.out_jsonl.with_suffix(".meta.json")
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE n={len(rows)} jsonl={args.out_jsonl.resolve()} meta={meta_path.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
