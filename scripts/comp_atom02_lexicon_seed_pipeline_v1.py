#!/usr/bin/env python3
"""COMP-ATOM-02: extract bench-matching terms from full 41k lexicon → genesis codebook seed."""
from __future__ import annotations

import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PILOT = ROOT / "reports" / "constitution" / "btrack_pilot"
INPUT_V2 = ROOT / "docs" / "final" / "artifacts" / "MULTILENS_PERFORMANCE_EVAL_INPUT_V2.json"
LEXICON = PILOT / "master_codebook_lexicon_v1_41775_rows_latest.json"


def _bench_words(cases: list[dict]) -> set[str]:
    words: set[str] = set()
    for c in cases:
        text = str(c.get("raw_text", "")).lower()
        words |= set(re.findall(r"[a-z]{3,}", text))
    return words


def main() -> int:
    if not LEXICON.is_file():
        print(f"ABORT: missing {LEXICON}")
        return 1

    inp = json.loads(INPUT_V2.read_text(encoding="utf-8"))
    cases = inp.get("compression_cases") or []
    bench_words = _bench_words(cases)

    lex = json.loads(LEXICON.read_text(encoding="utf-8"))
    entries = lex.get("entries") or []
    matched_terms: list[str] = []
    seen: set[str] = set()
    for ent in entries:
        if not isinstance(ent, dict):
            continue
        nf = str(ent.get("normalized_form") or "").strip().lower()
        if len(nf) < 3 or not nf.isascii():
            continue
        if nf in bench_words and nf not in seen:
            seen.add(nf)
            matched_terms.append(nf)

    ko = [
        "폭락", "금화교역", "태양인", "변동성", "레짐", "유동성", "붕괴", "회복",
        "리스크", "방어",
    ]
    terms: list[str] = list(ko)
    term_seen: set[str] = set(ko)
    for t in sorted(matched_terms):
        if t not in term_seen:
            term_seen.add(t)
            terms.append(t)

    terms_path = PILOT / "comp_atom02_lexicon_seed_terms_v1.json"
    codebook_path = PILOT / "genesis_gematria_4d_codebook_lexicon_seed_v1.json"
    terms_path.write_text(json.dumps(terms, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "build_genesis_gematria_4d_codebook_v1.py"),
            "--terms-json",
            str(terms_path),
            "--out",
            str(codebook_path),
        ],
        check=True,
        cwd=str(ROOT),
    )

    texts = [str(c.get("raw_text", "")) for c in cases if c.get("raw_text")]
    inputs_path = PILOT / "comp_atom02_router_inputs_full40_v1.json"
    inputs_path.write_text(json.dumps(texts, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    shadow_cfg = ROOT / "reports" / "constitution" / "btrack_pilot" / "genesis_pointer_runtime_shadow_only_v1.json"
    base = json.loads(
        (ROOT / "docs/final/artifacts/genesis_pointer_route_runtime_config_latest.json").read_text(
            encoding="utf-8"
        )
    )
    base["routing"] = {
        **base.get("routing", {}),
        "decision": "SHADOW_POINTER_ROUTE",
        "route_mode": "pointer_shadow",
        "pointer_enabled": False,
        "pointer_shadow": True,
        "track_a_primary": False,
    }
    base["generated_at_utc"] = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    base["research_only"] = True
    base["note"] = "COMP-ATOM-02 shadow-only probe; does not overwrite artifacts genesis_pointer_route_runtime_config_latest.json"
    shadow_cfg.write_text(json.dumps(base, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    router_out = PILOT / "comp_atom02_pointer_router_lexicon_shadow_v1.json"
    subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/pointer_hash_snapping_router_v1.py"),
            "--runtime-config",
            str(shadow_cfg),
            "--codebook-json",
            str(codebook_path),
            "--inputs-json",
            str(inputs_path),
            "--enable-snap",
            "--target-path",
            "reports/constitution/btrack_pilot/comp_atom02_pointer_router_lexicon_shadow_v1.json",
            "--out",
            str(router_out),
        ],
        check=True,
        cwd=str(ROOT),
    )

    doc = json.loads(router_out.read_text(encoding="utf-8"))
    rows = doc.get("rows") or []
    ok_rows = sum(1 for r in rows if r.get("pointer_candidate_ok"))
    shadow_meta = sum(1 for r in rows if r.get("effective_route_mode") == "pointer_shadow")

    summary = {
        "schema": "comp_atom02_lexicon_seed_run_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "research_only": True,
        "lexicon_entries_total": len(entries),
        "bench_token_count": len(bench_words),
        "matched_lexicon_terms": len(matched_terms),
        "codebook_term_count": len(terms),
        "case_count": len(texts),
        "codebook": str(codebook_path.relative_to(ROOT)).replace("\\", "/"),
        "runtime_shadow_config": str(shadow_cfg.relative_to(ROOT)).replace("\\", "/"),
        "router_summary": doc.get("summary"),
        "pointer_candidate_ok_count": ok_rows,
        "effective_pointer_shadow_count": shadow_meta,
    }
    out_path = PILOT / "comp_atom02_lexicon_seed_run_v1.json"
    out_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
