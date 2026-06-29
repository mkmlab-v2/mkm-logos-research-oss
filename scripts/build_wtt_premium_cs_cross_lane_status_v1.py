#!/usr/bin/env python3
"""Premium CS WTT + compression cross-lane status summary [HYPO]."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "reports/wtt_premium_cs_cross_lane_status_v1_latest.json"

PATHS = {
    "human_n30": ROOT / "reports/wtt_human_n30_gate_v1_latest.json",
    "customer_fsm": ROOT / "reports/wtt_tenant_fsm_batch_wtt-customer-live-v1_v1_latest.json",
    "wtt_intake": ROOT / "data/wtt/intake/wtt-customer-live-v1.jsonl",
    "bridge_export": ROOT / "reports/wtt_compression_bridge_export_v1_latest.json",
    "bridge_jsonl": ROOT / "data/compression/examples/wtt_premium_cs_compression_bridge_v1.jsonl",
    "compression_poc": ROOT / "reports/customer_compression_stateless_poc_wtt-premium-cs-compression-v1_v1_latest.json",
    "compression_roi": ROOT / "docs/final/artifacts/compression_b2b_pilot_roi_report_v1_latest.json",
    "readiness": ROOT / "reports/wtt_customer_intake_readiness_v1_latest.json",
    "stress_deck": ROOT / "reports/wtt_stress_certified_deck_v1_latest.md",
    "customer_provided_wtt": ROOT / "data/wtt/intake/wtt-premium-cs-customer-live-v1.jsonl",
    "customer_provided_wtt_fsm": ROOT
    / "reports/wtt_tenant_fsm_batch_wtt-premium-cs-customer-live-v1_v1_latest.json",
    "customer_provided_wtt_intake": ROOT
    / "reports/wtt_pilot_intake_wtt-premium-cs-customer-live-v1_v1.json",
    "customer_provided_poc": ROOT
    / "reports/customer_compression_stateless_poc_wtt-premium-cs-customer-v1_v1_latest.json",
    "customer_provided_intake": ROOT
    / "reports/compression_b2b_prospect_poc_corpus_wtt-premium-cs-customer-v1_v1.json",
    "cs_ablation": ROOT / "reports/wtt_cs_pilot_compression_ablation_v1_latest.json",
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_optional(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _line_count(path: Path) -> int:
    if not path.is_file():
        return 0
    return sum(1 for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip())


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    human = _load_optional(PATHS["human_n30"]) or {}
    cust_fsm = _load_optional(PATHS["customer_fsm"]) or {}
    bridge = _load_optional(PATHS["bridge_export"]) or {}
    poc = _load_optional(PATHS["compression_poc"]) or {}
    roi = _load_optional(PATHS["compression_roi"]) or {}
    readiness = _load_optional(PATHS["readiness"]) or {}
    cust_poc = _load_optional(PATHS["customer_provided_poc"]) or {}
    cust_intake = _load_optional(PATHS["customer_provided_intake"]) or {}
    cust_wtt_fsm = _load_optional(PATHS["customer_provided_wtt_fsm"]) or {}
    cust_wtt_pilot = _load_optional(PATHS["customer_provided_wtt_intake"]) or {}
    ablation = _load_optional(PATHS["cs_ablation"]) or {}

    wtt_rows = _line_count(PATHS["wtt_intake"])
    bridge_rows = _line_count(PATHS["bridge_jsonl"])
    customer_provided_rows = _line_count(PATHS["customer_provided_wtt"])
    agg = poc.get("aggregate") or {}
    cust_agg = cust_poc.get("aggregate") or {}

    report = {
        "schema": "wtt_premium_cs_cross_lane_status_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc_now(),
        "hypothesis_class": "HYPO",
        "track": "B",
        "research_only": True,
        "send_gate": "HOLD",
        "icp": "premium_cs",
        "wtt_lane": {
            "tenant_id": "wtt-customer-live-v1",
            "intake_jsonl": PATHS["wtt_intake"].as_posix(),
            "session_count": wtt_rows,
            "human_n30_gate_met": human.get("human_n30_gate_met"),
            "human_sessions_collected": human.get("human_sessions_collected"),
            "fsm_state_counts": cust_fsm.get("fsm_state_counts"),
            "curated_pilot_disclaimer": "research_only masked curation — not recruited third-party panel",
        },
        "compression_lane": {
            "tenant_id": "wtt-premium-cs-compression-v1",
            "bridge_jsonl": PATHS["bridge_jsonl"].as_posix(),
            "bridge_row_count": bridge_rows,
            "bridge_export_meta": bridge.get("compression_jsonl"),
            "poc_case_count": poc.get("case_count"),
            "poc_cases_passed": poc.get("cases_passed"),
            "mean_jaccard_proxy_all_cases": agg.get("mean_jaccard_proxy_all_cases"),
            "mean_token_saving_rate_proxy_all_cases": agg.get("mean_token_saving_rate_proxy_all_cases"),
            "roi_status": roi.get("roi_status"),
            "lane_isolated": True,
        },
        "customer_provided_wtt_lane": {
            "tenant_id": "wtt-premium-cs-customer-live-v1",
            "intake_jsonl": PATHS["customer_provided_wtt"].as_posix(),
            "session_count": customer_provided_rows,
            "fsm_state_counts": cust_wtt_fsm.get("fsm_state_counts"),
            "pilot_intake_ok": cust_wtt_pilot.get("send_gate") == "HOLD",
            "lane_isolated": True,
        },
        "customer_provided_compression_lane": {
            "tenant_id": "wtt-premium-cs-customer-v1",
            "wtt_jsonl": PATHS["customer_provided_wtt"].as_posix(),
            "session_count": customer_provided_rows,
            "btrack_poc_options": cust_intake.get("btrack_poc_options"),
            "poc_case_count": cust_poc.get("case_count"),
            "poc_cases_passed": cust_poc.get("cases_passed"),
            "pass_rate": round(
                (cust_poc.get("cases_passed") or 0) / (cust_poc.get("case_count") or 1),
                4,
            )
            if cust_poc.get("case_count")
            else None,
            "mean_jaccard_proxy_all_cases": cust_agg.get("mean_jaccard_proxy_all_cases"),
            "mean_token_saving_rate_proxy_all_cases": cust_agg.get(
                "mean_token_saving_rate_proxy_all_cases"
            ),
            "short_context_policy": cust_poc.get("short_context_policy"),
            "ablation_best_arm": ablation.get("best_arm_by_pass_then_jaccard"),
            "ablation_path": PATHS["cs_ablation"].as_posix()
            if PATHS["cs_ablation"].is_file()
            else None,
            "one_click_btrack": (
                "powershell -NoProfile -ExecutionPolicy Bypass -File "
                "scripts/Run-CompressionCustomerPilotIntake_v1.ps1 "
                "-TenantId wtt-premium-cs-customer-v1 "
                "-CustomerJsonl data/wtt/intake/wtt-premium-cs-customer-live-v1.jsonl "
                "-MaxCases 30 -MinCases 30 -RelaxPassGate -BtrackCsShortContext"
            ),
            "lane_isolated": True,
            "not_track_a_headline": True,
            "n30_target_sessions": 30,
            "n30_gate_met": customer_provided_rows >= 30,
            "n30_blocker": (
                f"awaiting_{30 - customer_provided_rows}_additional_customer_masked_sessions"
                if customer_provided_rows < 30
                else None
            ),
        },
        "operator_panel_separate": {
            "not_eligible_for_send": True,
            "note": "operator_panel 30/30 is dogfood only — never merge with customer lane headlines",
        },
        "readiness_blockers": readiness.get("blockers") or [],
        "artifacts": {k: v.as_posix() for k, v in PATHS.items() if v.is_file()},
        "one_click_closure": "powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Invoke-WttPremiumCsClosure_v1.ps1",
        "note_ko": "WTT human_n30와 compression ROI는 격벽 유지. SEND·Track A·대외 SLA 주장 금지.",
        "ok": wtt_rows >= 30 and human.get("human_n30_gate_met") is True,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": report["ok"],
                "wtt_sessions": wtt_rows,
                "human_n30_gate_met": report["wtt_lane"]["human_n30_gate_met"],
                "compression_bridge_rows": bridge_rows,
                "out": str(args.out.resolve()),
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
