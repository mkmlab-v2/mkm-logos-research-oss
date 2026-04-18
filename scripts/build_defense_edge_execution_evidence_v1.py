# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.92, L:0.9, K:0.52, M:0.74}
# Balance: 95
# Purpose: Build fact-safe edge execution evidence from local GPU env and defense bench artifacts.
# Keywords: defense, edge, gpu, benchmark, fact-lock, artifact
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
BENCH_L1 = ART / "bench_l1_api_load_latest.json"
DEFENSE_HYBRID = ART / "defense_hybrid_compression_bench_v0.json"
OUT = ART / "defense_edge_execution_evidence_v1.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _safe_float(value: Any) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _gpu_probe() -> dict[str, Any]:
    try:
        import torch  # type: ignore
    except Exception as exc:  # pragma: no cover
        return {
            "torch_available": False,
            "probe_error": f"{type(exc).__name__}: {exc}",
        }

    device_count = int(torch.cuda.device_count()) if torch.cuda.is_available() else 0
    devices: list[dict[str, Any]] = []
    for idx in range(device_count):
        props = torch.cuda.get_device_properties(idx)
        devices.append(
            {
                "index": idx,
                "name": props.name,
                "total_memory_gb": round(props.total_memory / (1024**3), 2),
                "multi_processor_count": int(props.multi_processor_count),
            }
        )
    return {
        "torch_available": True,
        "torch_version": getattr(torch, "__version__", None),
        "cuda_available": bool(torch.cuda.is_available()),
        "cuda_version": getattr(torch.version, "cuda", None),
        "device_count": device_count,
        "devices": devices,
    }


def main() -> int:
    bench_doc = _load_json(BENCH_L1)
    hybrid_doc = _load_json(DEFENSE_HYBRID)
    gpu_env = _gpu_probe()

    bench_latency = bench_doc.get("latency_ms") or {}
    hybrid_agg = hybrid_doc.get("aggregate") or {}

    out_doc = {
        "schema": "defense_edge_execution_evidence_v1",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "purpose": "Fact-safe submission evidence for edge/on-device narrative. No extrapolated board multiplier.",
        "sources": {
            "bench_l1": str(BENCH_L1.relative_to(ROOT)).replace("\\", "/"),
            "defense_hybrid": str(DEFENSE_HYBRID.relative_to(ROOT)).replace("\\", "/"),
        },
        "local_runtime_facts": {
            "bench_environment": bench_doc.get("bench_environment"),
            "base_url": bench_doc.get("base_url"),
            "total_requests": bench_doc.get("total_requests"),
            "max_concurrent": bench_doc.get("max_concurrent"),
            "latency_ms": {
                "p50": _safe_float(bench_latency.get("p50")),
                "p95": _safe_float(bench_latency.get("p95")),
                "p99": _safe_float(bench_latency.get("p99")),
                "max": _safe_float(bench_latency.get("max")),
            },
            "rss_measured": bool(bench_doc.get("rss_self_sampled") or bench_doc.get("server_pid")),
            "rss_note": "RSS values are null unless --server-pid or --rss-self is used during bench.",
        },
        "hybrid_integrity_facts": {
            "critical_field_integrity": _safe_float(hybrid_agg.get("critical_field_integrity")),
            "mean_semantic_jaccard": _safe_float(hybrid_agg.get("mean_semantic_jaccard")),
            "mean_payload_compression_ratio": _safe_float(hybrid_agg.get("mean_payload_compression_ratio")),
            "global_token_saving_rate": _safe_float(hybrid_agg.get("global_token_saving_rate")),
        },
        "local_gpu_environment": gpu_env,
        "proposal_guardrails": [
            "Do not claim deployed-board latency from this artifact; this is local evidence.",
            "Do not cite memory numbers unless RSS is directly measured in the same run.",
            "Keep wording as reproducible local measurements with source artifact paths.",
        ],
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(OUT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
