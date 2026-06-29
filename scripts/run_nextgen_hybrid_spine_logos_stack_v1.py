#!/usr/bin/env python3
"""[HYPO] Verbatim spine (byte exact) + Logos-boosted salience sidecar (NON_GATING)."""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.nextgen_archetype_prior_terms_v1 import load_prior_terms
from scripts.nextgen_latent_codec_v1 import WORD_RE, jaccard_text, token_salience
from scripts.nextgen_verbatim_spine_codec_v1 import (
    spine_packet_json_bytes,
    verbatim_spine_decode,
    verbatim_spine_encode,
)

BENCH = ROOT / "docs/final/artifacts/MULTILENS_PERFORMANCE_EVAL_INPUT_V2.json"
LOGOS_PACK = (
    ROOT / "docs/final/artifacts/logos_graphrag_bridge_evidence_pack_v1_latest.json"
)
SALIENCE_HOOK = (
    ROOT
    / "experiments/nextgen_clean_slate_cpu_v1/results/ng40_salience_hook_only.json"
)
NAV_FRAME = (
    ROOT / "experiments/nextgen_clean_slate_cpu_v1/ARCHETYPE_PRIOR_NAV_FRAME_V1.json"
)
OUT_DEFAULT = (
    ROOT
    / "experiments/nextgen_clean_slate_cpu_v1/results/ng40_hybrid_spine_logos_stack_v1_latest.json"
)

WORD_RE_LOCAL = WORD_RE


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_logos_terms(path: Path, max_terms: int) -> frozenset[str]:
    if not path.is_file():
        return frozenset()
    doc = json.loads(path.read_text(encoding="utf-8-sig"))
    terms: set[str] = set()
    for edge in doc.get("sample_edges") or doc.get("edges") or []:
        if isinstance(edge, dict):
            for k in ("src_term", "dst_term", "term", "label"):
                v = edge.get(k)
                if v:
                    terms.add(str(v).lower())
    for block in doc.get("bridge_terms") or []:
        if isinstance(block, str):
            terms.add(block.lower())
    # Fallback: scrape short keys from JSON text
    if len(terms) < 8:
        blob = path.read_text(encoding="utf-8")[:50000].lower()
        for m in re.findall(r'"term"\s*:\s*"([^"]{2,24})"', blob):
            terms.add(m.lower())
    return frozenset(list(terms)[:max_terms])


def _salience_reconstruct_logos(
    raw: str,
    keep_ratio: float,
    logos_terms: frozenset[str],
) -> tuple[str, str]:
    tokens = WORD_RE_LOCAL.findall(raw)
    if not tokens:
        return "", ""
    kr = max(0.05, min(0.98, keep_ratio))
    keep_n = max(1, int(round(len(tokens) * kr)))

    def score(i: int) -> float:
        tok = tokens[i]
        s = token_salience(tok)
        low = tok.lower()
        for lt in logos_terms:
            if lt in low or low in lt:
                s += 40.0
                break
        return (s, len(tok))

    ranked = sorted(range(len(tokens)), key=score, reverse=True)
    keep_idx = set(ranked[:keep_n])
    ordered = [tokens[i] for i in range(len(tokens)) if i in keep_idx]
    compressed = " ".join(ordered)
    return compressed, compressed


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--bench-input", type=Path, default=BENCH)
    ap.add_argument("--logos-pack", type=Path, default=LOGOS_PACK)
    ap.add_argument("--out-json", type=Path, default=OUT_DEFAULT)
    ap.add_argument("--keep-ratio", type=float, default=0.82)
    ap.add_argument("--max-logos-terms", type=int, default=128)
    ap.add_argument("--salience-hook-json", type=Path, default=SALIENCE_HOOK)
    ap.add_argument("--nav-frame-json", type=Path, default=NAV_FRAME)
    ap.add_argument(
        "--skip-logos-pack",
        action="store_true",
        help="Only archetype prior terms from hook + nav (no graphrag pack)",
    )
    args = ap.parse_args()

    cases = json.loads(args.bench_input.read_text(encoding="utf-8-sig")).get(
        "compression_cases"
    ) or []
    prior_terms, prior_meta = load_prior_terms(
        root=ROOT,
        salience_hook_path=args.salience_hook_json,
        nav_frame_path=args.nav_frame_json,
        logos_pack_path=None if args.skip_logos_pack else args.logos_pack,
        max_terms=args.max_logos_terms,
    )
    logos_terms = prior_terms if prior_terms else _load_logos_terms(
        args.logos_pack, args.max_logos_terms
    )
    wired_hook = bool(args.salience_hook_json.is_file())

    rows: list[dict[str, Any]] = []
    total_raw = total_spine = total_side = 0
    exact = 0
    j_spine = j_sem = 0.0

    for c in cases:
        raw = str(c.get("raw_text") or "")
        pkt = verbatim_spine_encode(raw)
        recon = verbatim_spine_decode(pkt)
        ok = raw == recon
        exact += int(ok)
        sem, _ = _salience_reconstruct_logos(raw, args.keep_ratio, logos_terms)
        sb = spine_packet_json_bytes(pkt)
        sc = len(sem.encode("utf-8"))
        rb = len(raw.encode("utf-8"))
        total_raw += rb
        total_spine += sb
        total_side += sc
        j_spine += jaccard_text(raw, recon)
        j_sem += jaccard_text(raw, sem)
        rows.append(
            {
                "id": c.get("id"),
                "byte_exact": ok,
                "logos_terms_loaded": len(logos_terms),
            }
        )

    n = len(rows)
    out = {
        "schema": "nextgen_hybrid_spine_logos_stack_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypo_label": "[HYPO]",
        "gating_policy": "NON_GATING",
        "track_a_active_write": False,
        "use_master_codebook_lexicon_v1": False,
        "keep_ratio": args.keep_ratio,
        "salience_hook_wired": wired_hook,
        "salience_hook": (
            str(args.salience_hook_json.relative_to(ROOT)).replace("\\", "/")
            if args.salience_hook_json.is_file()
            else None
        ),
        "nav_frame": (
            str(args.nav_frame_json.relative_to(ROOT)).replace("\\", "/")
            if args.nav_frame_json.is_file()
            else None
        ),
        "prior_terms_meta": prior_meta,
        "logos_pack": (
            str(args.logos_pack.relative_to(ROOT)).replace("\\", "/")
            if not args.skip_logos_pack and args.logos_pack.is_file()
            else None
        ),
        "logos_terms_count": len(logos_terms),
        "aggregate": {
            "case_count": n,
            "byte_exact_count": exact,
            "byte_exact_subset_parity": round(exact / n, 6) if n else 0.0,
            "global_token_saving_rate_spine_only": round(
                1.0 - (total_spine / max(1, total_raw)), 6
            ),
            "global_token_saving_rate_spine_plus_logos_sidecar": round(
                1.0 - ((total_spine + total_side) / max(1, total_raw)), 6
            ),
            "avg_reconstruction_fidelity_jaccard": round(j_spine / max(1, n), 6),
            "avg_logos_sidecar_jaccard": round(j_sem / max(1, n), 6),
        },
        "guardrails": [
            "Logos terms boost salience sidecar only; spine decode is SSOT for recon",
            "No cosine→probability; no Track A write",
        ],
        "stub_pointer": (
            "experiments/nextgen_clean_slate_cpu_v1/"
            "SYMBOLIC_ARCHETYPE_PREDICTIVE_INDEX_STUB_V1.json"
        ),
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(
        json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "wrote": str(args.out_json),
                "byte_exact_parity": out["aggregate"]["byte_exact_subset_parity"],
                "logos_terms": len(logos_terms),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
