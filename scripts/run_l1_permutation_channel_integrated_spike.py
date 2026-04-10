#!/usr/bin/env python3
"""Integrated spike: same noise distribution as run_l1_inverse_decoder_spike_test._noisify
with deterministic side-channel payload (swap log + typo/oov patches) for exact restore.

[FACT] With side_channel applied, restored text == source (round-trip).
[HYPO] Payload byte cost on wire; JSON UTF-8 length used as proxy here.
"""

from __future__ import annotations

import argparse
import json
import random
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from l1_side_channel_wire_codec import (
    codec_availability,
    decode_adaptive_msgpack,
    decode_msgpack,
    decode_msgpack_zstd,
    encode_adaptive_msgpack,
    encode_msgpack_zstd,
    merge_side_channel,
    minimal_payload,
    msgpack_payload_bytes,
)
from run_l1_inverse_decoder_spike_test import _build_corpus, _is_literal_token


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def noisify_with_side_channel(
    sentence: str,
    rng: random.Random,
    noise_level: float,
    forced_mode: str | None = None,
) -> tuple[str, str, dict]:
    """Mirror _noisify; return (noisy_text, mode, side_channel)."""
    toks = sentence.split()
    mode = forced_mode or rng.choice(["swap", "typo", "oov", "swap_typo"])
    swap_log: list[list[int]] = []

    if mode in {"swap", "swap_typo"} and len(toks) >= 2:
        swap_count = 2 if noise_level >= 0.2 else 1
        for _ in range(swap_count):
            i, j = rng.randrange(len(toks)), rng.randrange(len(toks))
            swap_log.append([i, j])
            toks[i], toks[j] = toks[j], toks[i]

    literal_positions = [i for i, t in enumerate(toks) if _is_literal_token(t)]
    typo_patches: list[dict] = []

    if mode in {"typo", "swap_typo"}:
        typo_count = 2 if noise_level >= 0.2 else 1
        for _ in range(typo_count):
            idx = rng.choice(literal_positions) if literal_positions else rng.randrange(len(toks))
            t = toks[idx]
            if len(t) >= 2:
                pos = rng.randrange(len(t))
                orig_ch = t[pos]
                chars = list(t)
                chars[pos] = "X"
                toks[idx] = "".join(chars)
                typo_patches.append({"idx": idx, "char_pos": pos, "orig_char": orig_ch})

    # Stack (idx, token_before): mirrors _noisify but guarantees invertible even if same idx twice.
    oov_stack: list[list[int | str]] = []
    if mode == "oov":
        oov_count = 2 if noise_level >= 0.2 else 1
        for _ in range(oov_count):
            idx = rng.choice(literal_positions) if literal_positions else rng.randrange(len(toks))
            prev = toks[idx]
            oov_stack.append([idx, prev])
            toks[idx] = "OOV_TOKEN"

    side_channel: dict = {
        "schema": "l1_side_channel_v1",
        "mode": mode,
        "swap_log": swap_log,
        "typo_patches": typo_patches,
        "oov_stack": oov_stack,
    }
    return " ".join(toks), mode, side_channel


def restore_from_side_channel(noisy: str, side_channel: dict) -> str:
    """Inverse of noisify_with_side_channel: last noise op undone first."""
    toks = noisy.split()
    # OOV-only / order in _noisify: swaps -> typo -> oov. Inverse: oov -> typo -> swaps.
    for entry in reversed(side_channel.get("oov_stack", [])):
        idx, prev = int(entry[0]), str(entry[1])
        if idx < len(toks):
            toks[idx] = prev
    for p in reversed(side_channel.get("typo_patches", [])):
        idx = int(p["idx"])
        pos = int(p["char_pos"])
        ch = p["orig_char"]
        if idx < len(toks) and pos < len(toks[idx]):
            s = list(toks[idx])
            s[pos] = ch
            toks[idx] = "".join(s)
    for pair in reversed(side_channel.get("swap_log", [])):
        i, j = int(pair[0]), int(pair[1])
        if i < len(toks) and j < len(toks):
            toks[i], toks[j] = toks[j], toks[i]
    return " ".join(toks)


def run_benchmark(
    seeds: list[int],
    samples_per_seed: int,
    noise_level: float,
    modes: list[str],
    zstd_level: int = 3,
    zstd_min_raw_bytes: int = 64,
) -> dict:
    corpus = _build_corpus()
    avail = codec_availability()
    rows: list[dict] = []
    round_trip_codec_ok = 0
    round_trip_codec_checked = 0
    for mode in modes:
        exact = 0
        total = 0
        overhead_bytes: list[int] = []
        overhead_msgpack: list[int] = []
        overhead_zstd: list[int] = []
        overhead_adaptive: list[int] = []
        adaptive_zstd_picks = 0
        for seed in seeds:
            rng = random.Random(seed)
            for _ in range(samples_per_seed):
                src = corpus[rng.randrange(len(corpus))]
                noisy, _, sc = noisify_with_side_channel(
                    src, rng, noise_level, forced_mode=mode
                )
                restored = restore_from_side_channel(noisy, sc)
                total += 1
                if restored == src:
                    exact += 1
                payload = minimal_payload(sc)
                overhead_bytes.append(
                    len(json.dumps(payload, ensure_ascii=False).encode("utf-8"))
                )
                if avail.msgpack:
                    mpb = msgpack_payload_bytes(payload)
                    assert mpb is not None
                    overhead_msgpack.append(len(mpb))
                    round_trip_codec_checked += 1
                    wire_adaptive, variant = encode_adaptive_msgpack(
                        payload,
                        zstd_min_raw_bytes=zstd_min_raw_bytes,
                        zstd_level=zstd_level,
                    )
                    overhead_adaptive.append(len(wire_adaptive))
                    if variant == "zstd":
                        adaptive_zstd_picks += 1
                    decoded = decode_adaptive_msgpack(wire_adaptive)
                    merged = merge_side_channel(sc["mode"], decoded)
                    if avail.zstandard:
                        zblob = encode_msgpack_zstd(payload, level=zstd_level)
                        assert zblob is not None
                        overhead_zstd.append(len(zblob))
                    if restore_from_side_channel(noisy, merged) == src:
                        round_trip_codec_ok += 1
        row: dict = {
            "mode": mode,
            "exact_restore_rate": exact / max(1, total),
            "samples": total,
            "overhead_json_utf8_bytes_mean": statistics.mean(overhead_bytes) if overhead_bytes else 0.0,
            "overhead_json_utf8_bytes_min": min(overhead_bytes) if overhead_bytes else 0,
            "overhead_json_utf8_bytes_max": max(overhead_bytes) if overhead_bytes else 0,
        }
        if overhead_msgpack:
            row["overhead_msgpack_bytes_mean"] = statistics.mean(overhead_msgpack)
            row["overhead_msgpack_bytes_min"] = min(overhead_msgpack)
            row["overhead_msgpack_bytes_max"] = max(overhead_msgpack)
        if overhead_zstd:
            row["overhead_msgpack_zstd_bytes_mean"] = statistics.mean(overhead_zstd)
            row["overhead_msgpack_zstd_bytes_min"] = min(overhead_zstd)
            row["overhead_msgpack_zstd_bytes_max"] = max(overhead_zstd)
        if overhead_adaptive:
            row["overhead_adaptive_tagged_wire_bytes_mean"] = statistics.mean(overhead_adaptive)
            row["overhead_adaptive_tagged_wire_bytes_min"] = min(overhead_adaptive)
            row["overhead_adaptive_tagged_wire_bytes_max"] = max(overhead_adaptive)
            row["adaptive_zstd_choice_rate"] = adaptive_zstd_picks / max(1, total)
        rows.append(row)
    wire_note = (
        "[FACT] msgpack, always-zstd, and adaptive tagged wire (1B tag + raw|zstd) measured; "
        "round-trip via decode_adaptive_msgpack. research_only / not production API contract."
    )
    if not avail.msgpack:
        wire_note = (
            "[HYPO] msgpack not installed; only JSON UTF-8 proxy measured. "
            "pip install msgpack zstandard for binary wire stats."
        )
    elif not avail.zstandard:
        wire_note = (
            "[FACT] msgpack round-trip restore checked; zstandard missing — no zstd size rows. "
            "pip install zstandard for Zstd(MessagePack) sizes."
        )
    return {
        "schema": "l1_permutation_channel_integrated_spike_v3",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "wire_codecs": {
            "msgpack_available": avail.msgpack,
            "zstandard_available": avail.zstandard,
            "zstd_level": zstd_level if avail.zstandard else None,
            "zstd_min_raw_bytes": zstd_min_raw_bytes if avail.msgpack else None,
            "round_trip_restore_via_codec_checked": round_trip_codec_checked,
            "round_trip_restore_via_codec_ok": round_trip_codec_ok,
        },
        "claims": {
            "exact_restore_with_side_channel": "[FACT] 1.0 when swap_log/typo/oov patches applied as below",
            "payload_wire_format": wire_note,
        },
        "inputs": {
            "seeds": seeds,
            "samples_per_seed": samples_per_seed,
            "noise_level": noise_level,
            "modes": modes,
            "zstd_min_raw_bytes": zstd_min_raw_bytes,
        },
        "rows": rows,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--seeds", type=str, default="701,809,907")
    ap.add_argument("--samples", type=int, default=180)
    ap.add_argument("--noise-level", type=float, default=0.2)
    ap.add_argument(
        "--modes",
        type=str,
        default="swap,swap_typo,typo,oov",
        help="Comma-separated forced modes",
    )
    ap.add_argument(
        "--out",
        type=Path,
        default=Path("docs/final/artifacts/l1_permutation_channel_integrated_spike_latest.json"),
    )
    ap.add_argument(
        "--zstd-level",
        type=int,
        default=3,
        help="Zstd compression level when zstandard is installed",
    )
    ap.add_argument(
        "--zstd-min-raw-bytes",
        type=int,
        default=64,
        help=(
            "Adaptive wire: only try zstd when raw msgpack length is >= this "
            "(and zstd is smaller than raw)."
        ),
    )
    args = ap.parse_args()

    seeds = [int(x.strip()) for x in args.seeds.split(",") if x.strip()]
    modes = [x.strip() for x in args.modes.split(",") if x.strip()]
    doc = run_benchmark(
        seeds,
        args.samples,
        args.noise_level,
        modes,
        zstd_level=args.zstd_level,
        zstd_min_raw_bytes=args.zstd_min_raw_bytes,
    )

    root = Path(__file__).resolve().parent.parent
    out_path = args.out if args.out.is_absolute() else root / args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(
        json.dumps(
            {"ok": True, "out": str(out_path), "rows": doc["rows"]},
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
