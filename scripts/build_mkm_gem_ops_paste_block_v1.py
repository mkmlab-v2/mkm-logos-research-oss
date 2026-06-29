#!/usr/bin/env python3
"""Build one JSON paste block for Gemini MKM ops brief (Fact-Lock, disk SSOT only)."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "reports/mkm_gem_ops_paste_block_latest.json"

PATHS = {
    "trading_go_no_go": ROOT / "docs/final/artifacts/trading_go_no_go_latest.json",
    "lens_shadow_gate": ROOT / "docs/final/artifacts/independent_lens_shadow_gate_latest.json",
    "regime_trinity": ROOT / "projects/bitcoin-trading/memory/v2/risk/risk_profile_fact_safe_latest.json",
    "logos_bridge_registry": ROOT / "docs/final/artifacts/logos_concept_bridge_registry_v1_latest.json",
    "gcp_billing_probe": ROOT / "reports/gcp_genai_app_builder_billing_probe_latest.json",
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _rel(p: Path) -> str:
    try:
        return str(p.resolve().relative_to(ROOT.resolve())).replace("\\", "/")
    except ValueError:
        return str(p).replace("\\", "/")


def _count_gemini_bridges(registry: dict[str, Any] | None) -> int:
    if not registry:
        return 0
    n = 0
    for entry in registry.get("entries") or []:
        if entry.get("generation_method") == "gemini_batch_v1":
            n += 1
    return n


def build_block() -> dict[str, Any]:
    go = _load(PATHS["trading_go_no_go"])
    lens = _load(PATHS["lens_shadow_gate"])
    risk = _load(PATHS["regime_trinity"])
    bridge_reg = _load(PATHS["logos_bridge_registry"])
    billing_probe = _load(PATHS["gcp_billing_probe"])
    gemini_bridge_count = _count_gemini_bridges(bridge_reg)

    block: dict[str, Any] = {
        "schema": "mkm_gem_ops_paste_block_v1",
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "boundary_ack": True,
        "note": "Gem 작전지휘 전용. 이 블록만 SSOT. 실매매 주문은 별도 승인.",
        "field": {
            "regime_id": None,
            "go_no_go": None,
            "risk_mode": None,
            "gate_ok": None,
            "approval_decision": None,
            "sources": {},
        },
        "lens": {
            "myeongni": {"status": None, "source": None},
            "sasang": {"status": None, "source": None},
            "logos": {"status": None, "tag": "[NON_GATING]", "source": None},
        },
        "conflict": {"items": [], "principle": "most_conservative_wins"},
        "final_action": {"decision": "HOLD", "reason": "pending_evidence"},
        "logos_research": {
            "logos_gemini_bridge_count": gemini_bridge_count,
            "bridge_registry_total": bridge_reg.get("bridge_count") if bridge_reg else None,
            "generation_method_filter": "gemini_batch_v1",
            "research_only": True,
            "non_gating": True,
            "cost_lock": "no_new_gemini_bridge_batch; no_vertex_bulk; whitelist_scheduled_tasks_only",
            "registry_source": None,
        },
        "gcp_credit_guard": {
            "app_builder_credit_ui_percent": None,
            "billing_wallets_note": "App Builder trial credit != Vertex AI SKU; 100% UI does not cap all Google AI spend",
            "probe_source": None,
        },
    }

    if go:
        block["field"]["go_no_go"] = go.get("go_no_go")
        block["field"]["gate_ok"] = go.get("gate_ok")
        block["field"]["approval_decision"] = go.get("approval_decision")
        block["field"]["risk_mode"] = go.get("risk_mode")
        block["field"]["sources"]["trading_go_no_go"] = _rel(PATHS["trading_go_no_go"])
        if go.get("reasons"):
            block["conflict"]["items"].append(
                {"kind": "go_no_go_reasons", "value": go.get("reasons")}
            )

    if risk:
        block["field"]["regime_id"] = (
            risk.get("regime_id")
            or risk.get("primary_regime")
            or (risk.get("regime") or {}).get("id") if isinstance(risk.get("regime"), dict) else None
        )
        block["field"]["sources"]["risk_profile"] = _rel(PATHS["regime_trinity"])

    if lens:
        block["field"]["sources"]["lens_shadow_gate"] = _rel(PATHS["lens_shadow_gate"])
        block["lens"]["logos"]["status"] = lens.get("decision")
        lc = lens.get("latest_consensus") or {}
        block["lens"]["myeongni"]["status"] = (
            lc.get("consensus_sign") if isinstance(lc, dict) else None
        )
        block["lens"]["sasang"]["status"] = f"agreement_rate={lc.get('agreement_rate')}" if isinstance(lc, dict) else None
        block["lens"]["logos"]["status"] = lens.get("decision")
        if lens.get("blockers"):
            block["conflict"]["items"].append(
                {"kind": "lens_blockers", "value": lens.get("blockers")}
            )
        if lens.get("allow_a_track_binding") is False:
            block["conflict"]["principle"] = "observation_only_no_a_binding"

    # Final action heuristic (ops only, not live order)
    if go and go.get("go_no_go") == "NO_GO":
        block["final_action"]["decision"] = "HOLD"
        block["final_action"]["reason"] = "go_no_go=NO_GO"
    elif lens and lens.get("decision") == "KEEP_OBSERVATION_ONLY":
        block["final_action"]["decision"] = "WATCH"
        block["final_action"]["reason"] = "lens_shadow=KEEP_OBSERVATION_ONLY"
    elif go and go.get("go_no_go") == "GO" and go.get("gate_ok"):
        block["final_action"]["decision"] = "WATCH"
        block["final_action"]["reason"] = "gates_ok_observation_not_live_order"

    if bridge_reg and PATHS["logos_bridge_registry"].is_file():
        block["logos_research"]["registry_source"] = _rel(PATHS["logos_bridge_registry"])

    if billing_probe:
        ui = billing_probe.get("console_credit_ui") or {}
        note = ui.get("note")
        block["gcp_credit_guard"]["probe_source"] = _rel(PATHS["gcp_billing_probe"])
        block["gcp_credit_guard"]["project_id"] = billing_probe.get("project_id")
        if isinstance(note, str) and "100%" in note:
            block["gcp_credit_guard"]["app_builder_credit_ui_percent"] = 100

    missing = [k for k, p in PATHS.items() if not p.is_file()]
    if missing:
        block["missing_paths"] = missing

    return block


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--stdout-only", action="store_true")
    args = ap.parse_args()

    block = build_block()
    text = json.dumps(block, ensure_ascii=False, indent=2) + "\n"
    if args.stdout_only:
        print(text, end="")
    else:
        args.out_json.parent.mkdir(parents=True, exist_ok=True)
        args.out_json.write_text(text, encoding="utf-8")
        print(json.dumps({"ok": True, "out": str(args.out_json)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
