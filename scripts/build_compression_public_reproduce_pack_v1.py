#!/usr/bin/env python3
"""Proof Sprint Lv.2 — aggregate reproducible public evidence (internal HOLD)."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT_DEFAULT = ROOT / "docs/final/artifacts/compression_public_reproduce_pack_v1_latest.json"
OPEN_STD = ROOT / "data/compression/stateless_poc_open_structured_v1.jsonl"
OPEN_LONG = ROOT / "data/compression/stateless_poc_open_structured_long_v1.jsonl"
GOLDEN40 = ROOT / "data/compression/stateless_poc_golden40_public_safe_v1.jsonl"
POC_STD = ROOT / "reports/customer_compression_stateless_poc_open_structured_v1_latest.json"
POC_LONG = ROOT / "reports/customer_compression_stateless_poc_open_structured_long_v1_latest.json"
POC_GOLDEN40 = ROOT / "reports/customer_compression_stateless_poc_golden40_public_safe_v1_latest.json"
POC_GOLDEN40_ROUTED = ROOT / "reports/customer_compression_stateless_poc_golden40_public_safe_routed_v1_latest.json"
OPEN_BENCH_DUAL = ROOT / "reports/compression_open_bench_dual_report_v1_latest.json"
OPEN_BENCH_ROUTING = ROOT / "docs/final/artifacts/compression_open_bench_public_routing_v1.json"
TRACK_A = ROOT / "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json"
HANDOFF_BENCH = ROOT / "reports/mkm_ops_memory_index_token_bench_v1_latest.json"
LAUNCH = ROOT / "docs/final/artifacts/a_codeai_public_benchmark_launch_checklist_v1.json"
FACT_SHEETS = ROOT / "docs/final/artifacts/media_fact_sheet_index_v1_latest.json"
PILOT_ROI = ROOT / "docs/final/artifacts/compression_b2b_pilot_roi_report_v1_latest.json"
LEGAL_SIGNOFF = ROOT / "docs/final/artifacts/compression_b2b_legal_send_signoff_v1_latest.json"
RECOMMENDED = ROOT / "docs/final/artifacts/compression_b2b_recommended_workflow_v1.json"
INDUSTRY_BUNDLE = ROOT / "reports/compression_b2b_sku_industry_poc_bundle_v1_latest.json"
INDUSTRY_GAP = ROOT / "reports/compression_b2b_industry_sku_gap_report_v1_latest.json"
INDUSTRY_FAILURE = ROOT / "reports/compression_b2b_industry_failure_panel_v1_latest.json"
SHORT_CAP_COMPARE = ROOT / "reports/compression_b2b_short_context_cap_compare_v1_latest.json"
INDUSTRY_CHAIN = ROOT / "reports/compression_b2b_evidence_v1_industry_chain_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _sha256(path: Path) -> str | None:
    if not path.is_file():
        return None
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _load(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _poc_metrics(path: Path) -> dict[str, Any]:
    doc = _load(path) or {}
    agg = doc.get("aggregate") or {}
    sku_ctx = doc.get("sku_context") if isinstance(doc.get("sku_context"), dict) else {}
    out: dict[str, Any] = {
        "report_path": path.relative_to(ROOT).as_posix(),
        "generated_at_utc": doc.get("generated_at_utc"),
        "case_count": doc.get("case_count"),
        "cases_passed_jaccard_floor": doc.get("cases_passed_jaccard_floor"),
        "mean_token_saving_rate_proxy": agg.get("mean_token_saving_rate_proxy"),
        "mean_jaccard_proxy": agg.get("mean_jaccard_proxy"),
        "exit_ok": bool(doc),
    }
    if sku_ctx.get("forced_shard_id"):
        out["forced_shard_id"] = sku_ctx.get("forced_shard_id")
    if sku_ctx.get("external_sku"):
        out["external_sku"] = sku_ctx.get("external_sku")
    return out


def _git_head() -> str | None:
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            check=False,
        )
        if proc.returncode == 0:
            return proc.stdout.strip()[:12]
    except OSError:
        pass
    return None


def build() -> dict[str, Any]:
    poc_std = _poc_metrics(POC_STD)
    poc_long = _poc_metrics(POC_LONG)
    poc_g40 = _poc_metrics(POC_GOLDEN40)
    poc_g40_routed = _poc_metrics(POC_GOLDEN40_ROUTED)
    track_a = _load(TRACK_A) or {}
    kpi = track_a.get("compression_metrics") or track_a.get("kpi") or {}
    if not kpi and track_a:
        kpi = {
            "global_token_saving_rate": track_a.get("global_token_saving_rate"),
            "avg_reconstruction_fidelity_jaccard": track_a.get("avg_reconstruction_fidelity_jaccard"),
        }
    handoff = _load(HANDOFF_BENCH) or {}
    launch = _load(LAUNCH) or {}
    pilot_roi = _load(PILOT_ROI) or {}
    signoff = _load(LEGAL_SIGNOFF) or {}
    send_gate = signoff.get("send_gate") or "HOLD"
    external_send = bool(signoff.get("ready_for_external_send"))

    handoff_full = (handoff.get("full_anchor_slices") or {}).get("tokens")
    handoff_off = (handoff.get("resume_pack_inject_off") or {}).get("tokens")
    handoff_pct = (handoff.get("delta_vs_full_slices") or {}).get("reduction_percent")

    industry_bundle = _load(INDUSTRY_BUNDLE) or {}
    industry_failure = _load(INDUSTRY_FAILURE) or {}
    short_cap = _load(SHORT_CAP_COMPARE) or {}
    industry_chain = _load(INDUSTRY_CHAIN) or {}

    industry_skus: list[dict[str, Any]] = []
    for step in industry_bundle.get("steps") or []:
        if step.get("exit_code") != 0:
            continue
        industry_skus.append(
            {
                "external_sku": step.get("external_sku"),
                "corpus_path": step.get("corpus_path"),
                "report_path": step.get("report_path"),
                "cases_passed_jaccard_floor": step.get("cases_passed_jaccard_floor"),
                "mean_token_saving_rate_proxy": step.get("mean_token_saving_rate_proxy"),
                "mean_jaccard_proxy": step.get("mean_jaccard_proxy"),
                "mean_jaccard_all_cases": step.get("mean_jaccard_all_cases"),
                "compression_profile": step.get("compression_profile")
                or industry_bundle.get("compression_profile_default"),
                "must_keep_overlay_applied": step.get("must_keep_overlay_applied"),
            }
        )

    lv3_industry = {
        "level": "Lv.3_industry_b2b",
        "research_only": True,
        "hypothesis_tier": "B",
        "send_gate": "HOLD",
        "bundle_ok": industry_bundle.get("bundle_ok"),
        "compression_profile_default": industry_bundle.get("compression_profile_default", "literal"),
        "rows_per_sku": industry_bundle.get("rows_per_sku"),
        "must_keep_overlay": industry_bundle.get("must_keep_overlay"),
        "sku_summaries": industry_skus,
        "gap_report_path": INDUSTRY_GAP.relative_to(ROOT).as_posix()
        if INDUSTRY_GAP.is_file()
        else None,
        "failure_panel_path": INDUSTRY_FAILURE.relative_to(ROOT).as_posix()
        if INDUSTRY_FAILURE.is_file()
        else None,
        "short_cap_compare_path": SHORT_CAP_COMPARE.relative_to(ROOT).as_posix()
        if SHORT_CAP_COMPARE.is_file()
        else None,
        "recommended_profile": short_cap.get("recommended_profile"),
        "failure_panel_high_saving_collapse_count": (
            industry_failure.get("summary") or {}
        ).get("high_saving_jaccard_collapse_count"),
        "chain_script": "scripts/run_compression_b2b_evidence_v1_industry_chain_v1.py",
        "chain_ok": industry_chain.get("chain_ok"),
    }

    return {
        "schema": "compression_public_reproduce_pack_v1",
        "proof_sprint_level": "lv3",
        "generated_at_utc": _utc(),
        "git_head": _git_head(),
        "labels": ["DRAFT", "internal_only", "research_only", "publish_allowed=false"],
        "send_gate": send_gate,
        "ready_for_external_send": external_send,
        "legal_send_signoff": LEGAL_SIGNOFF.relative_to(ROOT).as_posix()
        if LEGAL_SIGNOFF.is_file()
        else None,
        "one_command_reproduce": "py scripts/run_compression_evidence_lv1_chain_v1.py",
        "recommended_workflow": RECOMMENDED.relative_to(ROOT).as_posix()
        if RECOMMENDED.is_file()
        else None,
        "media_fact_sheets": FACT_SHEETS.relative_to(ROOT).as_posix()
        if FACT_SHEETS.is_file()
        else None,
        "skus": {
            "compression_api_open_structured": {
                "corpus_path": OPEN_STD.relative_to(ROOT).as_posix(),
                "corpus_sha256": _sha256(OPEN_STD),
                "metrics": poc_std,
                "allowed_headline": (
                    f"Open JSONL {poc_std.get('case_count') or '?'}-case structured API/log shapes — per-corpus measured proxy only"
                ),
                "forbidden_headline": "Global enterprise savings guarantee",
            },
            "compression_api_open_structured_long": {
                "corpus_path": OPEN_LONG.relative_to(ROOT).as_posix(),
                "corpus_sha256": _sha256(OPEN_LONG),
                "metrics": poc_long,
                "allowed_headline": (
                    f"Open JSONL {poc_long.get('case_count') or '?'}-case long structured batches — per-corpus measured proxy only"
                ),
                "forbidden_headline": "Marketing % without corpus+profile citation",
            },
            "compression_api_golden40_public_safe": {
                "corpus_path": GOLDEN40.relative_to(ROOT).as_posix(),
                "corpus_sha256": _sha256(GOLDEN40),
                "metrics": poc_g40,
                "source_eval": "docs/final/artifacts/MULTILENS_PERFORMANCE_EVAL_INPUT_V2.json",
                "role": "public_safe_reproduce_subset_stateless",
                "allowed_headline": (
                    "40-case EN ops eval excerpt — stateless PoC (no forced_shard); per-corpus measured only"
                ),
                "forbidden_headline": "Equate to customer SLA or global 47% guarantee",
            },
            "compression_api_golden40_public_safe_routed": {
                "corpus_path": GOLDEN40.relative_to(ROOT).as_posix(),
                "corpus_sha256": _sha256(GOLDEN40),
                "external_sku": "MKM-CHAT-D1",
                "forced_shard_id": poc_g40_routed.get("forced_shard_id") or "zone_d_ssot_b2b_v1",
                "routing_manifest": OPEN_BENCH_ROUTING.relative_to(ROOT).as_posix()
                if OPEN_BENCH_ROUTING.is_file()
                else None,
                "metrics": poc_g40_routed,
                "role": "public_safe_reproduce_subset_forced_shard",
                "allowed_headline": (
                    "Open golden40 N=40 · MKM-CHAT-D1 forced_shard — raw measured proxy only "
                    "(not production Track A SLA)"
                ),
                "forbidden_headline": "Merge with stateless 0% or Track A 47.5% in one headline",
            },
            "compression_api_track_a_reference": {
                "report_path": TRACK_A.relative_to(ROOT).as_posix(),
                "global_token_saving_rate": kpi.get("global_token_saving_rate")
                or track_a.get("global_token_saving_rate"),
                "avg_jaccard": kpi.get("avg_reconstruction_fidelity_jaccard")
                or track_a.get("avg_reconstruction_fidelity_jaccard"),
                "role": "internal_regression_ssot_only",
                "forbidden_headline": "Customer SLA or press guarantee",
            },
            "handoff_governance": {
                "bench_path": HANDOFF_BENCH.relative_to(ROOT).as_posix(),
                "full_anchor_tokens_top_n": handoff_full,
                "inject_off_tokens": handoff_off,
                "reduction_percent_vs_full": handoff_pct,
                "comparison_scope": handoff.get("comparison_scope"),
                "forbidden_headline": "General lossless 99% compression for arbitrary text",
            },
            "pilot_roi": {
                "customer_dollar_roi": pilot_roi.get("customer_dollar_roi"),
                "customer_krw_roi": pilot_roi.get("customer_krw_roi"),
                "prospect_corpus_cases": (pilot_roi.get("measured_proxy") or {}).get("case_count")
                or "20-50 (post-agreement)",
                "status": pilot_roi.get("status") or "awaiting_pilot_measurement",
                "report_path": PILOT_ROI.relative_to(ROOT).as_posix() if PILOT_ROI.is_file() else None,
                "measured_proxy": pilot_roi.get("measured_proxy"),
                "intake_template": "docs/final/artifacts/compression_b2b_prospect_poc_corpus_intake_v1.template.json",
            },
        },
        "open_bench_dual_report": OPEN_BENCH_DUAL.relative_to(ROOT).as_posix()
        if OPEN_BENCH_DUAL.is_file()
        else None,
        "open_bench_launch": {
            "checklist_path": LAUNCH.relative_to(ROOT).as_posix(),
            "decision": (launch.get("summary") or {}).get("decision"),
            "pass_count": (launch.get("summary") or {}).get("pass_count"),
        },
        "lv3_industry_b2b": lv3_industry,
        "reproduce_commands": [
            "py scripts/run_compression_evidence_lv1_chain_v1.py",
            "py scripts/run_compression_proof_completion_chain_v1.py",
            "py scripts/run_compression_b2b_evidence_v1_industry_chain_v1.py",
        ],
        "fail_comp_004": [
            "Do not merge open_long % with Track A % with handoff % in one headline",
            "Do not use tenant stub 97.6% as marketing proof",
        ],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-json", type=Path, default=OUT_DEFAULT)
    args = ap.parse_args()
    doc = build()
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "output": str(args.out_json),
                "open_long_saving": (
                    doc["skus"]["compression_api_open_structured_long"]["metrics"].get(
                        "mean_token_saving_rate_proxy"
                    )
                ),
                "handoff_reduction_percent": doc["skus"]["handoff_governance"].get(
                    "reduction_percent_vs_full"
                ),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
