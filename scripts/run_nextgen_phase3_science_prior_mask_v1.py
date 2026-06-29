#!/usr/bin/env python3
"""[HYPO] Phase 3b: Logos+science+sasang tri-lane prior as NG-40 must_keep mask + byte_exact audit."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.nextgen_science_prior_terms_v1 import DEFAULT_SPEC, load_trilane_prior_terms
from scripts.run_nextgen_latent_indexer_eval_ng40_v1 import (
    ACTIVE,
    INPUT_V2,
    _beat,
    _frozen_active,
    evaluate_ng40_lane,
)

BEST_CAPS = (
    ROOT
    / "experiments/nextgen_clean_slate_cpu_v1/results/ng40_latent_eval_best_v1_latest.json"
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
    / "experiments/nextgen_clean_slate_cpu_v1/results/ng40_latent_eval_science_prior_mask_v1_latest.json"
)


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_best_caps(path: Path) -> tuple[float, float, float, bool]:
    doc = json.loads(path.read_text(encoding="utf-8-sig"))
    rc = doc.get("run_config_summary") or {}
    return (
        float(rc.get("general_max_saving_rate", 0.32)),
        float(rc.get("sensitive_max_saving_rate", 0.28)),
        float(rc.get("hangul_max_saving_rate", 0.55)),
        bool(rc.get("with_domain_relaxed", False)),
    )


def _byte_exact_audit(
    raw_by_id: dict[str, str], cases: list[dict[str, Any]]
) -> dict[str, Any]:
    exact = 0
    mismatches: list[dict[str, Any]] = []
    for row in cases:
        cid = str(row.get("id", ""))
        raw = raw_by_id.get(cid, "")
        rec = str(row.get("reconstructed_text_effective", ""))
        ok = raw == rec
        if ok:
            exact += 1
        else:
            mismatches.append({"id": cid, "raw_len": len(raw.encode("utf-8"))})
    n = len(cases)
    parity = (exact / n) if n else 0.0
    return {
        "case_count": n,
        "byte_exact_count": exact,
        "byte_exact_subset_parity": round(parity, 6),
        "parity_target_met": parity >= 1.0,
        "mismatch_count": len(mismatches),
        "mismatch_sample": mismatches[:8],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-json", type=Path, default=OUT_DEFAULT)
    ap.add_argument("--best-caps-json", type=Path, default=BEST_CAPS)
    ap.add_argument("--science-spec", type=Path, default=SCIENCE_SPEC)
    ap.add_argument("--salience-hook-json", type=Path, default=SALIENCE_HOOK)
    ap.add_argument("--nav-frame-json", type=Path, default=NAV_FRAME)
    ap.add_argument(
        "--science-only",
        action="store_true",
        help="Science+sasang spec tokens only (no archetype merge)",
    )
    args = ap.parse_args()

    if not INPUT_V2.is_file():
        print(json.dumps({"error": "missing_bench_input"}))
        return 2
    if not args.best_caps_json.is_file():
        print(json.dumps({"error": "missing_best_caps", "path": str(args.best_caps_json)}))
        return 2
    if not args.science_spec.is_file():
        print(json.dumps({"error": "missing_science_spec", "path": str(args.science_spec)}))
        return 2

    if args.science_only:
        from scripts.nextgen_science_prior_terms_v1 import load_science_prior_terms

        prior_terms, prior_meta = load_science_prior_terms(
            root=ROOT, spec_path=args.science_spec
        )
    else:
        prior_terms, prior_meta = load_trilane_prior_terms(
            root=ROOT,
            spec_path=args.science_spec,
            salience_hook_path=args.salience_hook_json,
            nav_frame_path=args.nav_frame_json,
            logos_pack_path=None,
            merge_archetype=True,
        )

    g, s, h, relaxed = _load_best_caps(args.best_caps_json)
    doc = json.loads(INPUT_V2.read_text(encoding="utf-8-sig"))
    raw_by_id = {
        str(c.get("id", "")): str(c.get("raw_text", ""))
        for c in (doc.get("compression_cases") or [])
    }

    agg, report = evaluate_ng40_lane(
        doc,
        bench_input=INPUT_V2,
        general_cap=g,
        sensitive_cap=s,
        hangul_cap=h,
        use_domain_relaxed=relaxed,
        use_master_codebook_lexicon_v1=False,
        active_track_parity=False,
        archetype_prior_must_keep=prior_terms,
    )
    cases = (report.get("compression_metrics") or {}).get("cases") or []
    byte_audit = _byte_exact_audit(raw_by_id, cases)
    frozen = _frozen_active()

    out = {
        "schema": "nextgen_latent_eval_science_prior_mask_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypo_label": "[HYPO]",
        "track_a_active_write": False,
        "phase": "phase_3b_science_trilane_prior_mask_v1",
        "lane": "ng40_latent_eval_no_41k_lexicon + trilane_prior_must_keep",
        "latent_codec_wired": False,
        "policy_mask_only": True,
        "science_only": bool(args.science_only),
        "prior_terms_count": len(prior_terms),
        "prior_terms_meta": prior_meta,
        "science_spec": str(args.science_spec.relative_to(ROOT)).replace("\\", "/"),
        "aggregate": agg,
        "byte_exact_subset": byte_audit,
        "frozen_baseline": frozen,
        "beat_check": _beat(agg, frozen),
        "run_config_summary": {
            "use_master_codebook_lexicon_v1": False,
            "apply_gematria_4d_bridge_policy": False,
            "trilane_prior_must_keep_sample": sorted(prior_terms)[:32],
        },
        "delta_vs_archetype_only_note_ko": (
            "Compare with ng40_latent_eval_archetype_prior_mask_v1_latest.json; "
            "promotion requires human sign-off + gates"
        ),
        "reporting": {
            "raw_primary": True,
            "repair_v2_operational_if_repair_layer": True,
            "never_collapse_headline": True,
        },
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(
        json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "wrote": str(args.out_json),
                "prior_terms": len(prior_terms),
                "saving": agg.get("global_token_saving_rate"),
                "jaccard": agg.get("avg_reconstruction_fidelity_jaccard"),
                "byte_exact_parity": byte_audit.get("byte_exact_subset_parity"),
                "beat_frozen": (out.get("beat_check") or {}).get("any_beat_frozen"),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
