#!/usr/bin/env python3
"""[HYPO] Compression-is-Routing — per-shard reconstruction error → router_confidence (annotation only).

Reads Golden-40 ACTIVE cases; never writes ACTIVE. B-track theory shadow for Phase 3 DR.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ACTIVE = ROOT / "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json"
CODEC_MANIFEST = (
    ROOT
    / "experiments/nextgen_clean_slate_cpu_v1/results/ng40_codec_bench_split_manifest_v1_latest.json"
)
OUT_DEFAULT = ROOT / "reports/compression_routing_confidence_ng40_manifest_v1_latest.json"
SCHEMA = "compression_routing_confidence_ng40_manifest_v1"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _confidence_from_jaccard(j: float) -> dict[str, float]:
    err = round(max(0.0, 1.0 - j), 6)
    return {
        "reconstruction_error": err,
        "router_confidence": round(j, 6),
    }


def build(*, active_path: Path) -> dict[str, Any]:
    active = _load(active_path)
    if not active:
        raise FileNotFoundError(f"missing ACTIVE: {active_path}")

    cases = (active.get("compression_metrics") or {}).get("cases") or []
    per_case: list[dict[str, Any]] = []
    shard_buckets: dict[str, list[float]] = defaultdict(list)
    domain_buckets: dict[str, list[float]] = defaultdict(list)

    for case in cases:
        if not isinstance(case, dict):
            continue
        cid = str(case.get("id") or "")
        j = float(case.get("reconstruction_fidelity_jaccard") or 0.0)
        route = case.get("route") if isinstance(case.get("route"), dict) else {}
        shard = str(route.get("shard_id") or "unknown")
        domain = str(route.get("domain") or "unknown")
        conf = _confidence_from_jaccard(j)
        shard_buckets[shard].append(j)
        domain_buckets[domain].append(j)
        per_case.append(
            {
                "id": cid,
                "shard_id": shard,
                "domain": domain,
                "token_saving_rate": case.get("token_saving_rate"),
                "reconstruction_fidelity_jaccard": j,
                **conf,
                "routing_annotation_only": True,
            }
        )

    shard_stats: dict[str, Any] = {}
    for shard, js in shard_buckets.items():
        mean_j = sum(js) / len(js)
        shard_stats[shard] = {
            "case_count": len(js),
            "mean_jaccard": round(mean_j, 6),
            "mean_reconstruction_error": round(1.0 - mean_j, 6),
            "mean_router_confidence": round(mean_j, 6),
            "min_jaccard": round(min(js), 6),
            "max_jaccard": round(max(js), 6),
        }

    for row in per_case:
        shard = row["shard_id"]
        mean_j = shard_stats.get(shard, {}).get("mean_jaccard") or row["reconstruction_fidelity_jaccard"]
        if mean_j > 0:
            row["shard_relative_confidence"] = round(
                min(1.0, float(row["reconstruction_fidelity_jaccard"]) / float(mean_j)), 6
            )
        else:
            row["shard_relative_confidence"] = row["router_confidence"]

    low_conf = sorted(per_case, key=lambda r: r["router_confidence"])[:5]
    high_err_shards = sorted(
        shard_stats.items(),
        key=lambda kv: kv[1]["mean_reconstruction_error"],
        reverse=True,
    )[:3]

    codec = _load(CODEC_MANIFEST)
    return {
        "schema": SCHEMA,
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "send_gate": "HOLD",
        "track_a_active_write": False,
        "theory_lane": "compression_is_routing",
        "annotation_only": True,
        "source_active": str(active_path.relative_to(ROOT)).replace("\\", "/"),
        "codec_bench_split_pointer": (
            str(CODEC_MANIFEST.relative_to(ROOT)).replace("\\", "/")
            if codec
            else None
        ),
        "frozen_active_headline": {
            "global_token_saving_rate": (active.get("compression_metrics") or {}).get(
                "global_token_saving_rate"
            ),
            "avg_reconstruction_fidelity_jaccard": (active.get("compression_metrics") or {}).get(
                "avg_reconstruction_fidelity_jaccard"
            ),
        },
        "per_shard": shard_stats,
        "per_domain_case_count": {k: len(v) for k, v in domain_buckets.items()},
        "per_case": per_case,
        "routing_insights": {
            "lowest_confidence_cases": [
                {"id": r["id"], "shard_id": r["shard_id"], "router_confidence": r["router_confidence"]}
                for r in low_conf
            ],
            "highest_error_shards": [
                {"shard_id": s, **stats} for s, stats in high_err_shards
            ],
            "interpretation_ko": (
                "reconstruction_error 높음 = router가 해당 shard에서 fidelity risk 신호. "
                "Track A 트리거 아님 — annotation only."
            ),
        },
        "forbidden": [
            "router_confidence as live trade or SEND gate",
            "shard error as product spine KPI",
            "merge with UR topology 99.53%",
        ],
        "reproducible_command": "py scripts/build_compression_routing_confidence_ng40_manifest_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--active", type=Path, default=ACTIVE)
    ap.add_argument("--output", type=Path, default=OUT_DEFAULT)
    args = ap.parse_args()

    doc = build(active_path=args.active if args.active.is_absolute() else ROOT / args.active)
    out = args.output if args.output.is_absolute() else ROOT / args.output
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "wrote": str(out),
                "case_count": len(doc["per_case"]),
                "shard_count": len(doc["per_shard"]),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
