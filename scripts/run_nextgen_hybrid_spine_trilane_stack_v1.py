#!/usr/bin/env python3
"""[HYPO] Verbatim spine + Logos + science/sasang salience sidecar (tri-lane, NON_GATING)."""
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

from scripts.nextgen_science_prior_terms_v1 import (
    DEFAULT_SPEC,
    load_science_prior_terms,
    load_trilane_prior_terms,
)
from scripts.nextgen_coordinator_science_loss_v1 import (
    partition_lens_terms,
    salience_boost_weights,
)
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
SCIENCE_SPEC = ROOT / DEFAULT_SPEC
OUT_DEFAULT = (
    ROOT
    / "experiments/nextgen_clean_slate_cpu_v1/results/ng40_hybrid_spine_trilane_stack_v1_latest.json"
)

WORD_RE_LOCAL = WORD_RE


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _boost_weights(spec: dict[str, Any]) -> tuple[float, float, float, float]:
    return salience_boost_weights(spec)


def _salience_reconstruct_trilane(
    raw: str,
    keep_ratio: float,
    logos_terms: frozenset[str],
    science_terms: frozenset[str],
    sasang_terms: frozenset[str],
    w_logos: float,
    w_science: float,
    w_sasang: float,
    myeongni_terms: frozenset[str] | None = None,
    w_myeongni: float = 18.0,
) -> tuple[str, str]:
    tokens = WORD_RE_LOCAL.findall(raw)
    if not tokens:
        return "", ""

    kr = max(0.05, min(0.98, keep_ratio))
    keep_n = max(1, int(round(len(tokens) * kr)))
    myeongni_terms = myeongni_terms or frozenset()

    def score(i: int) -> float:
        tok = tokens[i]
        s = token_salience(tok)
        low = tok.lower()
        for lt in logos_terms:
            if lt in low or low in lt:
                s += w_logos
                break
        for st in science_terms:
            if st in low or low in st:
                s += w_science
                break
        for st in sasang_terms:
            if st in low or low in st:
                s += w_sasang
                break
        for mt in myeongni_terms:
            if mt in low or low in mt:
                s += w_myeongni
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
    ap.add_argument("--science-spec", type=Path, default=SCIENCE_SPEC)
    ap.add_argument("--logos-pack", type=Path, default=LOGOS_PACK)
    ap.add_argument("--out-json", type=Path, default=OUT_DEFAULT)
    ap.add_argument("--keep-ratio", type=float, default=0.82)
    ap.add_argument("--salience-hook-json", type=Path, default=SALIENCE_HOOK)
    ap.add_argument("--nav-frame-json", type=Path, default=NAV_FRAME)
    ap.add_argument(
        "--skip-logos-pack",
        action="store_true",
        help="Archetype hook+nav only for logos lane",
    )
    ap.add_argument(
        "--science-only",
        action="store_true",
        help="Do not merge archetype/logos terms (science+sasang spec only)",
    )
    args = ap.parse_args()

    if not args.science_spec.is_file():
        print(json.dumps({"error": "missing_science_spec", "path": str(args.science_spec)}))
        return 2

    spec_doc = json.loads(args.science_spec.read_text(encoding="utf-8-sig"))
    w_logos, w_science, w_sasang, w_myeongni = _boost_weights(spec_doc)
    science_only_terms, _ = load_science_prior_terms(
        root=ROOT, spec_path=args.science_spec
    )

    if args.science_only:
        all_terms = science_only_terms
        prior_meta = {"science_only": True}
    else:
        all_terms, prior_meta = load_trilane_prior_terms(
            root=ROOT,
            spec_path=args.science_spec,
            salience_hook_path=args.salience_hook_json,
            nav_frame_path=args.nav_frame_json,
            logos_pack_path=None if args.skip_logos_pack else args.logos_pack,
            merge_archetype=True,
        )

    logos_t, science_t, sasang_t, myeongni_t = partition_lens_terms(
        all_terms, science_only_terms
    )

    cases = json.loads(args.bench_input.read_text(encoding="utf-8-sig")).get(
        "compression_cases"
    ) or []
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
        sem, _ = _salience_reconstruct_trilane(
            raw,
            args.keep_ratio,
            logos_t,
            science_t,
            sasang_t,
            w_logos,
            w_science,
            w_sasang,
            myeongni_t,
            w_myeongni,
        )
        sb = spine_packet_json_bytes(pkt)
        sc = len(sem.encode("utf-8"))
        rb = len(raw.encode("utf-8"))
        total_raw += rb
        total_spine += sb
        total_side += sc
        j_spine += jaccard_text(raw, recon)
        j_sem += jaccard_text(raw, sem)
        rows.append({"id": c.get("id"), "byte_exact": ok})

    n = len(rows)
    out = {
        "schema": "nextgen_hybrid_spine_trilane_stack_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypo_label": "[HYPO]",
        "gating_policy": "NON_GATING",
        "track_a_active_write": False,
        "use_master_codebook_lexicon_v1": False,
        "keep_ratio": args.keep_ratio,
        "science_spec": str(args.science_spec.relative_to(ROOT)).replace("\\", "/"),
        "salience_boost": {
            "logos_weight": w_logos,
            "science_weight": w_science,
            "sasang_weight": w_sasang,
            "myeongni_weight": w_myeongni,
        },
        "term_counts": {
            "combined": len(all_terms),
            "logos_lane": len(logos_t),
            "science_lane": len(science_t),
            "sasang_lane": len(sasang_t),
            "myeongni_lane": len(myeongni_t),
        },
        "prior_terms_meta": prior_meta,
        "aggregate": {
            "case_count": n,
            "byte_exact_count": exact,
            "byte_exact_subset_parity": round(exact / n, 6) if n else 0.0,
            "global_token_saving_rate_spine_only": round(
                1.0 - (total_spine / max(1, total_raw)), 6
            ),
            "global_token_saving_rate_spine_plus_trilane_sidecar": round(
                1.0 - ((total_spine + total_side) / max(1, total_raw)), 6
            ),
            "avg_reconstruction_fidelity_jaccard": round(j_spine / max(1, n), 6),
            "avg_trilane_sidecar_jaccard": round(j_sem / max(1, n), 6),
        },
        "guardrails": spec_doc.get("salience_contract", {}).get("forbidden", []),
        "stub_pointer": spec_doc.get("stub_pointer"),
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
                "combined_terms": len(all_terms),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
