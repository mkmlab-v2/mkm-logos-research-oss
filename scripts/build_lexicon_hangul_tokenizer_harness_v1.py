#!/usr/bin/env python3
"""B-track [HYPO] Hangul lexicon tokenizer harness — cmp2_011–040 acceptance report."""
from __future__ import annotations

import json
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.core.hangul_lexicon_tokenizer_harness_v1 import (  # noqa: E402
    hangul_harness_token_set,
    zone_c_hangul_overlay_forms,
)
from scripts.core.master_codebook_lexicon_v1_bridge import (  # noqa: E402
    lexicon_hits_for_text,
    resolve_latest_codebook_path,
    unicode_word_tokens,
)

INPUT_V2 = ROOT / "docs/final/artifacts/MULTILENS_PERFORMANCE_EVAL_INPUT_V2.json"
AUDIT = ROOT / "reports/lexicon_lookup_exception_audit_v1_latest.json"
OUT = ROOT / "reports/lexicon_hangul_tokenizer_harness_v1_latest.json"
HANGUL_CASE_IDS = {f"cmp2_{i:03d}" for i in range(11, 41)}
_HANGUL_RE = re.compile(r"[\uac00-\ud7a3]")


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _hangul_ratio(raw: str) -> float:
    if not raw:
        return 0.0
    return round(len(_HANGUL_RE.findall(raw)) / max(len(raw), 1), 4)


def _lexicon_corpus_facts(cb: Path) -> dict:
    doc = json.loads(cb.read_text(encoding="utf-8"))
    lang_c: Counter[str] = Counter()
    ko_forms = 0
    for ent in doc.get("entries") or []:
        if not isinstance(ent, dict):
            continue
        lang_c[str(ent.get("lang") or "unknown")] += 1
        nf = ent.get("normalized_form")
        if isinstance(nf, str) and _HANGUL_RE.search(nf):
            ko_forms += 1
    return {
        "schema": doc.get("schema"),
        "row_count": doc.get("row_count") or len(doc.get("entries") or []),
        "normalized_form_hangul_count": ko_forms,
        "lang_distribution": dict(lang_c.most_common(8)),
    }


def _mode_hits(raw: str, cb: Path, **kwargs: object) -> tuple[int, set[str]]:
    hits, _ = lexicon_hits_for_text(raw, cb, min_token_len=2, **kwargs)
    return len(hits), hits


def _zone_c_policy_overlap(raw: str) -> tuple[int, set[str]]:
    """zone_c_hangul terms present in raw (policy/routing SSOT, not 41k lexicon)."""
    overlay = zone_c_hangul_overlay_forms()
    exact = {o for o in overlay if o in raw}
    return len(exact), exact


def main() -> int:
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--lexicon-path",
        type=Path,
        default=None,
        help="Override lexicon JSON (e.g. hangul_bench_overlay); default=production 41658",
    )
    import sys

    args = ap.parse_args(sys.argv[1:] if __name__ == "__main__" else [])

    if not INPUT_V2.is_file():
        print(f"ABORT: missing {INPUT_V2}")
        return 1
    if args.lexicon_path is not None:
        cb = args.lexicon_path if args.lexicon_path.is_absolute() else ROOT / args.lexicon_path
        if not cb.is_file():
            print(f"ABORT: lexicon missing {cb}")
            return 1
    else:
        cb = resolve_latest_codebook_path()
        if cb is None:
            print("ABORT: lexicon missing")
            return 1

    src = json.loads(INPUT_V2.read_text(encoding="utf-8"))
    cases = [c for c in (src.get("compression_cases") or []) if str(c.get("id")) in HANGUL_CASE_IDS]
    corpus = _lexicon_corpus_facts(cb)
    overlay_n = len(zone_c_hangul_overlay_forms())

    per_case = []
    for c in cases:
        cid = str(c.get("id", ""))
        raw = str(c.get("raw_text", ""))
        d_n, d_h = _mode_hits(raw, cb)
        h_n, h_h = _mode_hits(raw, cb, include_hangul_tokenizer_harness=True)
        pol_n, pol_h = _zone_c_policy_overlap(raw)
        harness_only = hangul_harness_token_set(raw)
        per_case.append(
            {
                "id": cid,
                "hangul_char_ratio": _hangul_ratio(raw),
                "modes": {
                    "bridge_default": {"hit_count": d_n, "hits_sample": sorted(d_h)[:8]},
                    "hangul_harness_v1": {
                        "hit_count": h_n,
                        "delta_vs_default": h_n - d_n,
                        "hits_sample": sorted(h_h)[:8],
                        "harness_token_count": len(harness_only),
                    },
                    "zone_c_policy_term_overlap": {
                        "match_count": pol_n,
                        "delta_vs_default_hits": pol_n - d_n,
                        "matched_terms_sample": sorted(pol_h)[:12],
                        "note": "zone_c_hangul must_keep/routing [HYPO]; not 41k lexicon intersection",
                    },
                },
            }
        )

    lift_default = sum(1 for r in per_case if r["modes"]["hangul_harness_v1"]["delta_vs_default"] > 0)
    lift_policy = sum(
        1 for r in per_case if r["modes"]["zone_c_policy_term_overlap"]["match_count"] > 0
    )
    total_default = sum(r["modes"]["bridge_default"]["hit_count"] for r in per_case)
    total_harness = sum(r["modes"]["hangul_harness_v1"]["hit_count"] for r in per_case)
    total_policy = sum(r["modes"]["zone_c_policy_term_overlap"]["match_count"] for r in per_case)

    acceptance = {
        "target_cases": "cmp2_011–cmp2_040",
        "hit_lift_on_production_41k_lexicon": total_harness > total_default,
        "cases_with_harness_lift_gt_0": lift_default,
        "zone_c_policy_term_matches_gt_0": total_policy > 0,
        "cases_with_zone_c_policy_match": lift_policy,
        "production_lexicon_has_ko_forms": corpus["normalized_form_hangul_count"] > 0,
    }

    if corpus["normalized_form_hangul_count"] == 0:
        verdict = (
            "Tokenizer harness wired; production 41k has zero Hangul normalized_form — "
            "P0 requires ko lexicon ingest or alias map, not bigram/CJK alone. "
            "zone_c policy-term overlap shows routing path only [HYPO]; not 41k lexicon hits."
        )
    elif not acceptance["hit_lift_on_production_41k_lexicon"]:
        verdict = "Harness tokens did not lift hits — refine stem/syllable policy or lexicon forms."
    else:
        verdict = "Harness lift on production lexicon — human review before bridge default change."

    doc = {
        "schema": "lexicon_hangul_tokenizer_harness_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "track_a_active_write": False,
        "hypo_label": "[HYPO]",
        "bridge_module": "scripts/core/hangul_lexicon_tokenizer_harness_v1.py",
        "lexicon_path": str(cb.relative_to(ROOT)).replace("\\", "/"),
        "bench_input": str(INPUT_V2.relative_to(ROOT)).replace("\\", "/"),
        "zone_c_overlay_pointer": "codebook/shards/zone_c_hangul.json",
        "zone_c_overlay_form_count": overlay_n,
        "lexicon_corpus_fact": corpus,
        "hangul_case_count": len(per_case),
        "aggregate": {
            "total_hits_bridge_default": total_default,
            "total_hits_hangul_harness_v1": total_harness,
            "total_zone_c_policy_term_matches": total_policy,
            "cases_harness_lift_gt_0": lift_default,
            "cases_zone_c_policy_match_gt_0": lift_policy,
        },
        "acceptance_gate": acceptance,
        "per_case": per_case,
        "verdict": {
            "promote_to_track_a": False,
            "promote_bridge_default": False,
            "recommendation": verdict,
        },
        "dod_p0_next": [
            "Ingest Hangul normalized_form rows into master_codebook_lexicon export (or alias table)",
            "Re-run harness; require hit_lift on production lexicon without zone_c overlay",
            "Optional: wire include_hangul_tokenizer_harness on evaluate_report after human sign-off",
        ],
    }
    if AUDIT.is_file():
        doc["audit_pointer"] = str(AUDIT.relative_to(ROOT)).replace("\\", "/")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "wrote": str(OUT),
                "ko_forms_in_lexicon": corpus["normalized_form_hangul_count"],
                "harness_lift_cases": lift_default,
                "policy_match_cases": lift_policy,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
