#!/usr/bin/env python3
"""Per-lane domain router shard distribution for Universal Matrix cases (B-track)."""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

MATRIX = ROOT / "docs/final/artifacts/UNIVERSAL_COMPRESSION_BENCH_MATRIX_INPUT_V1.json"
DEFAULT_SHARDS = ROOT / "codebook" / "shards"
SHARP_SHARDS = ROOT / "codebook" / "shards_btrack_router_sharp_v1"
SHARP_V2_SHARDS = ROOT / "codebook" / "shards_btrack_router_sharp_v2"
OUT = ROOT / "reports/constitution/btrack_pilot/comp_universal_matrix_routing_diagnosis_latest.json"

STRESS_LANES_DEFAULT = (
    "en_tech_spec_stress_v1",
    "server_log_stress_v1",
    "finance_alnum_dense_v1",
)


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_tiebreak(shards_root: Path) -> tuple[str, ...]:
    meta = shards_root / "_router_sharp_v1_meta.json"
    if meta.is_file():
        doc = json.loads(meta.read_text(encoding="utf-8-sig"))
        return tuple(str(x) for x in doc.get("tiebreak_priority") or ())
    return ()


def _route_stats(cases: list[dict[str, Any]], *, shards_root: Path) -> dict[str, Any]:
    from scripts.core.domain_router import DomainSpecificRouter

    tiebreak = _load_tiebreak(shards_root)
    router = DomainSpecificRouter(shards_root, tiebreak_priority=tiebreak or None)
    shard_counts: Counter[str] = Counter()
    score_zero = 0
    samples: list[dict[str, str]] = []
    for c in cases:
        raw = str(c.get("raw_text") or "")
        route = router.route(raw)
        shard_counts[route.shard_id] += 1
        words = {w.lower() for w in __import__("re").findall(r"[A-Za-z0-9_가-힣]+", raw)}
        best_score = 0
        for shard in router._shards:  # noqa: SLF001 — research diagnostic only
            keys = {str(k).lower() for k in shard.get("routing_keywords", [])}
            best_score = max(best_score, sum(1 for k in keys if k in words))
        if best_score <= 0:
            score_zero += 1
        if len(samples) < 5:
            samples.append(
                {
                    "case_id": str(c.get("id") or ""),
                    "shard_id": route.shard_id,
                    "domain": route.domain,
                }
            )
    total = len(cases) or 1
    return {
        "case_count": len(cases),
        "shard_distribution": dict(sorted(shard_counts.items(), key=lambda x: (-x[1], x[0]))),
        "zero_keyword_score_rate": round(score_zero / total, 4),
        "zero_keyword_score_count": score_zero,
        "sample_routes": samples,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--matrix-input", type=Path, default=MATRIX)
    ap.add_argument("--out-json", type=Path, default=OUT)
    ap.add_argument("--lane-id", action="append", default=[], help="Repeatable; default stress trio.")
    ap.add_argument("--compare-sharp", action="store_true", help="Also diagnose shards_btrack_router_sharp_v1.")
    ap.add_argument("--compare-sharp-v2", action="store_true", help="Also diagnose shards_btrack_router_sharp_v2.")
    args = ap.parse_args()

    doc = json.loads(args.matrix_input.read_text(encoding="utf-8-sig"))
    cases = list(doc.get("compression_cases") or [])
    lane_ids = list(args.lane_id or STRESS_LANES_DEFAULT)

    by_lane: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for c in cases:
        lid = str(c.get("lane_id") or "")
        if lid in lane_ids:
            by_lane[lid].append(c)

    profiles: dict[str, Any] = {
        "default_shards": {
            "shards_root": str(DEFAULT_SHARDS.relative_to(ROOT)).replace("\\", "/"),
            "lanes": {lid: _route_stats(by_lane.get(lid, []), shards_root=DEFAULT_SHARDS) for lid in lane_ids},
        }
    }
    if args.compare_sharp and SHARP_SHARDS.is_dir():
        profiles["router_sharp_v1"] = {
            "shards_root": str(SHARP_SHARDS.relative_to(ROOT)).replace("\\", "/"),
            "lanes": {lid: _route_stats(by_lane.get(lid, []), shards_root=SHARP_SHARDS) for lid in lane_ids},
        }
    if args.compare_sharp_v2 and SHARP_V2_SHARDS.is_dir():
        profiles["router_sharp_v2"] = {
            "shards_root": str(SHARP_V2_SHARDS.relative_to(ROOT)).replace("\\", "/"),
            "lanes": {lid: _route_stats(by_lane.get(lid, []), shards_root=SHARP_V2_SHARDS) for lid in lane_ids},
        }

    out_doc = {
        "schema": "comp_universal_matrix_routing_diagnosis_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "matrix_input": str(args.matrix_input.relative_to(ROOT)).replace("\\", "/"),
        "lane_ids": lane_ids,
        "profiles": profiles,
    }

    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(out_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    try:
        wrote = str(args.out_json.resolve().relative_to(ROOT.resolve())).replace("\\", "/")
    except ValueError:
        wrote = str(args.out_json.resolve())
    print(
        json.dumps(
            {
                "wrote": wrote,
                "lane_ids": lane_ids,
                "profiles": list(profiles.keys()),
            },
            ensure_ascii=False,
        )
    )
    return 0 if any(by_lane.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
