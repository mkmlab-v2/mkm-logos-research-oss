#!/usr/bin/env python3
"""ACTIVE report promotion packet — Hangul curated 41687 re-eval vs frozen ACTIVE (FAIL-COMP-004)."""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.compression_profile_v1 import PROFILE_BENCH_SSOT  # noqa: E402

ACTIVE = ROOT / "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json"
CANDIDATE = (
    ROOT / "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_HANGUL_CURATED_CANDIDATE_V1.json"
)
LEXICON_SIGNOFF = ROOT / "docs/final/artifacts/hangul_curated_track_a_lexicon_promotion_signoff_v1_latest.json"
TRACK_A_PACKET = ROOT / "reports/hangul_curated_track_a_promotion_packet_v1_latest.json"
OUT = ROOT / "reports/hangul_curated_active_promotion_packet_v1_latest.json"

MIN_SAVING_FLOOR = 0.45
MIN_JACCARD_FLOOR = 0.87
MAX_JACCARD_DROP_VS_FROZEN_PP = 0.02


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rel(p: Path) -> str:
    return str(p.relative_to(ROOT)).replace("\\", "/")


def _metrics(report: dict[str, Any]) -> dict[str, Any]:
    m = report.get("compression_metrics") or {}
    return {
        "case_count": m.get("case_count"),
        "global_token_saving_rate": m.get("global_token_saving_rate"),
        "avg_reconstruction_fidelity_jaccard": m.get("avg_reconstruction_fidelity_jaccard"),
        "sensitive_violation_count": m.get("sensitive_violation_count"),
    }


def main() -> int:
    py = sys.executable
    rc = subprocess.call(
        [py, "scripts/build_hangul_curated_active_report_candidate_v1.py"],
        cwd=str(ROOT),
    )
    if rc != 0:
        print("ABORT: candidate build failed", file=sys.stderr)
        return rc

    if not ACTIVE.is_file() or not CANDIDATE.is_file():
        print("ABORT: missing ACTIVE or candidate", file=sys.stderr)
        return 1

    frozen = json.loads(ACTIVE.read_text(encoding="utf-8"))
    cand = json.loads(CANDIDATE.read_text(encoding="utf-8"))
    m_frozen = _metrics(frozen)
    m_cand = _metrics(cand)

    saving_f = float(m_frozen.get("global_token_saving_rate") or 0)
    saving_c = float(m_cand.get("global_token_saving_rate") or 0)
    j_frozen = float(m_frozen.get("avg_reconstruction_fidelity_jaccard") or 0)
    j_cand = float(m_cand.get("avg_reconstruction_fidelity_jaccard") or 0)
    delta_saving = saving_c - saving_f
    delta_j = j_cand - j_frozen

    lex_sig = json.loads(LEXICON_SIGNOFF.read_text(encoding="utf-8")) if LEXICON_SIGNOFF.is_file() else {}
    lex_ok = bool(lex_sig.get("approved"))
    violations_ok = int(m_cand.get("sensitive_violation_count") or 0) == int(
        m_frozen.get("sensitive_violation_count") or 0
    )
    floor_saving_ok = saving_c >= MIN_SAVING_FLOOR
    floor_j_ok = j_cand >= MIN_JACCARD_FLOOR
    drop_vs_frozen_ok = delta_j >= -MAX_JACCARD_DROP_VS_FROZEN_PP
    case_ok = int(m_cand.get("case_count") or 0) >= 40

    ta_packet = json.loads(TRACK_A_PACKET.read_text(encoding="utf-8")) if TRACK_A_PACKET.is_file() else {}
    lexicon_double_gate_ok = bool((ta_packet.get("promotion_gates") or {}).get("golden40_delta_jaccard_pass")) and bool(
        ta_packet.get("promotion_ready")
    )
    jaccard_gate_ok = drop_vs_frozen_ok or lexicon_double_gate_ok
    marginal_drop_pp = round(-delta_j * 100, 4) if delta_j < 0 else 0.0

    checks = {
        "lexicon_signoff_approved": lex_ok,
        "regression_min_saving_0_45": floor_saving_ok,
        "regression_min_jaccard_0_87": floor_j_ok,
        "jaccard_drop_vs_frozen_active_pp_max": -MAX_JACCARD_DROP_VS_FROZEN_PP,
        "jaccard_drop_vs_frozen_active_actual": delta_j,
        "jaccard_drop_vs_frozen_active_pass": drop_vs_frozen_ok,
        "lexicon_41658_to_41687_double_gate_pass": lexicon_double_gate_ok,
        "jaccard_gate_combined_pass": jaccard_gate_ok,
        "marginal_drop_vs_frozen_active_pp": marginal_drop_pp,
        "sensitive_violation_unchanged": violations_ok,
        "case_count_40": case_ok,
    }
    promotion_ready = (
        lex_ok
        and floor_saving_ok
        and floor_j_ok
        and jaccard_gate_ok
        and violations_ok
        and case_ok
    )

    frozen_headline = PROFILE_BENCH_SSOT.get("economy") or {}
    doc: dict[str, Any] = {
        "schema": "hangul_curated_active_promotion_packet_v1",
        "generated_at_utc": _utc(),
        "hypo_label": "[HYPO]",
        "promotion_scope": {
            "multilens_active_report_write": True,
            "lexicon_production_ssot_swap": False,
            "ms_paste_headline_auto_update": False,
            "central_frozen_headline_auto_update": False,
            "live_trading": False,
        },
        "evidence": {
            "frozen_active": _rel(ACTIVE),
            "candidate": _rel(CANDIDATE),
            "lexicon_signoff": _rel(LEXICON_SIGNOFF) if LEXICON_SIGNOFF.is_file() else None,
            "track_a_lexicon_packet": _rel(TRACK_A_PACKET) if TRACK_A_PACKET.is_file() else None,
        },
        "golden40_compare": {
            "frozen_active_on_disk": m_frozen,
            "candidate_41687_lexicon": m_cand,
            "delta": {
                "global_token_saving_rate": delta_saving,
                "avg_reconstruction_fidelity_jaccard": delta_j,
            },
        },
        "headline_reference": {
            "profile_bench_ssot_economy_frozen_external": {
                "saving": frozen_headline.get("headline_global_token_saving_rate"),
                "jaccard": frozen_headline.get("headline_jaccard"),
            },
            "note": (
                "ACTIVE swap updates bench artifact KPI on disk; MS/CENTRAL 47.5%/0.890 paste "
                "remains HOLD until separate MS lane sign-off (FAIL-COMP-004)."
            ),
        },
        "promotion_gates": checks,
        "promotion_ready": promotion_ready,
        "commander_checklist": [
            "Confirm lexicon 41687 already applied (H3).",
            "Confirm candidate built from frozen ACTIVE run_config + 41687 lexicon only.",
            "Confirm regression floors and jaccard drop vs frozen ACTIVE within 2pp.",
            "MS paste / 대외 headline: separate policy — not auto-updated by this apply.",
        ],
        "apply_command_after_signoff": "py scripts/apply_hangul_curated_active_report_signoff_v1.py",
        "forbidden": [
            "Claim Track A gate from repair-only or 392 harvest.",
            "Auto-update MS paste from ACTIVE swap alone.",
            "Enable hangul harness or denylist as production default without review.",
        ],
    }
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"wrote": str(OUT), "promotion_ready": promotion_ready}, ensure_ascii=False))
    return 0 if promotion_ready else 2


if __name__ == "__main__":
    raise SystemExit(main())
