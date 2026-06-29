#!/usr/bin/env python3
"""Build Hangul bench overlay + re-run harness; optional Golden-40 KPI compare ([HYPO])."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.build_lexicon_hangul_tokenizer_harness_v1 import (  # noqa: E402
    HANGUL_CASE_IDS,
    _hangul_ratio,
    _lexicon_corpus_facts,
    _mode_hits,
    _zone_c_policy_overlap,
)
from scripts.build_master_codebook_golden40_lexicon_ab_v1 import (  # noqa: E402
    _load_signoff_relaxed,
    _metrics,
    _run_eval,
)
from scripts.build_master_codebook_hangul_bench_overlay_v1 import (  # noqa: E402
    DEFAULT_OUT as OVERLAY_PATH,
    build_overlay,
    _collect_hangul_forms,
)
from scripts.core.hangul_lexicon_tokenizer_harness_v1 import hangul_harness_token_set  # noqa: E402
from scripts.run_ultra_compression_default import INPUT_V2  # noqa: E402

PILOT = ROOT / "reports" / "constitution" / "btrack_pilot"
BASE = PILOT / "master_codebook_lexicon_v1_41658_rows_latest.json"
OUT = ROOT / "reports/lexicon_hangul_overlay_pilot_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _harness_slice(cb: Path, cases: list[dict]) -> dict:
    per = []
    for c in cases:
        cid = str(c.get("id", ""))
        raw = str(c.get("raw_text", ""))
        d_n, d_h = _mode_hits(raw, cb)
        h_n, h_h = _mode_hits(raw, cb, include_hangul_tokenizer_harness=True)
        pol_n, _ = _zone_c_policy_overlap(raw)
        per.append(
            {
                "id": cid,
                "modes": {
                    "bridge_default": {"hit_count": d_n},
                    "hangul_harness_v1": {"hit_count": h_n, "delta_vs_default": h_n - d_n},
                    "zone_c_policy_term_overlap": {"match_count": pol_n},
                },
            }
        )
    lift = sum(1 for r in per if r["modes"]["hangul_harness_v1"]["delta_vs_default"] > 0)
    return {
        "hangul_case_count": len(per),
        "cases_harness_lift_gt_0": lift,
        "total_hits_default": sum(r["modes"]["bridge_default"]["hit_count"] for r in per),
        "total_hits_harness": sum(r["modes"]["hangul_harness_v1"]["hit_count"] for r in per),
        "per_case": per,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-golden40-compare", action="store_true")
    ap.add_argument("--overlay-out", type=Path, default=OVERLAY_PATH)
    args = ap.parse_args()

    if not BASE.is_file() or not INPUT_V2.is_file():
        print("ABORT: missing base lexicon or INPUT_V2")
        return 1

    overlay = args.overlay_out if args.overlay_out.is_absolute() else ROOT / args.overlay_out
    forms = _collect_hangul_forms()
    meta = build_overlay(BASE, forms, overlay)

    src = json.loads(INPUT_V2.read_text(encoding="utf-8"))
    hangul_cases = [c for c in (src.get("compression_cases") or []) if str(c.get("id")) in HANGUL_CASE_IDS]

    corpus_base = _lexicon_corpus_facts(BASE)
    corpus_ov = _lexicon_corpus_facts(overlay)

    doc: dict = {
        "schema": "lexicon_hangul_overlay_pilot_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "track_a_active_write": False,
        "hypo_label": "[HYPO]",
        "overlay_path": str(overlay.relative_to(ROOT)).replace("\\", "/"),
        "overlay_meta": meta,
        "lexicon_corpus_fact_base": corpus_base,
        "lexicon_corpus_fact_overlay": corpus_ov,
        "harness_cmp2_011_040": {
            "on_production_41658": _harness_slice(BASE, hangul_cases),
            "on_hangul_bench_overlay": _harness_slice(overlay, hangul_cases),
        },
        "acceptance": {
            "overlay_ko_form_count_gt_0": corpus_ov["normalized_form_hangul_count"] > 0,
            "harness_hit_lift_on_overlay": False,
        },
        "verdict": {"promote_to_track_a": False, "promote_production_ssot": False},
    }
    ov = doc["harness_cmp2_011_040"]["on_hangul_bench_overlay"]
    doc["acceptance"]["harness_hit_lift_on_overlay"] = ov["cases_harness_lift_gt_0"] > 0 or (
        ov["total_hits_harness"] > doc["harness_cmp2_011_040"]["on_production_41658"]["total_hits_default"]
    )

    if not args.skip_golden40_compare:
        relaxed, allow, exclude = _load_signoff_relaxed()
        m_base = _metrics(_run_eval(src, lexicon_path=BASE, domain_relaxed=relaxed, relaxed_case_allowlist=allow, relaxed_case_exclude=exclude))
        m_ov = _metrics(_run_eval(src, lexicon_path=overlay, domain_relaxed=relaxed, relaxed_case_allowlist=allow, relaxed_case_exclude=exclude))
        doc["golden40_compare"] = {
            "base_41658": m_base,
            "hangul_overlay": m_ov,
            "delta": {
                "global_token_saving_rate": (m_ov.get("global_token_saving_rate") or 0)
                - (m_base.get("global_token_saving_rate") or 0),
                "avg_reconstruction_fidelity_jaccard": (m_ov.get("avg_reconstruction_fidelity_jaccard") or 0)
                - (m_base.get("avg_reconstruction_fidelity_jaccard") or 0),
            },
            "note": "Golden-40 full bench; overlay is research-only — not ACTIVE",
        }

    if doc["acceptance"]["harness_hit_lift_on_overlay"]:
        doc["verdict"]["recommendation"] = (
            "Overlay proves lookup path; ingest ko rows into export pipeline after human review."
        )
    else:
        doc["verdict"]["recommendation"] = "Expand form harvest or tokenizer; overlay lift still insufficient."

    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "wrote": str(OUT),
                "ko_added": meta["atom_ids_added_count"],
                "harness_lift_cases": ov["cases_harness_lift_gt_0"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
