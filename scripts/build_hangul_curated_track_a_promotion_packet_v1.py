#!/usr/bin/env python3
"""Track A lexicon-only promotion packet — Hangul curated export candidate (FAIL-COMP-004)."""
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
from scripts.compression_profile_v1 import PROFILE_BENCH_SSOT  # noqa: E402
from scripts.run_ultra_compression_default import INPUT_V2  # noqa: E402

PILOT_DIR = ROOT / "reports/constitution/btrack_pilot"
BASE = PILOT_DIR / "master_codebook_lexicon_v1_41658_rows_latest.json"
CANDIDATE = PILOT_DIR / "master_codebook_lexicon_v1_41687_hangul_curated_export_candidate_v1.json"
ACTIVE = ROOT / "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json"
OUT = ROOT / "reports/hangul_curated_track_a_promotion_packet_v1_latest.json"

EXPORT_SIGNOFF = ROOT / "reports/hangul_lexicon_export_merge_signoff_v1_latest.json"
CURATED_PILOT = ROOT / "reports/lexicon_hangul_curated_pilot_v1_latest.json"
POINTER = PILOT_DIR / "master_codebook_bench_lexicon_pointer_v1_latest.json"

GATE2_MIN_DELTA_SAVING = -0.02
GATE2_MIN_DELTA_JACCARD = -0.02


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rel(p: Path) -> str:
    return str(p.relative_to(ROOT)).replace("\\", "/")


def main() -> int:
    missing = [p for p in (BASE, CANDIDATE, INPUT_V2, CURATED_PILOT) if not p.is_file()]
    if missing:
        print("ABORT: missing", [str(m) for m in missing])
        return 1

    export_sig = json.loads(EXPORT_SIGNOFF.read_text(encoding="utf-8")) if EXPORT_SIGNOFF.is_file() else {}
    pilot = json.loads(CURATED_PILOT.read_text(encoding="utf-8"))
    pointer = json.loads(POINTER.read_text(encoding="utf-8")) if POINTER.is_file() else {}

    src = json.loads(INPUT_V2.read_text(encoding="utf-8"))
    relaxed, allow, exclude = _load_signoff_relaxed()
    m_base = _metrics(_run_eval(src, lexicon_path=BASE, domain_relaxed=relaxed, relaxed_case_allowlist=allow, relaxed_case_exclude=exclude))
    m_cand = _metrics(_run_eval(src, lexicon_path=CANDIDATE, domain_relaxed=relaxed, relaxed_case_allowlist=allow, relaxed_case_exclude=exclude))
    delta_saving = (m_cand.get("global_token_saving_rate") or 0) - (m_base.get("global_token_saving_rate") or 0)
    delta_j = (m_cand.get("avg_reconstruction_fidelity_jaccard") or 0) - (
        m_base.get("avg_reconstruction_fidelity_jaccard") or 0
    )

    frozen = PROFILE_BENCH_SSOT["economy"]
    active_m = _metrics(json.loads(ACTIVE.read_text(encoding="utf-8"))) if ACTIVE.is_file() else None

    both_pass = bool((pilot.get("double_gate") or {}).get("both_pass"))
    export_ok = bool(export_sig.get("approved"))
    gate_saving_ok = delta_saving >= GATE2_MIN_DELTA_SAVING
    gate_j_ok = delta_j >= GATE2_MIN_DELTA_JACCARD
    violations_ok = int(m_cand.get("sensitive_violation_count") or 0) == int(m_base.get("sensitive_violation_count") or 0)

    checks = {
        "export_merge_signoff_approved": export_ok,
        "curated_pilot_both_pass": both_pass,
        "golden40_delta_saving_pp_min": GATE2_MIN_DELTA_SAVING,
        "golden40_delta_saving_actual": delta_saving,
        "golden40_delta_saving_pass": gate_saving_ok,
        "golden40_delta_jaccard_pp_min": GATE2_MIN_DELTA_JACCARD,
        "golden40_delta_jaccard_actual": delta_j,
        "golden40_delta_jaccard_pass": gate_j_ok,
        "sensitive_violation_unchanged": violations_ok,
    }
    promotion_ready = export_ok and both_pass and gate_saving_ok and gate_j_ok and violations_ok

    doc: dict[str, Any] = {
        "schema": "hangul_curated_track_a_promotion_packet_v1",
        "generated_at_utc": _utc(),
        "hypo_label": "[HYPO]",
        "promotion_scope": {
            "lexicon_production_ssot_swap": True,
            "multilens_active_report_write": False,
            "ms_paste_headline_auto_update": False,
            "live_trading": False,
            "bridge_default_hangul_harness": False,
            "function_word_denylist_default_on": False,
        },
        "evidence": {
            "export_merge_signoff": _rel(EXPORT_SIGNOFF) if EXPORT_SIGNOFF.is_file() else None,
            "curated_pilot": _rel(CURATED_PILOT),
            "export_candidate": _rel(CANDIDATE),
            "current_production_lexicon": _rel(BASE),
            "pointer": _rel(POINTER) if POINTER.is_file() else None,
            "double_gate": pilot.get("double_gate"),
        },
        "golden40_compare": {
            "base_41658": m_base,
            "export_candidate_41687": m_cand,
            "delta": {
                "global_token_saving_rate": delta_saving,
                "avg_reconstruction_fidelity_jaccard": delta_j,
            },
        },
        "headline_reference": {
            "frozen_ms_external": pointer.get("frozen_ms_external_headline"),
            "profile_bench_ssot_economy": {
                "saving": frozen.get("headline_global_token_saving_rate"),
                "jaccard": frozen.get("headline_jaccard"),
            },
            "active_report_on_disk": active_m,
            "note": "Lexicon swap does not authorize ACTIVE or MS headline change without separate sign-off.",
        },
        "promotion_gates": checks,
        "promotion_ready": promotion_ready,
        "commander_checklist": [
            "Confirm curated 29 lemmas manifest (no 392 harvest).",
            "Confirm Golden-40 delta within −2pp saving and −2pp Jaccard.",
            "Confirm FAIL-COMP-004: ACTIVE report and MS paste remain HOLD.",
            "After sign-off: apply script copies candidate → 41687_rows_latest + pointer refresh only.",
        ],
        "apply_command_after_signoff": (
            "py scripts/apply_hangul_curated_production_lexicon_signoff_v1.py"
        ),
        "forbidden": [
            "Overwrite MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json from this packet.",
            "Claim Track A ~47.5%/0.890 from Hangul overlay alone.",
            "Enable include_hangul_tokenizer_harness as bridge default without separate review.",
        ],
    }
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"wrote": str(OUT), "promotion_ready": promotion_ready}, ensure_ascii=False))
    return 0 if promotion_ready else 2


if __name__ == "__main__":
    raise SystemExit(main())
