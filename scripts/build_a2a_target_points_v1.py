#!/usr/bin/env python3
"""Emit A2A target points v1 — three internal ROI call sites (WATCH · B-track).

  py scripts/build_a2a_target_points_v1.py
  py scripts/build_a2a_target_points_v1.py --strict-exit
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "a2a_target_points_v1_latest.json"
WIRE_PROFILE = ROOT / "docs" / "final" / "artifacts" / "mkm_inter_agent_wire_profile_v0.json"
DIALOGUE_MOCK_SUMMARY = ROOT / "docs/final/artifacts/mkm_inter_agent_dialogue_mock_summary_latest.json"
FIRST_MESSAGE = ROOT / "docs/final/artifacts/mkm_inter_agent_first_message_worked_example_v1.json"
TOKEN_BENCH = ROOT / "reports/mkm_ops_memory_index_token_bench_v1_latest.json"
RESUME_A2A_PILOT = ROOT / "docs/final/artifacts/mkm_chat_resume_a2a_pilot_v1_latest.json"
TP02_LEXICON_BENCH = ROOT / "docs/final/artifacts/a2a_tp02_lexicon_dense_bench_v1_latest.json"
TP03_CHAIN_REF_PILOT = ROOT / "docs/final/artifacts/a2a_tp03_chain_ref_pilot_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _dialogue_savings_snapshot() -> dict[str, Any] | None:
    doc = _read_json(DIALOGUE_MOCK_SUMMARY)
    if not doc:
        return None
    ratios: list[float] = []
    token_ins: list[int] = []
    for row in doc.get("transcript") or []:
        metrics = (row.get("compress") or {}).get("compression_metrics") or {}
        if isinstance(metrics.get("savings_ratio"), (int, float)):
            ratios.append(float(metrics["savings_ratio"]))
        if isinstance(metrics.get("token_in"), int):
            token_ins.append(int(metrics["token_in"]))
    return {
        "source": str(DIALOGUE_MOCK_SUMMARY.relative_to(ROOT)).replace("\\", "/"),
        "scenario": doc.get("scenario"),
        "savings_ratio_by_turn": ratios,
        "token_in_by_turn": token_ins,
        "zero_savings_turns": sum(1 for r in ratios if r <= 0.0),
        "max_savings_ratio": max(ratios) if ratios else None,
    }


def _first_message_snapshot() -> dict[str, Any] | None:
    doc = _read_json(FIRST_MESSAGE)
    if not doc:
        return None
    compress = doc.get("compress") or {}
    metrics = compress.get("compression_metrics") or {}
    flags = compress.get("integrity_flags") or {}
    return {
        "source": str(FIRST_MESSAGE.relative_to(ROOT)).replace("\\", "/"),
        "savings_ratio": metrics.get("savings_ratio"),
        "token_in": metrics.get("token_in"),
        "token_out": metrics.get("token_out"),
        "evaluate_report_ms": flags.get("evaluate_report_ms"),
        "jaccard_proxy": flags.get("jaccard_proxy"),
    }


def _token_bench_snapshot() -> dict[str, Any] | None:
    doc = _read_json(TOKEN_BENCH)
    if not doc:
        return None
    delta = doc.get("delta_vs_full_slices") or {}
    return {
        "source": str(TOKEN_BENCH.relative_to(ROOT)).replace("\\", "/"),
        "reduction_percent_vs_full_slices": delta.get("reduction_percent"),
        "tokens_saved_pins_off": delta.get("tokens_saved_pins_off"),
        "note": "resume-pack pin inject vs full anchor slices — not v2 compress yet",
    }


def _resume_a2a_pilot_snapshot() -> dict[str, Any] | None:
    doc = _read_json(RESUME_A2A_PILOT)
    if not doc:
        return None
    compress = doc.get("compress_result") or {}
    inject = doc.get("inject_payload") or {}
    return {
        "source": str(RESUME_A2A_PILOT.relative_to(ROOT)).replace("\\", "/"),
        "decision": compress.get("decision"),
        "inject_tokens": inject.get("tokens"),
        "savings_ratio": (compress.get("compression_metrics") or {}).get("savings_ratio"),
        "evaluate_report_ms": compress.get("evaluate_report_ms"),
        "content_fingerprint": compress.get("content_fingerprint"),
    }


def _tp02_lexicon_bench_snapshot() -> dict[str, Any] | None:
    doc = _read_json(TP02_LEXICON_BENCH)
    if not doc:
        return None
    headline = doc.get("kpi_headline") or {}
    return {
        "source": str(TP02_LEXICON_BENCH.relative_to(ROOT)).replace("\\", "/"),
        "bench_ok": doc.get("bench_ok"),
        "scenario": (doc.get("bench_config") or {}).get("scenario"),
        "mock_avg_savings_ratio": headline.get("mock_avg_savings_ratio"),
        "mock_max_savings_ratio": headline.get("mock_max_savings_ratio"),
        "wire_avg_envelope_vs_packet_savings": headline.get("wire_avg_envelope_vs_packet_savings"),
    }


def _tp03_chain_ref_pilot_snapshot() -> dict[str, Any] | None:
    doc = _read_json(TP03_CHAIN_REF_PILOT)
    if not doc:
        return None
    agg = doc.get("aggregate_pointer_vs_full") or {}
    headline = doc.get("kpi_headline") or {}
    return {
        "source": str(TP03_CHAIN_REF_PILOT.relative_to(ROOT)).replace("\\", "/"),
        "artifacts_present": doc.get("artifacts_present"),
        "reduction_percent_pointer_vs_full": agg.get("reduction_percent"),
        "tokens_saved_sum": agg.get("tokens_saved_sum"),
        "largest_artifact_id": headline.get("largest_artifact_id"),
    }


def build_document(*, include_kpi_snapshot: bool = True) -> dict[str, Any]:
    skip_rules: dict[str, Any] = {
        "status": "draft_hypothesis",
        "min_plaintext_tokens_recommend": 32,
        "max_evaluate_report_ms_without_roi_hypothesis": 615.0,
        "rationale": (
            "dialogue mock: token_in <= 26 showed savings_ratio 0.0; "
            "ACK+inferred turns ~49-54%. first_message evaluate_report_ms ~615."
        ),
        "boundary_ack": "Skip thresholds are B-track pilot hints — not production SLA.",
        "evidence_artifact_paths": [
            "docs/final/artifacts/mkm_inter_agent_dialogue_mock_summary_latest.json",
            "docs/final/artifacts/mkm_inter_agent_first_message_worked_example_v1.json",
        ],
    }

    target_points: list[dict[str, Any]] = [
        {
            "id": "tp01_cursor_ops_resume_handoff",
            "priority": 1,
            "title_ko": "Cursor 멀티채팅 ops resume handoff",
            "lane": "ops_memory_index",
            "status": "PILOT",
            "pilot_script": "scripts/build_mkm_chat_resume_a2a_pilot_v1.py",
            "pilot_artifact": "docs/final/artifacts/mkm_chat_resume_a2a_pilot_v1_latest.json",
            "input": {
                "sources": [
                    "MISSION_LOG.md",
                    "docs/final/CENTRAL_AGENT_MEMORY_V1.md",
                    "docs/final/artifacts/mkm_ops_memory_index_v1_latest.json",
                ],
                "builder_scripts": [
                    "scripts/build_mkm_chat_resume_pack_v1.py",
                    "scripts/build_mkm_ops_memory_index_v1.py",
                ],
                "payload_today": "essence + must_keep_tags (+ optional slice preview)",
            },
            "output": {
                "artifacts": [
                    "docs/final/artifacts/mkm_chat_resume_pack_latest.md",
                    "docs/final/artifacts/mkm_chat_resume_pack_latest.json",
                ],
                "a2a_target_wire": "v2 Trust Packet or wire envelope v1 + content_fingerprint",
            },
            "a2a_wire": {
                "compress_endpoint": "POST /v2/compress",
                "expand_endpoint": "POST /v2/expand",
                "stub": "scripts/compression_token_api_v2_stub.py",
                "routing_profile_default": "track_a_promoted",
                "wire_envelope_optional": "scripts/mkm_inter_agent_wire_envelope_v1.py",
                "pilot_bench": "scripts/bench_mkm_ops_memory_index_token_savings_v1.py",
            },
            "skip_rules": {
                "apply_global_skip_rules": True,
                "skip_if_inject_tokens_below": 32,
                "prefer_pins_over_full_slice": True,
                "note": "Measure pin inject first; add compress only when inject_on exceeds skip threshold.",
            },
            "pytest_paths": [
                "tests/test_bench_mkm_ops_memory_index_token_savings_v1.py",
                "tests/test_build_mkm_chat_resume_a2a_pilot_v1.py",
            ],
            "roi_hypothesis": {
                "driver": "daily cross-chat context re-injection",
                "evidence_bench": "scripts/bench_mkm_ops_memory_index_token_savings_v1.py",
                "expected_margin": "pin inject vs full slices (local bench); v2 compress TBD on dense turns",
            },
            "excluded_from": [
                "public_showroom_topology_radar_v1.html",
                "Track A commercial headline",
                "live trading trigger",
            ],
        },
        {
            "id": "tp02_btrack_prophecy_executor_wire",
            "priority": 2,
            "title_ko": "B-track 예언→집행 A2A wire loop",
            "lane": "inter_agent_encoding",
            "status": "PILOT",
            "pilot_script": "scripts/build_a2a_tp02_lexicon_dense_bench_v1.py",
            "pilot_artifact": "docs/final/artifacts/a2a_tp02_lexicon_dense_bench_v1_latest.json",
            "bench_scenario_ssot": "lexicon_dense",
            "input": {
                "scenarios": ["trading", "lexicon_dense", "health"],
                "alpha_role": "agent_alpha_prophecy",
                "beta_role": "agent_beta_executor",
                "on_wire_only": True,
            },
            "output": {
                "trust_packet_mock": "docs/final/artifacts/mkm_inter_agent_dialogue_mock_summary_latest.json",
                "wire_first_envelope": "docs/final/artifacts/mkm_inter_agent_dialogue_wire_first_latest.json",
                "smoke_wrapper": "scripts/Invoke-MkmInterAgentEncodingSmoke_v1.ps1",
            },
            "a2a_wire": {
                "trust_packet_dialogue": "scripts/run_mkm_inter_agent_dialogue_mock_v1.py",
                "wire_first_dialogue": "scripts/run_mkm_inter_agent_dialogue_wire_first_v1.py",
                "bench_scenario_recommend": "lexicon_dense",
                "routing_profiles": ["track_a_promoted", "b_track_domain_relax"],
            },
            "skip_rules": {
                "apply_global_skip_rules": True,
                "bench_scenario_for_roi": "lexicon_dense",
                "skip_short_alpha_turns": True,
                "note": "Use lexicon_dense for savings proof; trading short turns often savings_ratio 0.",
            },
            "pytest_paths": [
                "tests/test_run_mkm_inter_agent_dialogue_mock_v1.py",
                "tests/test_run_mkm_inter_agent_dialogue_wire_first_v1.py",
                "tests/test_build_a2a_tp02_lexicon_dense_bench_v1.py",
                "tests/test_compression_token_api_v2_stub.py",
            ],
            "roi_hypothesis": {
                "driver": "repeated alpha/beta handoff with lexicon-dense corpus",
                "bench_scenario_ssot": "lexicon_dense",
                "evidence_bench": "scripts/build_a2a_tp02_lexicon_dense_bench_v1.py",
            },
            "excluded_from": [
                "Track A trading execution",
                "production A2A SLA",
                "showroom inter-agent demo auto-merge to live",
            ],
        },
        {
            "id": "tp03_trackc_multilens_chain_refs",
            "priority": 3,
            "title_ko": "Track C / 멀티렌즈 체인 중간 참조",
            "lane": "track_c_fusion",
            "status": "PILOT",
            "pilot_script": "scripts/build_a2a_tp03_chain_ref_pilot_v1.py",
            "pilot_artifact": "docs/final/artifacts/a2a_tp03_chain_ref_pilot_v1_latest.json",
            "input": {
                "chain_wrappers": [
                    "scripts/Invoke-TrackCMacroDailyFusion_v1.ps1",
                    "scripts/Invoke-PremiumMultilensQueueRoutine_v1.ps1",
                ],
                "large_json_builders": [
                    "scripts/build_cross_lens_rag_fusion_v1.py",
                    "scripts/build_logos_insight_bundle_v1.py",
                    "scripts/build_mkm_trackc_ops_dashboard_v1.py",
                ],
                "queue_stub": "scripts/premium_multilens_job_queue_stub_v1.py",
            },
            "output": {
                "disk_ssot_pattern": "docs/final/artifacts/*_latest.json",
                "a2a_target_wire": "artifact path + content_fingerprint + optional Trust Packet pointer",
                "human_publish_unchanged": True,
            },
            "a2a_wire": {
                "pattern": "pointer_plus_fingerprint",
                "do_not_replace": "published showroom JSON/HTML bodies",
                "queue_export": "premium_multilens_job_queue_stub_v1.py export-pending",
            },
            "skip_rules": {
                "apply_global_skip_rules": True,
                "skip_if_agent_context_is_path_only": True,
                "compress_when": "agent must re-ingest large JSON body in same turn",
                "note": "File on disk stays SSOT; A2A shrinks agent context only.",
            },
            "pytest_paths": [
                "tests/test_premium_multilens_job_queue_stub_v1.py",
                "tests/test_build_a2a_tp03_chain_ref_pilot_v1.py",
            ],
            "roi_hypothesis": {
                "driver": "multi-step fusion passes large JSON between agent steps",
                "evidence_bench": "scripts/build_a2a_tp03_chain_ref_pilot_v1.py",
                "pattern": "pointer_plus_fingerprint on disk SSOT",
            },
            "excluded_from": [
                "showroom_macro_horizon_2030_slice_v1_latest.json public fetch",
                "B2B rehearsal MD",
                "Track A promotion",
            ],
        },
    ]

    doc: dict[str, Any] = {
        "schema": "a2a_target_points_v1",
        "version": "1.0.0",
        "status": "PILOT_ALL_THREE_TP",
        "research_only": True,
        "hypothesis_tier": "B",
        "final_action": "PILOT_ALL_THREE_TP",
        "boundary_ack": (
            "Three internal A2A ROI call sites. B-track [HYPO] only. "
            "No Track A KPI merge. No live trading. No showroom human UI wire codec."
        ),
        "wire_profile_ssot": "docs/final/artifacts/mkm_inter_agent_wire_profile_v0.json",
        "generated_at_utc": _utc_now(),
        "compress_skip_rules_v1": skip_rules,
        "target_points": target_points,
        "excluded_surfaces": [
            "projects/bitcoin-trading/ops/windows-rehearsal/jemaai-cloud-mvp/public_showroom_topology_radar_v1.html",
            "docs/final/artifacts/showroom_macro_horizon_2030_slice_v1_latest.json",
            "reports/track_c_b2b_15min_rehearsal_script_v1_latest.md",
            "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json",
        ],
        "evidence_paths": [
            "scripts/build_a2a_target_points_v1.py",
            "scripts/build_a2a_target_points_pilot_bundle_v1.py",
            "scripts/Invoke-A2aTargetPointsPilotBundle_v1.ps1",
            "scripts/build_mkm_chat_resume_a2a_pilot_v1.py",
            "scripts/build_a2a_tp02_lexicon_dense_bench_v1.py",
            "scripts/build_a2a_tp03_chain_ref_pilot_v1.py",
            "scripts/run_mkm_inter_agent_dialogue_mock_v1.py",
            "scripts/compression_token_api_v2_stub.py",
            "docs/final/artifacts/mkm_inter_agent_wire_profile_v0.json",
        ],
        "pilot_bundle": {
            "script": "scripts/build_a2a_target_points_pilot_bundle_v1.py",
            "wrapper_ps1": "scripts/Invoke-A2aTargetPointsPilotBundle_v1.ps1",
            "artifact": "docs/final/artifacts/a2a_target_points_pilot_bundle_v1_latest.json",
        },
    }

    if include_kpi_snapshot:
        snap: dict[str, Any] = {}
        dm = _dialogue_savings_snapshot()
        if dm:
            snap["dialogue_mock"] = dm
        fm = _first_message_snapshot()
        if fm:
            snap["first_message_worked_example"] = fm
        tb = _token_bench_snapshot()
        if tb:
            snap["ops_memory_index_token_bench"] = tb
        pilot = _resume_a2a_pilot_snapshot()
        if pilot:
            snap["tp01_resume_a2a_pilot"] = pilot
        tp02 = _tp02_lexicon_bench_snapshot()
        if tp02:
            snap["tp02_lexicon_dense_bench"] = tp02
        tp03 = _tp03_chain_ref_pilot_snapshot()
        if tp03:
            snap["tp03_chain_ref_pilot"] = tp03
        if snap:
            doc["measured_kpi_snapshot"] = snap

    return doc


def _validate_paths(doc: dict[str, Any], *, root: Path) -> list[str]:
    errors: list[str] = []
    for rel in doc.get("evidence_paths") or []:
        if not (root / rel).is_file():
            errors.append(f"missing evidence path: {rel}")
    wire = root / str(doc.get("wire_profile_ssot") or "")
    if not wire.is_file():
        errors.append(f"missing wire profile: {doc.get('wire_profile_ssot')}")

    for tp in doc.get("target_points") or []:
        for rel in tp.get("pytest_paths") or []:
            if not (root / rel).is_file():
                errors.append(f"missing pytest for {tp.get('id')}: {rel}")
        for key in ("builder_scripts",):
            for block in [tp.get("input") or {}]:
                for rel in block.get(key) or []:
                    if not (root / rel).is_file():
                        errors.append(f"missing script for {tp.get('id')}: {rel}")
        a2a = tp.get("a2a_wire") or {}
        for rel_key in ("stub", "trust_packet_dialogue", "wire_first_dialogue", "pilot_bench"):
            rel = a2a.get(rel_key)
            if rel and not (root / rel).is_file():
                errors.append(f"missing a2a_wire.{rel_key} for {tp.get('id')}: {rel}")
        for rel_key in ("pilot_script",):
            rel = tp.get(rel_key)
            if rel and not (root / rel).is_file():
                errors.append(f"missing {rel_key} for {tp.get('id')}: {rel}")
    bundle = doc.get("pilot_bundle") or {}
    for rel_key in ("script", "wrapper_ps1"):
        rel = bundle.get(rel_key)
        if rel and not (root / rel).is_file():
            errors.append(f"missing pilot_bundle.{rel_key}: {rel}")
    return errors


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--out",
        type=Path,
        default=DEFAULT_OUT,
        help="Output JSON path",
    )
    ap.add_argument(
        "--strict-exit",
        action="store_true",
        help="Exit 1 if referenced paths missing",
    )
    ap.add_argument(
        "--skip-kpi-snapshot",
        action="store_true",
        help="Omit measured_kpi_snapshot block",
    )
    args = ap.parse_args()

    doc = build_document(include_kpi_snapshot=not args.skip_kpi_snapshot)
    errors = _validate_paths(doc, root=ROOT)
    if errors and args.strict_exit:
        for err in errors:
            print(f"FAIL: {err}", file=sys.stderr)
        return 1

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.out}")
    if errors:
        for err in errors:
            print(f"WARN: {err}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
