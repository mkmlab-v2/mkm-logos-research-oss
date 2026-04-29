#!/usr/bin/env python3
"""Build unified dashboard JSON for live status + GPU pipeline + shadow score."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
OPS = ROOT / "projects" / "bitcoin-trading" / "memory" / "v2" / "ops"

DEFAULT_LIVE_HEALTH = OPS / "live_trading_health_latest.json"
DEFAULT_LIVE_BLOCKERS = OPS / "live_trading_blockers_latest.json"
DEFAULT_RELEASE_INDEX = ART / "track_a_release_ready_index_v1_latest.json"
DEFAULT_GPU_BACKLOG = ART / "gpu_semantic_expansion_backlog_v1_latest.json"
DEFAULT_GPU_BENCH = ART / "gpu_full_edge_cosine_benchmark_v1_latest.json"
DEFAULT_GPU_CACHE = ART / "gpu_corpus_embedding_refresh_v1_latest.json"
DEFAULT_GPU_GRAPH = ART / "gpu_graph_anomaly_sweep_v1_latest.json"
DEFAULT_GPU_RESWEEP = ART / "gpu_universal_precursor_resweep_v1_latest.json"
DEFAULT_GPU_SHADOW = ART / "gpu_shadow_runtime_score_v1_latest.json"
DEFAULT_OUT = ART / "live_gpu_unified_status_dashboard_v1_latest.json"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return {}
    return obj if isinstance(obj, dict) else {}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    live_health = _load(DEFAULT_LIVE_HEALTH)
    live_blockers = _load(DEFAULT_LIVE_BLOCKERS)
    release_idx = _load(DEFAULT_RELEASE_INDEX)
    gpu_backlog = _load(DEFAULT_GPU_BACKLOG)
    gpu_bench = _load(DEFAULT_GPU_BENCH)
    gpu_cache = _load(DEFAULT_GPU_CACHE)
    gpu_graph = _load(DEFAULT_GPU_GRAPH)
    gpu_resweep = _load(DEFAULT_GPU_RESWEEP)
    gpu_shadow = _load(DEFAULT_GPU_SHADOW)

    work_items = gpu_backlog.get("work_items") if isinstance(gpu_backlog.get("work_items"), list) else []
    completed = sum(1 for w in work_items if str(w.get("status")) == "completed")

    out = {
        "schema": "live_gpu_unified_status_dashboard_v1",
        "generated_at_utc": _now(),
        "live": {
            "health_result": live_health.get("result"),
            "daemon_running": live_health.get("daemon_running"),
            "trading_enabled": live_health.get("trading_enabled"),
            "blockers_result": live_blockers.get("result"),
            "blocker_count": len(live_blockers.get("blockers") or []),
        },
        "release": {
            "ready_count": ((release_idx.get("summary") or {}).get("ready_count")),
            "ready_tracks": ((release_idx.get("summary") or {}).get("ready_tracks")),
        },
        "gpu": {
            "backlog_completed": completed,
            "backlog_total": len(work_items),
            "benchmark_status": gpu_bench.get("status"),
            "cache_rows": ((gpu_cache.get("outputs") or {}).get("rows")),
            "graph_pairs_evaluated": ((gpu_graph.get("summary") or {}).get("pairs_evaluated")),
            "resweep_status": gpu_resweep.get("status"),
            "shadow_runtime_decision": ((gpu_shadow.get("shadow") or {}).get("runtime_decision")),
            "shadow_runtime_score_0_1": ((gpu_shadow.get("shadow") or {}).get("runtime_score_0_1")),
        },
        "constraints": {
            "no_auto_live_binding_for_gpu_shadow": True,
            "human_review_required_for_live_switch": True,
        },
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
