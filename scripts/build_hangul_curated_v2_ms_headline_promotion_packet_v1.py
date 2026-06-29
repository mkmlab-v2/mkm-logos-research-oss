#!/usr/bin/env python3
"""MS/CENTRAL headline policy packet — v2 ACTIVE bench KPI (submission archive separate)."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
ACTIVE = ROOT / "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json"
V2_ACTIVE_SIGNOFF = ROOT / "docs/final/artifacts/hangul_curated_v2_active_promotion_signoff_v1_latest.json"
V2_LEXICON_SIGNOFF = ROOT / "docs/final/artifacts/hangul_curated_v2_track_a_lexicon_promotion_signoff_v1_latest.json"
HEADLINE_POLICY = ROOT / "reports/compression_track_a_headline_policy_v1_latest.json"
OUT = ROOT / "reports/hangul_curated_v2_ms_headline_promotion_packet_v1_latest.json"
P41708 = ROOT / "reports/constitution/btrack_pilot/master_codebook_lexicon_v1_41708_rows_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rel(p: Path) -> str:
    return str(p.relative_to(ROOT)).replace("\\", "/")


def _round_pct(rate: float) -> float:
    return round(rate * 100.0, 2)


def _metrics_from_active(doc: dict[str, Any]) -> dict[str, Any]:
    m = doc.get("compression_metrics") or {}
    saving = float(m.get("global_token_saving_rate") or 0)
    jaccard = float(m.get("avg_reconstruction_fidelity_jaccard") or 0)
    return {
        "case_count": m.get("case_count"),
        "global_token_saving_rate": saving,
        "global_token_saving_rate_pct": _round_pct(saving),
        "avg_reconstruction_fidelity_jaccard": jaccard,
        "avg_reconstruction_fidelity_jaccard_rounded": round(jaccard, 3),
        "sensitive_violation_count": m.get("sensitive_violation_count"),
    }


def main() -> int:
    if not ACTIVE.is_file():
        print("ABORT: ACTIVE report missing")
        return 1

    active_sig = (
        json.loads(V2_ACTIVE_SIGNOFF.read_text(encoding="utf-8")) if V2_ACTIVE_SIGNOFF.is_file() else {}
    )
    lex_sig = json.loads(V2_LEXICON_SIGNOFF.read_text(encoding="utf-8")) if V2_LEXICON_SIGNOFF.is_file() else {}

    prior: dict[str, Any] = {
        "global_token_saving_rate": 0.47538677918424754,
        "global_token_saving_rate_pct": 47.54,
        "avg_reconstruction_fidelity_jaccard": 0.8904921794966301,
        "note": "MS submission archive (HWPX) — unchanged on disk",
    }
    ms_submission_archive = dict(prior)
    policy_lane_prior: dict[str, Any] | None = None
    if HEADLINE_POLICY.is_file():
        hp = json.loads(HEADLINE_POLICY.read_text(encoding="utf-8"))
        archive = hp.get("ms_submission_archive")
        if isinstance(archive, dict):
            ms_submission_archive = {
                "global_token_saving_rate": float(
                    archive.get("global_token_saving_rate") or ms_submission_archive["global_token_saving_rate"]
                ),
                "global_token_saving_rate_pct": archive.get("global_token_saving_rate_pct")
                or _round_pct(float(ms_submission_archive["global_token_saving_rate"])),
                "avg_reconstruction_fidelity_jaccard": float(
                    archive.get("avg_reconstruction_fidelity_jaccard")
                    or ms_submission_archive["avg_reconstruction_fidelity_jaccard"]
                ),
                "note": archive.get("note") or ms_submission_archive.get("note"),
            }
            prior = dict(ms_submission_archive)
        frozen = hp.get("frozen_headline_prior")
        if isinstance(frozen, dict):
            policy_lane_prior = {
                "global_token_saving_rate": float(
                    frozen.get("global_token_saving_rate") or 0
                ),
                "global_token_saving_rate_pct": frozen.get("global_token_saving_rate_pct")
                or _round_pct(float(frozen.get("global_token_saving_rate") or 0)),
                "avg_reconstruction_fidelity_jaccard": float(
                    frozen.get("avg_reconstruction_fidelity_jaccard") or 0
                ),
                "note": frozen.get("note") or "MS lane policy prior (internal paste)",
            }

    active_doc = json.loads(ACTIVE.read_text(encoding="utf-8"))
    proposed = _metrics_from_active(active_doc)

    delta_saving_pp = round(
        (proposed["global_token_saving_rate"] - float(prior["global_token_saving_rate"])) * 100.0,
        2,
    )
    delta_j_pp = round(
        (proposed["avg_reconstruction_fidelity_jaccard"] - float(prior["avg_reconstruction_fidelity_jaccard"]))
        * 100.0,
        2,
    )
    delta_j_vs_policy_lane_pp = None
    if policy_lane_prior:
        delta_j_vs_policy_lane_pp = round(
            (
                proposed["avg_reconstruction_fidelity_jaccard"]
                - float(policy_lane_prior["avg_reconstruction_fidelity_jaccard"])
            )
            * 100.0,
            2,
        )

    ms_external_j_floor = 0.890
    active_regression_j_floor = 0.868
    ms_external_paste_ok = float(proposed["avg_reconstruction_fidelity_jaccard"] or 0) >= ms_external_j_floor
    active_regression_ok = float(proposed["avg_reconstruction_fidelity_jaccard"] or 0) >= active_regression_j_floor

    active_approved = bool(active_sig.get("approved"))
    lex_approved = bool(lex_sig.get("approved"))
    violations_ok = int(proposed.get("sensitive_violation_count") or 0) == 0
    case_ok = int(proposed.get("case_count") or 0) >= 40
    policy_hold = (
        HEADLINE_POLICY.is_file()
        and json.loads(HEADLINE_POLICY.read_text(encoding="utf-8")).get("headline_kpi_update") == "HOLD"
    )

    promotion_ready = bool(
        active_approved
        and lex_approved
        and violations_ok
        and case_ok
        and P41708.is_file()
    )

    doc = {
        "schema": "hangul_curated_v2_ms_headline_promotion_packet_v1",
        "generated_at_utc": _utc(),
        "evidence": {
            "active_report": _rel(ACTIVE),
            "v2_active_signoff": _rel(V2_ACTIVE_SIGNOFF) if V2_ACTIVE_SIGNOFF.is_file() else None,
            "v2_lexicon_signoff": _rel(V2_LEXICON_SIGNOFF) if V2_LEXICON_SIGNOFF.is_file() else None,
            "production_lexicon": _rel(P41708) if P41708.is_file() else None,
            "headline_policy_before": _rel(HEADLINE_POLICY) if HEADLINE_POLICY.is_file() else None,
        },
        "gates": {
            "v2_active_signoff_approved": active_approved,
            "v2_lexicon_signoff_approved": lex_approved,
            "sensitive_violations_zero": violations_ok,
            "golden40_case_count_ok": case_ok,
            "production_lexicon_41708_present": P41708.is_file(),
            "prior_headline_was_hold": policy_hold,
        },
        "frozen_headline_prior_ms_archive": prior,
        "ms_submission_archive_unchanged": ms_submission_archive,
        "ms_lane_policy_prior": policy_lane_prior,
        "proposed_ms_lane_headline": proposed,
        "delta_vs_ms_submission_archive_pp": {
            "saving": delta_saving_pp,
            "jaccard": delta_j_pp,
        },
        "delta_vs_ms_lane_policy_prior_pp": {
            "jaccard": delta_j_vs_policy_lane_pp,
        },
        "section_5_external_promo_thresholds": {
            "question": "대외 홍보 채널용 Jaccard 복원 하한선 허용 역치",
            "lanes": {
                "ms_submission_archive_external_paste": {
                    "jaccard_floor": ms_external_j_floor,
                    "saving_reference_pct": 47.5,
                    "proposed_jaccard": proposed["avg_reconstruction_fidelity_jaccard_rounded"],
                    "pass": ms_external_paste_ok,
                    "verdict": "BLOCKED" if not ms_external_paste_ok else "ALLOW_CANDIDATE",
                    "note": "FAIL-COMP-004 frozen MS HWPX KPI; do not paste disk ACTIVE as submission claim.",
                },
                "internal_ms_lane_policy_paste": {
                    "jaccard_floor": active_regression_j_floor,
                    "proposed_jaccard": proposed["avg_reconstruction_fidelity_jaccard_rounded"],
                    "pass": active_regression_ok,
                    "verdict": "ALLOW_INTERNAL" if active_regression_ok else "BLOCKED",
                    "note": "CENTRAL/NVIDIA internal bench paste; already APPLIED in headline policy if signoff done.",
                },
                "disk_active_bench_regression": {
                    "jaccard_floor": active_regression_j_floor,
                    "pass": active_regression_ok,
                    "script": "scripts/check_compression_golden_bench_regression_v1.py --min-avg-jaccard 0.868",
                },
            },
            "recommended_commander_default": (
                "External/public: keep MS archive 47.54%/0.890 until J≥0.890 on chosen lane. "
                "Internal policy: 48.8%/0.869 with dual-label (archive vs active bench)."
            ),
        },
        "delta_vs_prior_ms_archive_pp": {
            "saving": delta_saving_pp,
            "jaccard": delta_j_pp,
            "deprecated_alias_of": "delta_vs_ms_submission_archive_pp",
        },
        "dual_reporting_contract": {
            "ms_submission_files_unchanged": True,
            "ms_submission_archive_kpi": (
                f"{ms_submission_archive.get('global_token_saving_rate_pct')}% / "
                f"Jaccard {round(float(ms_submission_archive['avg_reconstruction_fidelity_jaccard']), 3)}"
            ),
            "track_a_active_bench_kpi": (
                f"{proposed['global_token_saving_rate_pct']}% / "
                f"Jaccard {proposed['avg_reconstruction_fidelity_jaccard_rounded']}"
            ),
            "fail_comp_004": "ACTIVE bench updated separately; MS lane syncs policy/pointer only.",
            "repair_v2_not_headline": True,
        },
        "promotion_ready": promotion_ready,
        "ms_lane_scope": {
            "updates": [
                "reports/compression_track_a_headline_policy_v1_latest.json",
                "reports/constitution/btrack_pilot/master_codebook_bench_lexicon_pointer_v1_latest.json",
                "reports/ms_rq019_paste_ready/track_a_internal_bench_headline_v2_hangul_curated_paste.txt",
            ],
            "does_not_update": [
                "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json",
                "submitted MS HWPX/PDF archive on disk",
            ],
        },
        "commander_note": (
            "Open MS lane headline policy to v2 ACTIVE (41708). "
            "Does not rewrite closed MS submission body."
        ),
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"wrote": _rel(OUT), "promotion_ready": promotion_ready}, ensure_ascii=False))
    return 0 if promotion_ready else 2


if __name__ == "__main__":
    raise SystemExit(main())
