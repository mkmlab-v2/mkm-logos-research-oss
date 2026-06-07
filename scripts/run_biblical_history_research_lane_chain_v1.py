#!/usr/bin/env python3
"""One-click B-track biblical history research lane chain (no production merge)."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _run(cmd: list[str]) -> int:
    p = subprocess.run(cmd, cwd=str(ROOT), check=False)
    return int(p.returncode)


def main() -> int:
    ap = argparse.ArgumentParser(description="Run biblical history research lane chain.")
    ap.add_argument("--permutation-repeats", type=int, default=500)
    ap.add_argument("--skip-news-slice", action="store_true")
    ap.add_argument("--include-production-news-ingest", action="store_true")
    ap.add_argument(
        "--include-apocrypha-rebuild",
        action="store_true",
        help="Opt-in run_apocrypha_pilot frontline rebuild (live re-fetch; default off).",
    )
    ap.add_argument(
        "--ndjson-ingest-mode",
        choices=("manifest_summary", "work_surface", "full_surface_chunk"),
        default="full_surface_chunk",
        help="DSS NDJSON research ingest granularity (metadata only; no raw token text).",
    )
    args = ap.parse_args()

    perm = [
        sys.executable,
        "scripts/eval_biblical_history_h_bc1_epoch_permutation_v1.py",
        "--permutation-repeats",
        str(args.permutation_repeats),
    ]
    steps: list[tuple[str, list[str]]] = [
        ("h_bc1_permutation", perm + ["--sidecar-json", "docs/final/artifacts/biblical_history_h_bc1_bronze_collapse_chronology_sidecar_v1.json"]),
        (
            "h_ax1_permutation",
            perm
            + [
                "--sidecar-json",
                "docs/final/artifacts/biblical_history_h_ax1_axial_age_chronology_sidecar_v1.json",
            ],
        ),
        (
            "h_bc1_paleoclimate_join",
            [sys.executable, "scripts/join_biblical_history_h_bc1_paleoclimate_v1.py"],
        ),
        (
            "h_pl1_lexicon_uplift",
            [sys.executable, "scripts/eval_biblical_history_h_pl1_lexicon_uplift_v1.py"],
        ),
        (
            "h_pr1_lexicon_uplift",
            [sys.executable, "scripts/eval_biblical_history_h_pr1_lexicon_uplift_v1.py"],
        ),
        (
            "h_pr1_permutation",
            perm
            + [
                "--sidecar-json",
                "docs/final/artifacts/biblical_history_h_pr1_printing_info_disruption_chronology_sidecar_v1.json",
            ],
        ),
        (
            "h_pr1_chronicle_hold_alignment",
            [sys.executable, "scripts/eval_biblical_history_h_pr1_chronicle_hold_alignment_v1.py"],
        ),
        (
            "korea_health_infectious_fetch",
            [sys.executable, "scripts/build_korea_health_infectious_news_context_v1.py", "--use-exa"],
        ),
        (
            "h_ar1_bce_permutation",
            perm
            + [
                "--sidecar-json",
                "docs/final/artifacts/biblical_history_h_ar1_adna_migration_chronology_sidecar_v1.json",
                "--era",
                "bce",
            ],
        ),
        (
            "h_ar1_ce_permutation",
            perm
            + [
                "--sidecar-json",
                "docs/final/artifacts/biblical_history_h_ar1_adna_migration_chronology_sidecar_v1.json",
                "--era",
                "ce",
            ],
        ),
        (
            "h_ar1_adna_events_join",
            [sys.executable, "scripts/join_biblical_history_h_ar1_adna_events_v1.py"],
        ),
        (
            "chronicle_pr1_daily_overlay",
            [sys.executable, "scripts/build_chronicle_pr1_daily_overlay_v1.py"],
        ),
        (
            "chronicle_signal_refresh",
            [sys.executable, "scripts/build_chronicle_history_news_signal_stub_v1.py"],
        ),
        (
            "chronicle_weekly_eval",
            [sys.executable, "scripts/evaluate_chronicle_history_news_signal_weekly_v1.py"],
        ),
        (
            "cosmological_calibration_smoke",
            [
                sys.executable,
                "scripts/apply_biblical_history_cosmological_epoch_calibration_v1.py",
                "--hypothesis-id",
                "H-BC1",
            ],
        ),
        (
            "h_dss1_bce_permutation",
            perm
            + [
                "--sidecar-json",
                "docs/final/artifacts/biblical_history_h_dss_apocrypha_chronology_sidecar_v1.json",
                "--era",
                "bce",
            ],
        ),
        (
            "h_dss1_ce_permutation",
            perm
            + [
                "--sidecar-json",
                "docs/final/artifacts/biblical_history_h_dss_apocrypha_chronology_sidecar_v1.json",
                "--era",
                "ce",
                "--output-json",
                "reports/biblical_history_h_dss1_ce_epoch_permutation_latest.json",
            ],
        ),
        (
            "dss_frontline_research_bridge",
            [sys.executable, "scripts/build_dss_frontline_research_bridge_v1.py"],
        ),
        (
            "dss_authority_readiness_reconciliation",
            [sys.executable, "scripts/build_dss_authority_readiness_reconciliation_v1.py"],
        ),
        (
            "dss_authority_pin_policy",
            [sys.executable, "scripts/build_dss_authority_pin_policy_v1.py"],
        ),
        (
            "dss_apocrypha_research_context_ingest",
            [sys.executable, "scripts/ingest_dss_apocrypha_research_context_v1.py"],
        ),
        (
            "dss_ndjson_token_manifest_research_context_ingest",
            [
                sys.executable,
                "scripts/ingest_dss_ndjson_token_manifest_research_context_v1.py",
                "--ingest-mode",
                args.ndjson_ingest_mode,
                "--merge-into",
                "docs/final/artifacts/news_observation_v1_dss_apocrypha_research_context_latest.jsonl",
            ],
        ),
        (
            "h_dss1_chronicle_daily_overlay",
            [sys.executable, "scripts/build_chronicle_h_dss1_daily_overlay_v1.py"],
        ),
        (
            "h_dss1_chronicle_hold_alignment",
            [sys.executable, "scripts/eval_biblical_history_h_dss1_chronicle_hold_alignment_v1.py"],
        ),
        (
            "chronicle_research_decision_mix",
            [sys.executable, "scripts/build_chronicle_history_research_decision_mix_v1.py"],
        ),
        (
            "h_dss1_chronicle_epoch_shuffle_negative_control",
            [
                sys.executable,
                "scripts/eval_biblical_history_h_dss1_chronicle_epoch_shuffle_negative_control_v1.py",
                "--shuffle-repeats",
                str(min(500, args.permutation_repeats)),
            ],
        ),
        (
            "biblical_resonance_research_production_ab",
            [sys.executable, "scripts/build_biblical_resonance_research_production_ab_v1.py"],
        ),
        (
            "dss_ndjson_resonance_uplift_report",
            [sys.executable, "scripts/build_dss_ndjson_resonance_uplift_report_v1.py"],
        ),
        (
            "holdout_merge_readiness",
            [
                sys.executable,
                "scripts/build_biblical_history_holdout_merge_readiness_v1.py",
                "--run-merge",
            ],
        ),
        (
            "holdout_brier_dual_report",
            [sys.executable, "scripts/build_biblical_history_holdout_brier_dual_report_v1.py"],
        ),
    ]
    if not args.skip_news_slice:
        steps.append(
            (
                "news_research_slice",
                [
                    sys.executable,
                    "scripts/refresh_biblical_history_news_observation_slice_v1.py",
                    "--run-resonance-eval",
                    "--lookback-days",
                    "90",
                ],
            )
        )
    if args.include_apocrypha_rebuild:
        insert_at = next(i for i, (n, _) in enumerate(steps) if n == "dss_apocrypha_research_context_ingest")
        steps.insert(
            insert_at,
            (
                "dss_apocrypha_frontline_rebuild",
                [
                    sys.executable,
                    "projects/dss-4d-ingest/run_apocrypha_pilot.py",
                    "--manifest",
                    "pilot_manifest_ext2.json",
                ],
            ),
        )
    if args.include_production_news_ingest:
        steps.append(
            (
                "production_news_ingest_korea",
                [sys.executable, "scripts/ingest_korea_context_to_news_observation_v1.py", "--validate"],
            )
        )
        steps.append(
            (
                "production_news_ingest_platform_pr1",
                [
                    sys.executable,
                    "scripts/build_korea_platform_disinfo_news_context_v1.py",
                    "--use-exa",
                ],
            )
        )
        steps.append(
            (
                "production_news_ingest_platform_pr1_ledger",
                [
                    sys.executable,
                    "scripts/ingest_korea_context_to_news_observation_v1.py",
                    "--articles-json",
                    "reports/korea_platform_disinfo_news_articles_v1.json",
                    "--source-id-prefix",
                    "korea_platform_pr1",
                    "--dataset-partition",
                    "train_holdout",
                    "--validate",
                ],
            )
        )
        steps.append(
            (
                "production_news_ingest_health_pl1",
                [
                    sys.executable,
                    "scripts/ingest_korea_context_to_news_observation_v1.py",
                    "--articles-json",
                    "reports/korea_health_infectious_news_articles_v1.json",
                    "--source-id-prefix",
                    "korea_health",
                    "--dataset-partition",
                    "train_holdout",
                    "--validate",
                ],
            )
        )
        steps.append(
            (
                "production_resonance_eval_90d",
                [
                    sys.executable,
                    "scripts/evaluate_biblical_resonance_hypotheses_v1.py",
                    "--lookback-days",
                    "90",
                    "--output-json",
                    "reports/biblical_resonance_eval_production_90d_latest.json",
                ],
            )
        )

    log: list[dict[str, object]] = []
    for name, cmd in steps:
        rc = _run(cmd)
        log.append({"step": name, "return_code": rc})
        if rc != 0:
            print(json.dumps({"ok": False, "failed_step": name, "log": log}, ensure_ascii=False), file=sys.stderr)
            return rc

    out = ROOT / "reports/biblical_history_research_lane_chain_latest.json"
    payload = {
        "schema": "biblical_history_research_lane_chain_v1",
        "ok": True,
        "steps": log,
        "artifacts": {
            "h_bc1_permutation": "reports/biblical_history_h_bc1_epoch_permutation_latest.json",
            "h_ax1_permutation": "reports/biblical_history_h_ax1_epoch_permutation_latest.json",
            "h_pl1_lexicon_uplift": "reports/biblical_history_h_pl1_lexicon_uplift_latest.json",
            "h_pr1_permutation": "reports/biblical_history_h_pr1_epoch_permutation_latest.json",
            "h_pr1_chronicle_hold_alignment": "reports/biblical_history_h_pr1_chronicle_hold_alignment_latest.json",
            "korea_health_infectious": "reports/korea_health_infectious_news_articles_v1.json",
            "h_ar1_permutation": "reports/biblical_history_h_ar1_epoch_permutation_latest.json",
            "chronicle_pr1_overlay": "docs/final/artifacts/chronicle_history_news_signal_pr1_daily_overlay_latest.jsonl",
            "chronicle_signal_stub": "docs/final/artifacts/chronicle_history_news_signal_stub_latest.json",
            "chronicle_weekly_eval": "docs/final/artifacts/chronicle_history_news_signal_weekly_eval_latest.json",
            "cosmological_calibration_smoke": "reports/biblical_history_cosmological_calibration_smoke_latest.json",
            "h_dss1_sidecar": "docs/final/artifacts/biblical_history_h_dss_apocrypha_chronology_sidecar_v1.json",
            "h_dss1_bce_permutation": "reports/biblical_history_h_dss1_epoch_permutation_latest.json",
            "h_dss1_ce_permutation": "reports/biblical_history_h_dss1_ce_epoch_permutation_latest.json",
            "dss_apocrypha_research_context": "docs/final/artifacts/news_observation_v1_dss_apocrypha_research_context_latest.jsonl",
            "dss_ndjson_research_context": "docs/final/artifacts/news_observation_v1_dss_ndjson_research_context_latest.jsonl",
            "dss_apocrypha_frontline_rebuild": "reports/dss_apocrypha_frontline_rebuild_chain_latest.json",
            "dss_frontline_research_bridge": "reports/dss_frontline_research_bridge_latest.json",
            "dss_authority_readiness_reconciliation": "reports/dss_authority_readiness_reconciliation_latest.json",
            "dss_ndjson_resonance_uplift": "reports/dss_ndjson_resonance_uplift_latest.json",
            "h_dss1_chronicle_overlay": "docs/final/artifacts/chronicle_history_news_signal_h_dss1_daily_overlay_latest.jsonl",
            "h_dss1_chronicle_hold_alignment": "reports/biblical_history_h_dss1_chronicle_hold_alignment_latest.json",
            "chronicle_research_decision_mix": "docs/final/artifacts/chronicle_history_news_signal_research_decision_mix_latest.jsonl",
            "h_dss1_chronicle_epoch_shuffle_negative_control": "reports/biblical_history_h_dss1_chronicle_epoch_shuffle_negative_control_latest.json",
            "biblical_resonance_research_production_ab": "reports/biblical_resonance_research_production_ab_latest.json",
            "holdout_merge_readiness": "reports/biblical_history_holdout_merge_readiness_latest.json",
            "holdout_brier_dual_report": "reports/biblical_history_holdout_brier_dual_report_latest.json",
            "paleoclimate_join": "reports/biblical_history_h_bc1_paleoclimate_join_latest.json",
            "h_ax1_sidecar": "docs/final/artifacts/biblical_history_h_ax1_axial_age_chronology_sidecar_v1.json",
            "h_pl1_sidecar": "docs/final/artifacts/biblical_history_h_pl1_plague_chronology_sidecar_v1.json",
            "news_slice": "docs/final/artifacts/news_observation_v1_biblical_history_research_slice_latest.jsonl",
            "resonance_eval": "reports/biblical_resonance_eval_research_slice_latest.json",
            "production_resonance_eval": "reports/biblical_resonance_eval_production_90d_latest.json",
        },
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "output": str(out)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
