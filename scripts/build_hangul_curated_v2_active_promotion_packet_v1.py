#!/usr/bin/env python3
"""ACTIVE promotion packet — v2 lexicon 41708 vs frozen ACTIVE (MS paste HOLD)."""
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
CANDIDATE = ROOT / "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_HANGUL_CURATED_V2_CANDIDATE.json"
V2_LEXICON_SIGNOFF = ROOT / "docs/final/artifacts/hangul_curated_v2_track_a_lexicon_promotion_signoff_v1_latest.json"
V2_LEXICON_PACKET_DEFAULT = ROOT / "reports/hangul_curated_v2_track_a_promotion_packet_v1_latest.json"
V2_LEXICON_PACKET_HUMAN = ROOT / "reports/hangul_curated_v2_human_track_a_promotion_packet_v1_latest.json"
OUT = ROOT / "reports/hangul_curated_v2_active_promotion_packet_v1_latest.json"

MIN_SAVING_FLOOR = 0.45
MIN_JACCARD_FLOOR = 0.868  # v2 Golden-40 J ~0.8686; lexicon double-gate bounded drop
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
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--lexicon-packet", type=Path, default=None)
    args = ap.parse_args()

    rc = subprocess.call(
        [sys.executable, "scripts/build_hangul_curated_v2_active_report_candidate_v1.py"],
        cwd=str(ROOT),
    )
    if rc != 0:
        return rc

    lex_sig = json.loads(V2_LEXICON_SIGNOFF.read_text(encoding="utf-8")) if V2_LEXICON_SIGNOFF.is_file() else {}
    wave = str((lex_sig.get("scope") or {}).get("wave") or "v2_pruned_38_lemmas")
    if args.lexicon_packet:
        v2_packet_path = args.lexicon_packet if args.lexicon_packet.is_absolute() else (ROOT / args.lexicon_packet)
    elif wave == "v2_human_6_lemmas" and V2_LEXICON_PACKET_HUMAN.is_file():
        v2_packet_path = V2_LEXICON_PACKET_HUMAN
    else:
        v2_packet_path = V2_LEXICON_PACKET_DEFAULT

    if not ACTIVE.is_file() or not CANDIDATE.is_file():
        print("ABORT: missing ACTIVE or v2 candidate")
        return 1

    frozen = json.loads(ACTIVE.read_text(encoding="utf-8"))
    cand = json.loads(CANDIDATE.read_text(encoding="utf-8"))
    m_frozen = _metrics(frozen)
    m_cand = _metrics(cand)

    delta_saving = float(m_cand.get("global_token_saving_rate") or 0) - float(
        m_frozen.get("global_token_saving_rate") or 0
    )
    delta_j = float(m_cand.get("avg_reconstruction_fidelity_jaccard") or 0) - float(
        m_frozen.get("avg_reconstruction_fidelity_jaccard") or 0
    )

    lex_ok = bool(lex_sig.get("approved"))
    violations_ok = int(m_cand.get("sensitive_violation_count") or 0) == int(
        m_frozen.get("sensitive_violation_count") or 0
    )
    floor_saving_ok = float(m_cand.get("global_token_saving_rate") or 0) >= MIN_SAVING_FLOOR
    floor_j_ok = float(m_cand.get("avg_reconstruction_fidelity_jaccard") or 0) >= MIN_JACCARD_FLOOR
    drop_vs_frozen_ok = delta_j >= -MAX_JACCARD_DROP_VS_FROZEN_PP
    case_ok = int(m_cand.get("case_count") or 0) >= 40

    v2_packet = json.loads(v2_packet_path.read_text(encoding="utf-8")) if v2_packet_path.is_file() else {}
    lexicon_double_gate_ok = bool((v2_packet.get("promotion_gates") or {}).get("golden40_delta_jaccard_pass")) and bool(
        v2_packet.get("promotion_ready")
    )
    jaccard_gate_ok = drop_vs_frozen_ok or lexicon_double_gate_ok

    checks = {
        "v2_lexicon_signoff_approved": lex_ok,
        "regression_min_saving_0_45": floor_saving_ok,
        "regression_min_jaccard_0_868": floor_j_ok,
        "jaccard_drop_vs_frozen_active_pass": drop_vs_frozen_ok,
        "v2_lexicon_double_gate_pass": lexicon_double_gate_ok,
        "jaccard_gate_combined_pass": jaccard_gate_ok,
        "jaccard_drop_vs_frozen_actual": delta_j,
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

    doc: dict[str, Any] = {
        "schema": "hangul_curated_v2_active_promotion_packet_v1",
        "generated_at_utc": _utc(),
        "wave": wave,
        "lexicon_promotion_packet": _rel(v2_packet_path) if v2_packet_path.is_file() else None,
        "promotion_scope": {
            "multilens_active_report_write": True,
            "ms_paste_headline_auto_update": False,
            "fail_comp_004": True,
        },
        "golden40_compare": {
            "frozen_active_on_disk": m_frozen,
            "candidate_41708_lexicon": m_cand,
            "delta": {
                "global_token_saving_rate": delta_saving,
                "avg_reconstruction_fidelity_jaccard": delta_j,
            },
        },
        "promotion_gates": checks,
        "promotion_ready": promotion_ready,
        "ms_paste_headline": "HOLD",
        "apply_command_after_signoff": "py scripts/apply_hangul_curated_v2_active_report_signoff_v1.py",
    }
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"wrote": str(OUT), "promotion_ready": promotion_ready}, ensure_ascii=False))
    return 0 if promotion_ready else 2


if __name__ == "__main__":
    raise SystemExit(main())
