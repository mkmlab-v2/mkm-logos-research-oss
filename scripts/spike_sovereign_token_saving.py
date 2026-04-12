# -*- coding: utf-8 -*-
"""Spike: baseline tokenizer vs 16 sovereign placeholder tokens for sasang-codebook terms.

Maps up to 16 lexicon terms (from myeongri_sasang_codebook_spike_v1 JSON) to strings
``<S00>``..``<S15>`` and compares tiktoken counts (o200k_base when available).
Hypothesis tier B; not a production tokenizer.
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

SCHEMA = "spike_sovereign_token_saving_v1"
DEFAULT_CODEBOOK_DIR = _ROOT / "docs" / "final" / "artifacts" / "derived" / "myeongri_sasang_codebook_spike_v1"
SASANG_FILES = ("taeeum_in.json", "soeum_in.json", "taeyang_in.json", "soyang_in.json")


def _collect_terms(codebook_dir: Path, max_terms: int = 16) -> list[str]:
    out: list[str] = []
    for name in SASANG_FILES:
        p = codebook_dir / name
        if not p.is_file():
            continue
        doc = json.loads(p.read_text(encoding="utf-8"))
        toks = doc.get("tokens") or []
        for t in toks:
            s = str(t).strip()
            if s and s not in out:
                out.append(s)
            if len(out) >= max_terms:
                return out
    while len(out) < max_terms:
        out.append(f"_pad_{len(out)}")
    return out[:max_terms]


def _replace_sovereign(text: str, terms: list[str]) -> str:
    """Longest phrase first → <S00>..<S15>."""
    indexed = sorted(enumerate(terms), key=lambda x: len(x[1]), reverse=True)
    out = text
    for i, phrase in indexed:
        if not phrase:
            continue
        out = out.replace(phrase, f"<S{i:02d}>")
    return out


def _count_tokens(text: str) -> tuple[int, str]:
    try:
        import tiktoken

        enc = tiktoken.get_encoding("o200k_base")
        n = len(enc.encode(text))
        return n, "o200k_base"
    except Exception:
        # Rough UTF-8 proxy: not comparable to OpenAI billing
        return max(1, len(text.encode("utf-8")) // 4), "utf8_byte_proxy"


def _synthetic_corpus(terms: list[str], n_lines: int, seed: int) -> str:
    rng = random.Random(seed)
    lines = []
    pool = terms + ["일반", "텍스트", "문장", "테스트", "MKM"]
    for _ in range(n_lines):
        parts = [rng.choice(pool) for _ in range(rng.randint(3, 8))]
        lines.append(" ".join(parts))
    return "\n".join(lines)


def run_spike(
    *,
    codebook_dir: Path,
    samples: int,
    seed: int,
    stdout_only: bool,
) -> dict[str, Any]:
    terms = _collect_terms(codebook_dir, 16)
    corpus = _synthetic_corpus(terms, samples, seed)
    sovereign_corpus = _replace_sovereign(corpus, terms)
    base_n, enc_name = _count_tokens(corpus)
    sov_n, _ = _count_tokens(sovereign_corpus)
    delta = (base_n - sov_n) / base_n if base_n else 0.0

    doc: dict[str, Any] = {
        "schema": SCHEMA,
        "hypothesis_tier": "B",
        "boundary_ack": True,
        "tokenizer": enc_name,
        "codebook_dir": str(codebook_dir).replace("\\", "/"),
        "terms_mapped": len(terms),
        "samples_lines": samples,
        "seed": seed,
        "baseline_token_count": base_n,
        "sovereign_token_count": sov_n,
        "delta_saving_ratio": round(delta, 6),
    }
    out_path = _ROOT / "docs" / "final" / "artifacts" / "derived" / "spike_sovereign_token_saving_latest.json"
    if not stdout_only:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(str(out_path))
    return doc


def main() -> int:
    ap = argparse.ArgumentParser(description="Sovereign token-saving spike (B-track)")
    ap.add_argument("--codebook-dir", type=Path, default=DEFAULT_CODEBOOK_DIR)
    ap.add_argument("--samples", type=int, default=80)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--stdout-only", action="store_true")
    args = ap.parse_args()
    doc = run_spike(
        codebook_dir=args.codebook_dir,
        samples=max(1, args.samples),
        seed=args.seed,
        stdout_only=bool(args.stdout_only),
    )
    if args.stdout_only:
        print(json.dumps(doc, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
