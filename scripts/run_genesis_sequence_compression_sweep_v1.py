#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ART = ROOT / "docs" / "final" / "artifacts"
OUT_DEFAULT = ART / "genesis_sequence_compression_sweep_latest.json"

BASE_TOKENS = [
    "비트코인",
    "시장",
    "거시",
    "충격",
    "하방",
    "변동성",
    "리스크",
    "방어",
    "유동성",
    "레짐",
    "회복",
    "추세",
]


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _make_seq(length_chars: int, seed: int) -> str:
    out: list[str] = []
    i = 0
    while len(" ".join(out)) < length_chars:
        out.append(BASE_TOKENS[(seed + i) % len(BASE_TOKENS)])
        i += 1
    s = " ".join(out)
    return s[:length_chars]


def _hash64_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).digest()[:8].hex()


def _run_bucket(length_chars: int, samples: int) -> dict:
    raws: list[int] = []
    pointer_bytes = 8
    vector4_bytes = 16
    exact = 0
    codebook: dict[str, str] = {}
    collisions = 0
    for i in range(samples):
        seq = _make_seq(length_chars, i)
        h = _hash64_hex(seq)
        if h in codebook and codebook[h] != seq:
            collisions += 1
        codebook[h] = seq
        exact += int(codebook.get(h) == seq)
        raws.append(len(seq.encode("utf-8")))
    avg_raw = sum(raws) / float(max(1, len(raws)))
    ptr_saving = 1.0 - (pointer_bytes / float(max(1.0, avg_raw)))
    vec_saving = 1.0 - (vector4_bytes / float(max(1.0, avg_raw)))
    return {
        "target_length_chars": length_chars,
        "sample_count": samples,
        "avg_raw_utf8_bytes": avg_raw,
        "pointer_payload_bytes": pointer_bytes,
        "vector4_payload_bytes": vector4_bytes,
        "pointer_saving_rate": ptr_saving,
        "vector4_saving_rate": vec_saving,
        "exact_lookup_rate": exact / float(max(1, samples)),
        "hash64_collision_count": collisions,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--lengths-csv", type=str, default="10,20,40,80,120,200,400,800,1200")
    ap.add_argument("--samples-per-length", type=int, default=64)
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    args = ap.parse_args()

    lengths = [int(x.strip()) for x in args.lengths_csv.split(",") if x.strip()]
    rows = [_run_bucket(n, args.samples_per_length) for n in lengths]
    ptr_breakeven = next((r["target_length_chars"] for r in rows if r["pointer_saving_rate"] > 0.0), None)
    vec_breakeven = next((r["target_length_chars"] for r in rows if r["vector4_saving_rate"] > 0.0), None)

    out_doc = {
        "schema": "genesis_sequence_compression_sweep_v1",
        "generated_at_utc": _now_utc(),
        "research_only": True,
        "promotion_required": True,
        "source_track": "B",
        "inputs": {"lengths_chars": lengths, "samples_per_length": args.samples_per_length},
        "rows": rows,
        "summary": {
            "pointer_break_even_length_chars": ptr_breakeven,
            "vector4_break_even_length_chars": vec_breakeven,
            "note": "Closed-dictionary lookup simulation; not open-vocabulary production claim.",
        },
    }
    out = args.out if args.out.is_absolute() else ROOT / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(out_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(out), "summary": out_doc["summary"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
