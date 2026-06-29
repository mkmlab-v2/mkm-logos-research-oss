#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--metrics", type=Path, default=ROOT / "reports" / "e2e_memory_proof_metrics_latest.json")
    ap.add_argument("--live-metrics", type=Path, default=ROOT / "reports" / "e2e_memory_proof_live_metrics_latest.json")
    ap.add_argument("--stats", type=Path, default=ROOT / "reports" / "e2e_memory_proof_stats_latest.json")
    ap.add_argument("--onepager-out", type=Path, default=ROOT / "docs" / "final" / "artifacts" / "E2E_MEMORY_PROOF_B2B_ONEPAGER_latest.md")
    ap.add_argument("--manifest-out", type=Path, default=ROOT / "reports" / "e2e_memory_proof_repro_manifest_latest.json")
    args = ap.parse_args()

    metrics = _read(args.metrics)
    live_metrics = _read(args.live_metrics)
    stats = _read(args.stats)

    m1 = (metrics.get("metrics") or {}).get("m1_token_cost") or {}
    m2 = (metrics.get("metrics") or {}).get("m2_ttft") or {}
    m3_offline = (metrics.get("metrics") or {}).get("m3_quality_safety") or {}
    m3_live = (live_metrics.get("metrics") or {}).get("m3_quality_safety") or {}
    m3 = m3_live if m3_live else m3_offline
    summary = stats.get("summary") or {}

    onepager = [
        "# E2E Memory Proof (B2B Onepager)",
        "",
        f"- generated_at_utc: `{utc_now_iso()}`",
        "- mode: `research_only`",
        "- scope: `compressed resume packet vs baseline`",
        "",
        "## Conclusion",
        f"- M1 cost reduction ratio: `{summary.get('m1_cost_reduction_ratio')}`",
        f"- M2 TTFT delta mean(ms): `{summary.get('m2_ttft_delta_ms_mean')}`",
        f"- M2 CI95(ms): `{summary.get('m2_ttft_delta_ms_ci95')}`",
        "",
        "## M1 Token/Cost",
        f"- avg tokens/run baseline: `{((m1.get('input_tokens_avg_per_run') or {}).get('baseline_a'))}`",
        f"- avg tokens/run compressed: `{((m1.get('input_tokens_avg_per_run') or {}).get('compressed_b'))}`",
        f"- estimated cost baseline: `{((m1.get('estimated_cost_usd') or {}).get('baseline_a'))}`",
        f"- estimated cost compressed: `{((m1.get('estimated_cost_usd') or {}).get('compressed_b'))}`",
        "",
        "## M2 TTFT",
        f"- p50 baseline(ms): `{((m2.get('ttft_p50_ms') or {}).get('baseline_a'))}`",
        f"- p50 compressed(ms): `{((m2.get('ttft_p50_ms') or {}).get('compressed_b'))}`",
        f"- p95 baseline(ms): `{((m2.get('ttft_p95_ms') or {}).get('baseline_a'))}`",
        f"- p95 compressed(ms): `{((m2.get('ttft_p95_ms') or {}).get('compressed_b'))}`",
        "",
        "## M3 Quality/Safety",
        f"- guardrail violation baseline: `{((m3.get('guardrail_violation_rate') or {}).get('baseline_a'))}`",
        f"- guardrail violation compressed: `{((m3.get('guardrail_violation_rate') or {}).get('compressed_b'))}`",
        f"- guard-step failure baseline: `{((m3.get('guard_step_failure_rate') or {}).get('baseline_a'))}`",
        f"- guard-step failure compressed: `{((m3.get('guard_step_failure_rate') or {}).get('compressed_b'))}`",
        f"- composite failure baseline: `{((m3.get('composite_failure_rate') or {}).get('baseline_a'))}`",
        f"- composite failure compressed: `{((m3.get('composite_failure_rate') or {}).get('compressed_b'))}`",
        f"- degraded run baseline: `{((m3.get('degraded_run_rate') or {}).get('baseline_a'))}`",
        f"- degraded run compressed: `{((m3.get('degraded_run_rate') or {}).get('compressed_b'))}`",
        "",
        "## Limits",
        "- This package is `[HYPO]` research_only evidence.",
        "- No Track A promotion or live trading action is implied.",
    ]
    args.onepager_out.parent.mkdir(parents=True, exist_ok=True)
    args.onepager_out.write_text("\n".join(onepager) + "\n", encoding="utf-8")

    manifest: dict[str, Any] = {
        "schema": "e2e_memory_proof_repro_manifest_v1",
        "generated_at_utc": utc_now_iso(),
        "research_only": True,
        "boundary_ack": "[HYPO] repro manifest for E2E memory proof",
        "commands": [
            "py scripts/run_e2e_memory_proof_offline_ab_v1.py --runs 5",
            "py scripts/run_e2e_memory_proof_live_ab_v1.py",
            "py scripts/aggregate_e2e_memory_proof_stats_v1.py",
            "py scripts/build_e2e_memory_proof_b2b_pack_v1.py"
        ],
        "inputs": [
            str(args.metrics).replace("\\", "/"),
            str(args.stats).replace("\\", "/"),
            "docs/final/artifacts/e2e_memory_proof_experiment_contract_v1.json"
        ],
        "outputs": [
            "reports/e2e_memory_proof_metrics_latest.json",
            "reports/e2e_memory_proof_live_metrics_latest.json",
            "reports/e2e_memory_proof_stats_latest.json",
            "docs/final/artifacts/E2E_MEMORY_PROOF_B2B_ONEPAGER_latest.md",
            "reports/e2e_memory_proof_repro_manifest_latest.json"
        ]
    }
    args.manifest_out.parent.mkdir(parents=True, exist_ok=True)
    args.manifest_out.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.onepager_out}")
    print(f"WROTE: {args.manifest_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
