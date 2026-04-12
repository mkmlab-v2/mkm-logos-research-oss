# -*- coding: utf-8 -*-
"""Spike: codebook shard keywords → sovereign placeholders; measure tiktoken savings vs baseline.

Reads ``codebook/shards/zone_*.json`` (routing_keywords + must_keep_* + guard_tokens), maps up to
``max_terms`` unique strings to ``<S00>``.., compares o200k_base counts. Hypothesis tier B.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

SCHEMA = "spike_sovereign_vocab_efficiency_v1"
DEFAULT_SHARDS_DIR = _ROOT / "codebook" / "shards"
TERM_KEYS = ("routing_keywords", "must_keep_hard_terms", "must_keep_soft_terms", "guard_tokens")


def _collect_terms(shards_dir: Path, max_leaf: int) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    paths = sorted(shards_dir.glob("zone_*.json"))
    for p in paths:
        doc = json.loads(p.read_text(encoding="utf-8"))
        for key in TERM_KEYS:
            for t in doc.get(key) or []:
                s = str(t).strip()
                if s and s not in seen:
                    seen.add(s)
                    out.append(s)
                if len(out) >= max_leaf:
                    return out[:max_leaf]
    return out


def _get_encoder():
    try:
        import tiktoken

        return tiktoken.get_encoding("o200k_base"), "o200k_base"
    except Exception:
        return None, "utf8_byte_proxy"


def _encode_n(enc: object | None, text: str) -> int:
    if enc is not None:
        return len(enc.encode(text))
    return max(1, len(text.encode("utf-8")) // 4)


def _phrases_that_save_tokens(terms: list[str], *, max_phrases: int, chunk: int) -> list[str]:
    """Build multi-word phrases from shard terms; keep only if phrase tokens > placeholder tokens."""
    if not terms:
        return []
    enc, _ = _get_encoder()
    uniq = list(dict.fromkeys(terms))
    uniq.sort(key=lambda s: -len(s))
    phrases: list[str] = []
    i = 0
    while len(phrases) < max_phrases and i + chunk <= len(uniq):
        phrase = " ".join(uniq[i : i + chunk])
        i += chunk
        ph_idx = len(phrases)
        placeholder = f"<S{ph_idx:02d}>"
        if _encode_n(enc, phrase) > _encode_n(enc, placeholder):
            phrases.append(phrase)
    if len(phrases) < 4 and len(uniq) >= 6:
        i = 0
        phrases = []
        while len(phrases) < max_phrases and i + 5 <= len(uniq):
            phrase = " ".join(uniq[i : i + 5])
            i += 5
            ph_idx = len(phrases)
            placeholder = f"<S{ph_idx:02d}>"
            if _encode_n(enc, phrase) > _encode_n(enc, placeholder):
                phrases.append(phrase)
    return phrases


def _replace_sovereign(text: str, terms: list[str]) -> str:
    indexed = sorted(enumerate(terms), key=lambda x: len(x[1]), reverse=True)
    out = text
    for i, phrase in indexed:
        if not phrase:
            continue
        out = out.replace(phrase, f"<S{i:02d}>")
    return out


def _count_tokens(text: str) -> tuple[int, str]:
    enc, name = _get_encoder()
    if enc is not None:
        return len(enc.encode(text)), name
    return max(1, len(text.encode("utf-8")) // 4), name


def _synthetic_corpus(phrases: list[str], n_lines: int, seed: int) -> str:
    rng = random.Random(seed)
    lines = []
    pool = list(phrases) + ["MKM", "line", "field"]
    for _ in range(n_lines):
        parts = [rng.choice(pool) for _ in range(rng.randint(5, 12))]
        lines.append(" ".join(parts))
    return "\n".join(lines)


def run_spike(
    *,
    shards_dir: Path,
    samples: int,
    seed: int,
    max_leaf_terms: int,
    max_phrases: int,
    phrase_chunk: int,
    stdout_only: bool,
) -> dict[str, Any]:
    leaf = _collect_terms(shards_dir, max_leaf_terms)
    if len(leaf) < 12:
        raise RuntimeError(f"Too few shard terms under {shards_dir}: {len(leaf)}")

    phrases = _phrases_that_save_tokens(leaf, max_phrases=max_phrases, chunk=phrase_chunk)
    if len(phrases) < 4:
        phrases = _phrases_that_save_tokens(leaf, max_phrases=max_phrases, chunk=5)

    if len(phrases) < 4:
        raise RuntimeError(
            "Could not build enough token-saving phrases from shards; check tiktoken vs terms."
        )

    corpus = _synthetic_corpus(phrases, samples, seed)
    sovereign_corpus = _replace_sovereign(corpus, phrases)
    base_n, enc_name = _count_tokens(corpus)
    sov_n, _ = _count_tokens(sovereign_corpus)
    delta = (base_n - sov_n) / base_n if base_n else 0.0

    doc: dict[str, Any] = {
        "schema": SCHEMA,
        "hypothesis_tier": "B",
        "boundary_ack": True,
        "tokenizer": enc_name,
        "shards_dir": str(shards_dir).replace("\\", "/"),
        "shard_glob": "zone_*.json",
        "phrases_mapped": len(phrases),
        "leaf_terms_sampled": len(leaf),
        "samples_lines": samples,
        "seed": seed,
        "baseline_token_count": base_n,
        "sovereign_token_count": sov_n,
        "delta_saving_ratio": round(delta, 6),
    }
    out_path = _ROOT / "docs" / "final" / "artifacts" / "derived" / "spike_sovereign_vocab_efficiency_latest.json"
    if not stdout_only:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(str(out_path))
    return doc


def main() -> int:
    ap = argparse.ArgumentParser(description="Sovereign vocab efficiency spike from codebook shards (B-track)")
    ap.add_argument("--shards-dir", type=Path, default=DEFAULT_SHARDS_DIR)
    ap.add_argument("--samples", type=int, default=120)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--max-leaf-terms", type=int, default=400)
    ap.add_argument("--max-phrases", type=int, default=48)
    ap.add_argument("--phrase-chunk", type=int, default=3)
    ap.add_argument("--stdout-only", action="store_true")
    args = ap.parse_args()
    doc = run_spike(
        shards_dir=args.shards_dir,
        samples=max(1, args.samples),
        seed=args.seed,
        max_leaf_terms=max(50, args.max_leaf_terms),
        max_phrases=max(8, min(100, args.max_phrases)),
        phrase_chunk=max(2, min(8, args.phrase_chunk)),
        stdout_only=bool(args.stdout_only),
    )
    if args.stdout_only:
        print(json.dumps(doc, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
