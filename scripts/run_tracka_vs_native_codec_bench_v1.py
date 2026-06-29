#!/usr/bin/env python3
"""B-track: Track-A proxy compression ratio vs native zlib/zstd on fixed payload.

research_only — do not replace MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1 KPI.
"""

from __future__ import annotations

import argparse
import json
import statistics
import time
import zlib
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_INPUT = ROOT / "docs/final/artifacts/MULTILENS_PERFORMANCE_EVAL_INPUT_V2.json"
DEFAULT_OUT = ROOT / "docs/final/artifacts/tracka_vs_native_codec_bench_latest.json"
TARGET_RAW_BYTES = 20 * 1024 * 1024


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _tracka_proxy_ratios(input_doc: dict) -> tuple[float, float, int]:
    ratios: list[float] = []
    for case in input_doc.get("compression_cases", []):
        raw = str(case.get("raw_text", "")).encode("utf-8")
        comp = str(case.get("compressed_text", "")).encode("utf-8")
        if not raw:
            continue
        ratios.append(len(comp) / len(raw))
    if not ratios:
        return 0.0, 0.0, 0
    mean_ratio = statistics.mean(ratios)
    return mean_ratio, 1.0 - mean_ratio, len(ratios)


def _build_payload(input_doc: dict, target_bytes: int) -> bytes:
    parts = [str(c.get("raw_text", "")) for c in input_doc.get("compression_cases", []) if c.get("raw_text")]
    if not parts:
        parts = ["MKM tracka_vs_native_codec_bench_v1 synthetic payload. "]
    blob = "\n".join(parts).encode("utf-8")
    if len(blob) >= target_bytes:
        return blob[:target_bytes]
    reps = (target_bytes // max(len(blob), 1)) + 1
    out = (blob * reps)[:target_bytes]
    return out


def _bench_zlib(data: bytes, level: int = 3, rounds: int = 3) -> dict:
    times: list[float] = []
    compressed = b""
    for _ in range(rounds):
        t0 = time.perf_counter()
        compressed = zlib.compress(data, level=level)
        times.append((time.perf_counter() - t0) * 1000.0)
    raw_len = len(data)
    comp_len = len(compressed)
    ratio = comp_len / raw_len if raw_len else 0.0
    return {
        "name": f"zlib_level{level}",
        "ratio": ratio,
        "saving_rate": 1.0 - ratio,
        "compressed_bytes": comp_len,
        "raw_bytes": raw_len,
        "compress_ms_mean": statistics.mean(times),
    }


def _bench_zstd(data: bytes, level: int = 3, rounds: int = 3, trained_dict: bytes | None = None) -> dict:
    try:
        import zstandard as zstd
    except ImportError:
        return {"name": "zstd_unavailable", "available": False}
    times: list[float] = []
    compressed = b""
    if trained_dict:
        cctx = zstd.ZstdCompressor(level=level, dict_data=zstd.ZstdCompressionDict(trained_dict))
        name = "zstd_level3_with_trained_dict"
    else:
        cctx = zstd.ZstdCompressor(level=level)
        name = "zstd_level3_no_dict"
    for _ in range(rounds):
        t0 = time.perf_counter()
        compressed = cctx.compress(data)
        times.append((time.perf_counter() - t0) * 1000.0)
    raw_len = len(data)
    comp_len = len(compressed)
    ratio = comp_len / raw_len if raw_len else 0.0
    return {
        "name": name,
        "available": True,
        "ratio": ratio,
        "saving_rate": 1.0 - ratio,
        "compressed_bytes": comp_len,
        "raw_bytes": raw_len,
        "compress_ms_mean": statistics.mean(times),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Track-A proxy vs native codec bench (B-track, research_only).")
    ap.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--payload-bytes", type=int, default=TARGET_RAW_BYTES)
    args = ap.parse_args()

    input_doc = json.loads(args.input.read_text(encoding="utf-8"))
    mean_ratio, mean_saving, n_samples = _tracka_proxy_ratios(input_doc)
    payload = _build_payload(input_doc, args.payload_bytes)

    trained_dict = None
    try:
        import zstandard as zstd

        sample = payload[: min(len(payload), 256 * 1024)]
        trained_dict = zstd.train_dictionary(32 * 1024, [sample])
    except Exception:
        trained_dict = None

    native = [_bench_zlib(payload)]
    z_no = _bench_zstd(payload, trained_dict=None)
    if z_no.get("available"):
        native.append(z_no)
    if trained_dict is not None:
        z_dict = _bench_zstd(payload, trained_dict=trained_dict)
        if z_dict.get("available"):
            native.append(z_dict)

    out_doc = {
        "schema": "tracka_vs_native_codec_bench_v1",
        "generated_at_utc": _now_utc(),
        "research_only": True,
        "input_json": str(args.input.resolve()),
        "payload_raw_bytes": len(payload),
        "tracka_proxy": {
            "mean_ratio": mean_ratio,
            "mean_saving_rate": mean_saving,
            "samples": n_samples,
            "note": "Proxy from input raw_text/compressed_text pairs; not production Track-A active report.",
        },
        "native_codecs": native,
        "guardrail_note": "Do not replace Track-A ACTIVE KPI with this proxy benchmark.",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(args.out), "tracka_proxy_saving": mean_saving}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
