#!/usr/bin/env python3
"""Build GPU semantic expansion backlog artifact (B-track, research-only)."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
DEFAULT_OUT = ART / "gpu_semantic_expansion_backlog_v1_latest.json"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    payload = {
        "schema": "gpu_semantic_expansion_backlog_v1",
        "generated_at_utc": _now(),
        "research_only": True,
        "fact_lock_mode": "numeric_scan_only",
        "principles": {
            "no_deterministic_narrative_generation": True,
            "no_auto_live_binding": True,
            "use_gpu_for_scan_and_measurement_only": True,
        },
        "work_items": [
            {
                "id": "gpu-01",
                "title": "3M+ edge full cosine scan benchmark",
                "objective": "Measure end-to-end speedup and reproducibility on full edge set.",
                "outputs": [
                    "docs/final/artifacts/gpu_full_edge_cosine_benchmark_v1_latest.json"
                ],
                "status": "planned",
            },
            {
                "id": "gpu-02",
                "title": "Expanded corpus embedding cache refresh",
                "objective": "Rebuild canonical+manuscript embedding caches via GPU batch encoding.",
                "outputs": [
                    "docs/final/artifacts/gpu_corpus_embedding_refresh_v1_latest.json"
                ],
                "status": "planned",
            },
            {
                "id": "gpu-03",
                "title": "Graph anomaly metric sweep",
                "objective": "Compute structural drift metrics (bridge density / cluster stress) at scale.",
                "outputs": [
                    "docs/final/artifacts/gpu_graph_anomaly_sweep_v1_latest.json"
                ],
                "status": "planned",
            },
            {
                "id": "gpu-04",
                "title": "Universal precursor gate resweep",
                "objective": "Run broader threshold/coherence search with GPU-assisted scoring.",
                "outputs": [
                    "docs/final/artifacts/gpu_universal_precursor_resweep_v1_latest.json"
                ],
                "status": "planned",
            },
            {
                "id": "gpu-05",
                "title": "Shadow-only runtime scorer",
                "objective": "Produce live shadow scores for alerting without auto trade binding.",
                "outputs": [
                    "docs/final/artifacts/gpu_shadow_runtime_score_v1_latest.json"
                ],
                "status": "planned",
            },
        ],
        "execution_order": ["gpu-01", "gpu-02", "gpu-03", "gpu-04", "gpu-05"],
        "notes_ko": [
            "본 백로그는 의미 생성/서사 단정이 아니라 수치 스캔 가속 작업만 포함한다.",
            "모든 산출물은 B-track research_only로 유지하고 Track A 자동 합선 금지.",
        ],
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
