#!/usr/bin/env python3
"""Wave2 export prep packet — research only until commander signoff (no production apply)."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.build_master_codebook_golden40_lexicon_ab_v1 import (  # noqa: E402
    _load_signoff_relaxed,
    _metrics,
    _run_eval,
)
from scripts.run_ultra_compression_default import INPUT_V2  # noqa: E402

PILOT = ROOT / "reports/constitution/btrack_pilot"
BASE = PILOT / "master_codebook_lexicon_v1_41658_rows_latest.json"
PRODUCTION = PILOT / "master_codebook_lexicon_v1_41687_rows_latest.json"
OVERLAY_V2 = PILOT / "master_codebook_lexicon_v1_41658_hangul_curated_overlay_v2.json"
CANDIDATE_V2 = PILOT / "master_codebook_lexicon_v1_41708_hangul_curated_export_candidate_v2.json"
PILOT_V2 = ROOT / "reports/lexicon_hangul_curated_pilot_v2_latest.json"
OUT = ROOT / "reports/hangul_curated_v2_export_prep_packet_v1_latest.json"

GATE2_MIN_DELTA_SAVING = -0.02
GATE2_MIN_DELTA_JACCARD = -0.02


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rel(p: Path) -> str:
    return str(p.relative_to(ROOT)).replace("\\", "/")


def main() -> int:
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--manifest",
        type=Path,
        default=ROOT / "docs/final/artifacts/hangul_lexicon_curated_lemma_manifest_v2.json",
    )
    ap.add_argument("--overlay", type=Path, default=OVERLAY_V2)
    ap.add_argument("--candidate", type=Path, default=CANDIDATE_V2)
    ap.add_argument("--pilot-json", type=Path, default=PILOT_V2)
    ap.add_argument("--wave", type=str, default="v2_50_lemmas")
    ap.add_argument(
        "--base-lexicon",
        type=Path,
        default=BASE,
        help="Golden-40 baseline lexicon (default 41658; use 41708 for v2_human pilot).",
    )
    ap.add_argument(
        "--out",
        type=Path,
        default=OUT,
        help="Export prep packet JSON (default: hangul_curated_v2_export_prep_packet_v1_latest.json)",
    )
    args = ap.parse_args()

    manifest_path = args.manifest if args.manifest.is_absolute() else (ROOT / args.manifest)
    overlay_path = args.overlay if args.overlay.is_absolute() else (ROOT / args.overlay)
    candidate_path = args.candidate if args.candidate.is_absolute() else (ROOT / args.candidate)
    pilot_path = args.pilot_json if args.pilot_json.is_absolute() else (ROOT / args.pilot_json)
    base_path = args.base_lexicon if args.base_lexicon.is_absolute() else (ROOT / args.base_lexicon)
    base_path = base_path.resolve()
    out_path = args.out if args.out.is_absolute() else (ROOT / args.out)

    missing = [p for p in (base_path, candidate_path, INPUT_V2, pilot_path, overlay_path) if not p.is_file()]
    if missing:
        print("ABORT: missing", [str(m) for m in missing])
        return 1

    pilot = json.loads(pilot_path.read_text(encoding="utf-8"))
    src = json.loads(INPUT_V2.read_text(encoding="utf-8"))
    relaxed, allow, exclude = _load_signoff_relaxed()

    m_base = _metrics(
        _run_eval(
            src,
            lexicon_path=base_path,
            domain_relaxed=relaxed,
            relaxed_case_allowlist=allow,
            relaxed_case_exclude=exclude,
        )
    )
    m_prod = _metrics(
        _run_eval(
            src,
            lexicon_path=PRODUCTION,
            domain_relaxed=relaxed,
            relaxed_case_allowlist=allow,
            relaxed_case_exclude=exclude,
        )
    ) if PRODUCTION.is_file() else None
    m_cand = _metrics(
        _run_eval(
            src,
            lexicon_path=candidate_path,
            domain_relaxed=relaxed,
            relaxed_case_allowlist=allow,
            relaxed_case_exclude=exclude,
        )
    )

    delta_vs_base_saving = (m_cand.get("global_token_saving_rate") or 0) - (m_base.get("global_token_saving_rate") or 0)
    delta_vs_base_j = (m_cand.get("avg_reconstruction_fidelity_jaccard") or 0) - (
        m_base.get("avg_reconstruction_fidelity_jaccard") or 0
    )

    both_pass = bool((pilot.get("double_gate") or {}).get("both_pass"))
    gate_saving_ok = delta_vs_base_saving >= GATE2_MIN_DELTA_SAVING
    gate_j_ok = delta_vs_base_j >= GATE2_MIN_DELTA_JACCARD
    violations_ok = int(m_cand.get("sensitive_violation_count") or 0) == int(m_base.get("sensitive_violation_count") or 0)

    export_prep_ready = both_pass and gate_saving_ok and gate_j_ok and violations_ok

    doc: dict[str, Any] = {
        "schema": "hangul_curated_v2_export_prep_packet_v1",
        "generated_at_utc": _utc(),
        "hypo_label": "[HYPO]",
        "research_only": True,
        "wave": args.wave,
        "promotion_scope": {
            "lexicon_production_ssot_swap": False,
            "multilens_active_report_write": False,
            "ms_paste_headline_auto_update": False,
            "requires_commander_v2_export_signoff": True,
        },
        "evidence": {
            "manifest": _rel(manifest_path),
            "overlay": _rel(overlay_path),
            "pilot": _rel(pilot_path),
            "export_candidate": _rel(candidate_path),
            "production_lexicon_current": _rel(PRODUCTION) if PRODUCTION.is_file() else None,
        },
        "pilot_v2_double_gate": pilot.get("double_gate"),
        "golden40_candidate_vs_base": {
            "baseline_lexicon": str(base_path.relative_to(ROOT)).replace("\\", "/"),
            "delta_saving_pp": delta_vs_base_saving,
            "delta_jaccard_pp": delta_vs_base_j,
            "gate_pass": gate_saving_ok and gate_j_ok,
        },
        "metrics": {
            "baseline": m_base,
            "production_41687": m_prod,
            "export_candidate": m_cand,
        },
        "checks": {
            "pilot_v2_both_pass": both_pass,
            "golden40_delta_saving_pass": gate_saving_ok,
            "golden40_delta_jaccard_pass": gate_j_ok,
            "sensitive_violation_unchanged": violations_ok,
        },
        "export_prep_ready": export_prep_ready,
        "promotion_ready": False,
        "ms_paste_headline": "HOLD",
        "next_commands_after_commander_signoff": [
            "py scripts/record_hangul_lexicon_export_merge_signoff_v1.py --commander-export-merge-approve",
            "py scripts/build_hangul_curated_track_a_promotion_packet_v1.py (update paths to v2 candidate)",
            "py scripts/run_hangul_curated_track_a_promotion_preflight_chain_v1.py --commander-track-a-lexicon-approve",
        ],
        "forbidden_without_signoff": [
            "apply_hangul_curated_production_lexicon_signoff_v1",
            "apply_hangul_curated_active_report_signoff_v1",
            "MS/CENTRAL 47.5%/0.890 headline paste",
        ],
    }
    out_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"wrote": str(out_path), "export_prep_ready": export_prep_ready}, ensure_ascii=False))
    return 0 if export_prep_ready else 1


if __name__ == "__main__":
    raise SystemExit(main())
