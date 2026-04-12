# -*- coding: utf-8 -*-
"""4-grid B-track spike: baseline Zstd vs sasang codebook substitution vs routed vs 4D-mix + Zstd.

Measures payload size (UTF-8) vs zstd-compressed bytes assuming **shared** static dictionaries OOB.
Hypothesis tier B; not production compression. Requires: pip install zstandard
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import statistics
import sys
import time
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from tools.core.myeongri_4d_correction import _ohang_data_to_4d

SCHEMA = "spike_4grid_myeongri_compression_v1"
SASANG_KEYS = ("taeeum_in", "soeum_in", "taeyang_in", "soyang_in")
DEFAULT_CODEBOOK_DIR = _ROOT / "docs" / "final" / "artifacts" / "derived" / "myeongri_sasang_codebook_spike_v1"


def _zstd(data: bytes, level: int) -> bytes | None:
    try:
        import zstandard as zstd

        return zstd.ZstdCompressor(level=level).compress(data)
    except Exception:
        return None


def _load_tokens(path: Path) -> list[str]:
    if not path.is_file():
        return []
    doc = json.loads(path.read_text(encoding="utf-8"))
    toks = doc.get("tokens") or []
    return [str(t) for t in toks if str(t).strip()]


def _substitute(text: str, tokens: list[str], max_codes: int = 512) -> str:
    """Longest-token-first replace with private-use codepoints (reversible for same table)."""
    out = text
    for i, tok in enumerate(tokens[:max_codes]):
        if not tok:
            continue
        repl = chr(0xE000 + i)
        out = out.replace(tok, repl)
    return out


def _synthetic_ohang(text: str) -> dict[str, Any]:
    h = hashlib.sha256(text.encode("utf-8")).digest()
    vals = [int(h[i]) / 255.0 for i in range(5)]
    s = sum(vals) or 1.0
    return {
        "wood_strength": vals[0] / s,
        "fire_strength": vals[1] / s,
        "earth_strength": vals[2] / s,
        "metal_strength": vals[3] / s,
        "water_strength": vals[4] / s,
    }


def _mix_bytes_inv(data: bytes, v4: dict[str, float]) -> bytes:
    """Invertible per-byte mix using 4D vector (B-track toy)."""
    axes = [round(v4[k] * 255) & 0xFF for k in ("S", "L", "K", "M")]
    out = bytearray(len(data))
    for i, b in enumerate(data):
        out[i] = (b + axes[i % 4]) & 0xFF
    return bytes(out)


def _route_sasang(text: str, codebook_dir: Path) -> str:
    scores: dict[str, int] = {k: 0 for k in SASANG_KEYS}
    lower = text.lower()
    for key in SASANG_KEYS:
        toks = _load_tokens(codebook_dir / f"{key}.json")
        for t in toks:
            if len(t) >= 2 and t in text:
                scores[key] += text.count(t)
            elif t.lower() in lower and t != t.lower():
                scores[key] += lower.count(t.lower())
    best = max(scores, key=lambda k: scores[k])
    if scores[best] <= 0:
        return "taeeum_in"
    return best


def _generate_corpus(rng: random.Random, n: int, codebook_dir: Path) -> list[str]:
    global_toks = _load_tokens(codebook_dir / "global_tokens.json")
    if not global_toks:
        raise RuntimeError("missing codebook; run build_myeongri_sasang_codebook_spike_v1.py")
    per: dict[str, list[str]] = {}
    for key in SASANG_KEYS:
        per[key] = _load_tokens(codebook_dir / f"{key}.json") or global_toks[:3]

    docs: list[str] = []
    for i in range(n):
        key = rng.choice(SASANG_KEYS)
        pool = per[key] + global_toks
        parts = [rng.choice(pool) for _ in range(rng.randint(6, 24))]
        filler = " ".join(parts)
        docs.append(f"{filler} 반복{i} 사상의학 체질 " * rng.randint(1, 2))
    return docs


def _bench_one(text: str, codebook_dir: Path, zstd_level: int) -> dict[str, Any]:
    raw = text.encode("utf-8")
    raw_len = len(raw)

    t0 = time.perf_counter()
    z0 = _zstd(raw, zstd_level)
    ms0 = (time.perf_counter() - t0) * 1000.0

    global_toks = _load_tokens(codebook_dir / "global_tokens.json")
    t1 = time.perf_counter()
    sub_g = _substitute(text, sorted(global_toks, key=len, reverse=True))
    z1 = _zstd(sub_g.encode("utf-8"), zstd_level)
    ms1 = (time.perf_counter() - t1) * 1000.0

    sas = _route_sasang(text, codebook_dir)
    local_toks = _load_tokens(codebook_dir / f"{sas}.json") or global_toks
    t2 = time.perf_counter()
    sub_r = _substitute(text, sorted(local_toks, key=len, reverse=True))
    z2 = _zstd(sub_r.encode("utf-8"), zstd_level)
    ms2 = (time.perf_counter() - t2) * 1000.0

    oh = _synthetic_ohang(sub_r)
    v4 = _ohang_data_to_4d(oh)
    t3 = time.perf_counter()
    mixed = _mix_bytes_inv(sub_r.encode("utf-8"), v4)
    z3 = _zstd(mixed, zstd_level)
    ms3 = (time.perf_counter() - t3) * 1000.0

    def ratio(z: bytes | None) -> float | None:
        if z is None or raw_len == 0:
            return None
        return 1.0 - (len(z) / raw_len)

    return {
        "raw_utf8_bytes": raw_len,
        "baseline_zstd_bytes": None if z0 is None else len(z0),
        "myeongri_light_zstd_bytes": None if z1 is None else len(z1),
        "myeongri_routed_zstd_bytes": None if z2 is None else len(z2),
        "heavy_fusion_zstd_bytes": None if z3 is None else len(z3),
        "routed_sasang": sas,
        "ratio_baseline": ratio(z0),
        "ratio_light": ratio(z1),
        "ratio_routed": ratio(z2),
        "ratio_heavy": ratio(z3),
        "ms_baseline": round(ms0, 3),
        "ms_light": round(ms1, 3),
        "ms_routed": round(ms2, 3),
        "ms_heavy": round(ms3, 3),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--codebook-dir", type=Path, default=DEFAULT_CODEBOOK_DIR)
    ap.add_argument("--samples", type=int, default=100)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--zstd-level", type=int, default=3)
    ap.add_argument(
        "--out",
        type=Path,
        default=_ROOT / "docs" / "final" / "artifacts" / "derived" / "spike_4grid_myeongri_compression_latest.json",
    )
    ap.add_argument("--stdout-only", action="store_true")
    ap.add_argument(
        "--full-rows",
        action="store_true",
        help="Include per-sample rows in --out JSON (large). Default: summary only.",
    )
    args = ap.parse_args()

    if _zstd(b"test", args.zstd_level) is None:
        print("ERROR: zstandard not installed (pip install zstandard)", file=sys.stderr)
        return 2

    rng = random.Random(args.seed)
    corpus = _generate_corpus(rng, args.samples, args.codebook_dir)

    rows: list[dict[str, Any]] = []
    for text in corpus:
        rows.append(_bench_one(text, args.codebook_dir, args.zstd_level))

    def _mean(key: str) -> float | None:
        vals = [r[key] for r in rows if r.get(key) is not None]
        return float(statistics.mean(vals)) if vals else None

    summary = {
        "schema": SCHEMA,
        "hypothesis_tier": "B",
        "boundary_ack": True,
        "label": "[HYPO][NON-MEDICAL] 4-grid compression spike; shared static dict assumed OOB",
        "samples": args.samples,
        "seed": args.seed,
        "zstd_level": args.zstd_level,
        "codebook_dir": str(args.codebook_dir),
        "mean_ratio_baseline": _mean("ratio_baseline"),
        "mean_ratio_light": _mean("ratio_light"),
        "mean_ratio_routed": _mean("ratio_routed"),
        "mean_ratio_heavy": _mean("ratio_heavy"),
        "mean_ms_baseline": _mean("ms_baseline"),
        "mean_ms_light": _mean("ms_light"),
        "mean_ms_routed": _mean("ms_routed"),
        "mean_ms_heavy": _mean("ms_heavy"),
    }
    if args.stdout_only or args.full_rows:
        summary["rows"] = rows

    out_txt = json.dumps(summary, ensure_ascii=False, indent=2)
    if args.stdout_only:
        print(out_txt)
        return 0

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(out_txt, encoding="utf-8")
    print(str(args.out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
