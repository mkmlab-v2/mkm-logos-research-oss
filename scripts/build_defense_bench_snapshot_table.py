#!/usr/bin/env python3
"""Assemble one JSON table row-set for defense-facing briefs: Track A + hybrid UAV (+ optional merged) + bridge A/B.

Reads existing artifacts only — does not run benchmarks.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

ART = ROOT / "docs" / "final" / "artifacts"
DEFAULT_TRACK_A = ART / "MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json"
DEFAULT_HYBRID = ART / "defense_hybrid_compression_bench_v0.json"
DEFAULT_HYBRID_MERGED = ART / "defense_hybrid_compression_bench_merged_v0.json"
DEFAULT_BRIDGE_SUMMARY = ART / "MULTILENS_BRIDGE_POLICY_AB_V1.json"
DEFAULT_BRIDGE_BY_MODE = ART / "MULTILENS_BRIDGE_POLICY_AB_BY_MODE_V1.json"
DEFAULT_OUT = ART / "DEFENSE_BENCH_SNAPSHOT_TABLE_V1.json"


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser(description="Build DEFENSE_BENCH_SNAPSHOT_TABLE_V1.json from artifacts.")
    ap.add_argument("--track-a", type=Path, default=DEFAULT_TRACK_A)
    ap.add_argument("--hybrid", type=Path, default=DEFAULT_HYBRID)
    ap.add_argument(
        "--hybrid-merged",
        type=Path,
        default=DEFAULT_HYBRID_MERGED,
        help="If this file exists, add a merged (100+stress) hybrid row.",
    )
    ap.add_argument("--bridge-summary", type=Path, default=DEFAULT_BRIDGE_SUMMARY)
    ap.add_argument("--bridge-by-mode", type=Path, default=DEFAULT_BRIDGE_BY_MODE)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    track_a = _load(args.track_a)
    hybrid = _load(args.hybrid)
    cm = track_a.get("compression_metrics") or {}
    agg = hybrid.get("aggregate") or {}

    rows: list[dict[str, Any]] = [
        {
            "lane": "track_a_universal",
            "artifact": str(args.track_a.relative_to(ROOT)).replace("\\", "/"),
            "unit": "multilens V2 bench",
            "global_token_saving_rate": cm.get("global_token_saving_rate"),
            "avg_reconstruction_fidelity_jaccard": cm.get("avg_reconstruction_fidelity_jaccard"),
            "case_count": cm.get("case_count"),
            "note": "토큰·Jaccard — 바이트 하이브리드와 동일 문장 병기 금지.",
        },
        {
            "lane": "defense_hybrid_uav_synthetic",
            "artifact": str(args.hybrid.relative_to(ROOT)).replace("\\", "/"),
            "unit": "bytes + literal semantic lane",
            "critical_field_integrity": agg.get("critical_field_integrity"),
            "mean_payload_compression_ratio": agg.get("mean_payload_compression_ratio"),
            "global_token_saving_rate": agg.get("global_token_saving_rate"),
            "mean_semantic_jaccard": agg.get("mean_semantic_jaccard"),
            "record_count": hybrid.get("record_count"),
            "note": "필수 필드 msgpack 와이어 + situational_text 압축 UTF-8; research_only.",
        },
    ]

    if args.hybrid_merged.is_file():
        merged = _load(args.hybrid_merged)
        magg = merged.get("aggregate") or {}
        rows.insert(
            2,
            {
                "lane": "defense_hybrid_uav_synthetic_merged",
                "artifact": str(args.hybrid_merged.relative_to(ROOT)).replace("\\", "/"),
                "unit": "bytes + literal semantic lane (primary + stress append)",
                "critical_field_integrity": magg.get("critical_field_integrity"),
                "mean_payload_compression_ratio": magg.get("mean_payload_compression_ratio"),
                "global_token_saving_rate": magg.get("global_token_saving_rate"),
                "mean_semantic_jaccard": magg.get("mean_semantic_jaccard"),
                "record_count": merged.get("record_count"),
                "stress_input_appended": merged.get("stress_input_appended"),
                "note": "run_defense_hybrid_compression_bench.py --append-stress; headline 수치는 100건 전용 행과 혼동 금지.",
            },
        )

    bridge_by_mode: dict[str, Any] | None = None
    if args.bridge_by_mode.is_file():
        bridge_by_mode = _load(args.bridge_by_mode)
        rows.append(
            {
                "lane": "multilens_bridge_policy_ab_by_mode",
                "artifact": str(args.bridge_by_mode.relative_to(ROOT)).replace("\\", "/"),
                "unit": "same V2 input; bridge OFF vs ON per SLA track",
                "modes": list((bridge_by_mode.get("modes") or {}).keys()),
                "note": "슬라이스별 token_saving / Jaccard는 modes.*.bridge_off|on.compression_metrics_summary",
            }
        )

    if args.bridge_summary.is_file():
        br = _load(args.bridge_summary)
        off = br.get("bridge_off", {}).get("compression_metrics_summary") or {}
        on = br.get("bridge_on", {}).get("compression_metrics_summary") or {}
        rows.append(
            {
                "lane": "multilens_bridge_policy_ab_single_mode",
                "artifact": str(args.bridge_summary.relative_to(ROOT)).replace("\\", "/"),
                "unit": "same V2 input; single --mode (default ultra-literal)",
                "mode": br.get("mode"),
                "bridge_off_global_token_saving_rate": off.get("global_token_saving_rate"),
                "bridge_on_global_token_saving_rate": on.get("global_token_saving_rate"),
                "jaccard_either": off.get("avg_reconstruction_fidelity_jaccard"),
                "note": "레거시 세 파일 OFF/ON/SUMMARY와 동조; --all-modes와 병행 가능.",
            }
        )

    doc = {
        "schema": "defense_bench_snapshot_table_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "purpose": "제안서·내부 브리핑용 한 화면 표 — 토큰 행과 바이트 행을 섞어 쓰지 말 것.",
        "rows": rows,
        "sources": {
            "track_a": str(args.track_a.relative_to(ROOT)).replace("\\", "/"),
            "hybrid": str(args.hybrid.relative_to(ROOT)).replace("\\", "/"),
            "hybrid_merged": str(args.hybrid_merged.relative_to(ROOT)).replace("\\", "/")
            if args.hybrid_merged.is_file()
            else None,
            "bridge_summary": str(args.bridge_summary.relative_to(ROOT)).replace("\\", "/")
            if args.bridge_summary.is_file()
            else None,
            "bridge_by_mode": str(args.bridge_by_mode.relative_to(ROOT)).replace("\\", "/")
            if args.bridge_by_mode.is_file()
            else None,
        },
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
