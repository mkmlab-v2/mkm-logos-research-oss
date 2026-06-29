#!/usr/bin/env python3
"""Curated Hangul ingest pilot — double gate on overlay lexicon ([HYPO])."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.build_lexicon_hangul_tokenizer_harness_v1 import (  # noqa: E402
    HANGUL_CASE_IDS,
    _lexicon_corpus_facts,
)
from scripts.run_hangul_lexicon_overlay_pilot_v1 import _harness_slice  # noqa: E402
from scripts.build_master_codebook_golden40_lexicon_ab_v1 import (  # noqa: E402
    _load_signoff_relaxed,
    _metrics,
    _run_eval,
)
from scripts.build_master_codebook_hangul_curated_overlay_v1 import (  # noqa: E402
    DEFAULT_OUT as CURATED_OVERLAY,
    build_from_manifest,
)
from scripts.build_hangul_lexicon_curated_lemma_manifest_v1 import (  # noqa: E402
    OUT as MANIFEST,
)
from scripts.run_ultra_compression_default import INPUT_V2  # noqa: E402

PILOT = ROOT / "reports/constitution/btrack_pilot"
DEFAULT_BASE = PILOT / "master_codebook_lexicon_v1_41658_rows_latest.json"
OUT = ROOT / "reports/lexicon_hangul_curated_pilot_v1_latest.json"
GATE1_MIN = 25
GATE2_MIN_DELTA_SAVING = -0.02


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--overlay-path",
        type=Path,
        default=CURATED_OVERLAY,
        help="Lexicon JSON to evaluate (default curated overlay).",
    )
    ap.add_argument(
        "--skip-rebuild-overlay",
        action="store_true",
        help="Do not rebuild overlay from manifest (use existing --overlay-path).",
    )
    ap.add_argument("--manifest", type=Path, default=MANIFEST)
    ap.add_argument(
        "--base-lexicon",
        type=Path,
        default=DEFAULT_BASE,
        help="Baseline lexicon for Golden-40 compare and harness prod slice (default 41658).",
    )
    ap.add_argument("--out-json", type=Path, default=OUT)
    args = ap.parse_args(sys.argv[1:] if __name__ == "__main__" else [])

    base_path = Path(args.base_lexicon)
    if not base_path.is_absolute():
        base_path = (ROOT / base_path).resolve()
    overlay_path = Path(args.overlay_path)
    if not overlay_path.is_absolute():
        overlay_path = (ROOT / overlay_path).resolve()
    if not base_path.is_file() or not INPUT_V2.is_file():
        print("ABORT: missing base or bench input")
        return 1

    manifest_path = Path(args.manifest)
    if not manifest_path.is_absolute():
        manifest_path = (ROOT / manifest_path).resolve()
    if args.skip_rebuild_overlay:
        if not overlay_path.is_file():
            print(f"ABORT: overlay missing {overlay_path}")
            return 1
        meta = json.loads(overlay_path.read_text(encoding="utf-8")).get("overlay_meta") or {}
        if not meta:
            meta = json.loads(overlay_path.read_text(encoding="utf-8")).get("export_candidate_meta") or {}
        meta = dict(meta)
        meta.setdefault("atom_ids_added_count", meta.get("ko_rows_merged") or meta.get("atom_ids_added_count"))
    else:
        if not manifest_path.is_file():
            print("ABORT: manifest missing for overlay rebuild")
            return 1
        meta = build_from_manifest(manifest_path, base_path, overlay_path)

    src = json.loads(INPUT_V2.read_text(encoding="utf-8"))
    hangul_cases = [c for c in (src.get("compression_cases") or []) if str(c.get("id")) in HANGUL_CASE_IDS]

    harness_prod = _harness_slice(base_path, hangul_cases)
    harness_cur = _harness_slice(overlay_path, hangul_cases)

    relaxed, allow, exclude = _load_signoff_relaxed()
    m_base = _metrics(
        _run_eval(src, lexicon_path=base_path, domain_relaxed=relaxed, relaxed_case_allowlist=allow, relaxed_case_exclude=exclude)
    )
    m_cur = _metrics(
        _run_eval(
            src,
            lexicon_path=overlay_path,
            domain_relaxed=relaxed,
            relaxed_case_allowlist=allow,
            relaxed_case_exclude=exclude,
        )
    )
    delta_saving = (m_cur.get("global_token_saving_rate") or 0) - (m_base.get("global_token_saving_rate") or 0)

    cases_with_hit = sum(
        1 for r in harness_cur["per_case"] if r["modes"]["hangul_harness_v1"]["hit_count"] > 0
    )
    gate1_ok = cases_with_hit >= GATE1_MIN
    gate2_ok = delta_saving >= GATE2_MIN_DELTA_SAVING

    doc = {
        "schema": "lexicon_hangul_curated_pilot_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "track_a_active_write": False,
        "hypo_label": "[HYPO]",
        "manifest_path": str(Path(args.manifest).resolve().relative_to(ROOT.resolve())).replace("\\", "/"),
        "base_lexicon_path": str(base_path.relative_to(ROOT)).replace("\\", "/"),
        "overlay_path": str(overlay_path.relative_to(ROOT)).replace("\\", "/"),
        "overlay_meta": meta,
        "lexicon_corpus_fact_curated": _lexicon_corpus_facts(overlay_path),
        "harness_cmp2_011_040": {
            "baseline_lexicon": harness_prod,
            "curated_overlay": harness_cur,
        },
        "golden40_compare": {
            "baseline_lexicon": m_base,
            "curated_overlay": m_cur,
            "delta": {
                "global_token_saving_rate": delta_saving,
                "avg_reconstruction_fidelity_jaccard": (m_cur.get("avg_reconstruction_fidelity_jaccard") or 0)
                - (m_base.get("avg_reconstruction_fidelity_jaccard") or 0),
            },
        },
        "double_gate": {
            "gate1_cases_with_hit_gt_0_min": GATE1_MIN,
            "gate1_actual": cases_with_hit,
            "gate1_pass": gate1_ok,
            "gate2_delta_saving_pp_min": GATE2_MIN_DELTA_SAVING,
            "gate2_actual_delta_saving": delta_saving,
            "gate2_pass": gate2_ok,
            "both_pass": gate1_ok and gate2_ok,
        },
        "verdict": {
            "promote_production_ssot": False,
            "promote_track_a": False,
            "recommendation": "",
        },
    }
    if doc["double_gate"]["both_pass"]:
        doc["verdict"]["recommendation"] = (
            "Curated overlay passes both gates — human review before production ingest pipeline."
        )
    elif gate1_ok and not gate2_ok:
        doc["verdict"]["recommendation"] = "Shrink lemma set or tighten tiers — saving leak despite lookup lift."
    else:
        doc["verdict"]["recommendation"] = "Expand curated lemmas (within cap 50) or refine harness stems."

    out_path = Path(args.out_json)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "wrote": str(out_path),
                "gate1": gate1_ok,
                "gate2": gate2_ok,
                "added_ko": meta["atom_ids_added_count"],
            },
            ensure_ascii=False,
        )
    )
    return 0 if doc["double_gate"]["both_pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
