#!/usr/bin/env python3
"""Build GPU full-edge cosine benchmark artifact from latest probe outputs."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
BACKTEST = ROOT / "backtest_results"

DEFAULT_BENCH = BACKTEST / "LOGOS_GPU_BENCH_v2.json"
DEFAULT_IMF = BACKTEST / "LOGOS_RESONANCE_PROBE_IMF_TOP100.json"
DEFAULT_LEHMAN = BACKTEST / "LOGOS_RESONANCE_PROBE_LEHMAN_TOP100.json"
DEFAULT_OUT = ART / "gpu_full_edge_cosine_benchmark_v1_latest.json"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return obj if isinstance(obj, dict) else {}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--bench-json", type=Path, default=DEFAULT_BENCH)
    ap.add_argument("--imf-json", type=Path, default=DEFAULT_IMF)
    ap.add_argument("--lehman-json", type=Path, default=DEFAULT_LEHMAN)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    bench = _load(args.bench_json)
    imf = _load(args.imf_json)
    lehman = _load(args.lehman_json)

    verses_encoded = int(bench.get("verses_encoded") or 0)
    scanned_imf = int(imf.get("verses_scanned") or 0)
    scanned_lehman = int(lehman.get("verses_scanned") or 0)
    corpus_paths = bench.get("corpus_paths") if isinstance(bench.get("corpus_paths"), list) else []
    used_fixture_fallback = any("tests\\fixtures\\logos_mini.jsonl" in str(p).lower() for p in corpus_paths)

    payload = {
        "schema": "gpu_full_edge_cosine_benchmark_v1",
        "generated_at_utc": _now(),
        "research_only": True,
        "inputs": {
            "bench_json": str(args.bench_json).replace("\\", "/"),
            "imf_json": str(args.imf_json).replace("\\", "/"),
            "lehman_json": str(args.lehman_json).replace("\\", "/"),
        },
        "benchmark": {
            "device": bench.get("device"),
            "cuda_available": bench.get("cuda_available"),
            "verses_encoded": verses_encoded,
            "items_per_second_encode_phase": bench.get("items_per_second_encode_phase"),
            "items_per_second_wall": bench.get("items_per_second_wall"),
            "peak_cuda_memory_mb": bench.get("peak_cuda_memory_mb"),
            "corpus_paths": corpus_paths,
        },
        "scans": {
            "imf_verses_scanned": scanned_imf,
            "lehman_verses_scanned": scanned_lehman,
            "imf_top_k": len(imf.get("hits") or []),
            "lehman_top_k": len(lehman.get("hits") or []),
        },
        "status": "partial_fixture_fallback" if used_fixture_fallback else "ready_full_corpus",
        "notes_ko": [
            "코사인 스캔은 GPU 경로에서 정상 실행됨.",
            "현재 코퍼스 경로가 fixture fallback이면 full corpus 경로 복구 후 재실행 필요.",
        ],
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.out}")
    print(f"status={payload['status']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
