#!/usr/bin/env python3
"""Build web_ops_regime_gate_v1 report from portal probe JSON artifacts."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
import sys

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.web_ops_regime_classifier_v1 import probe_from_portal_json, worst_final_action


DEFAULT_OUT = ROOT / "reports/web_ops_regime_gate_v1_latest.json"
DEFAULT_NEBIUS = ROOT / "reports/nvidia_nebius_console_setup_latest.json"
DEFAULT_NEBIUS_BENEFIT = ROOT / "reports/nvidia_nebius_benefit_request_latest.json"
DEFAULT_AZURE = ROOT / "reports/azure_gpu_feasibility_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _merge_nebius_docs(*docs: dict[str, Any]) -> dict[str, Any]:
    merged: dict[str, Any] = {}
    for doc in docs:
        if doc:
            merged.update(doc)
    hints = merged.get("welcome_email_summary") or {}
    quota = hints.get("default_quota_no_extra_approval") or {}
    if quota:
        merged.setdefault("gpu_limits_mentioned", [])
        for key, label in (("nvidia_h200", "H200"), ("nvidia_h100", "H100"), ("nvidia_l40s", "L40S")):
            if quota.get(key) and label not in merged["gpu_limits_mentioned"]:
                merged["gpu_limits_mentioned"].append(label)
    if merged.get("billing_complete"):
        merged["payment_configured"] = True
    return merged


def _azure_probe(doc: dict[str, Any]) -> dict[str, Any]:
    blocker = str(doc.get("gpu_vm_blocker") or "")
    body = blocker + " " + json.dumps(doc.get("credits") or {}, ensure_ascii=False)
    synthetic = {
        "url": "https://portal.azure.com/",
        "console_title": str(doc.get("subscription_name") or "azure_portal"),
        "billing_snippet": body[:800],
        "payment_configured": True,
        "feasibility_report": True,
        "artifact_read_only": True,
        "human_gate": None,
        "gpu_vm_feasible_now": doc.get("gpu_vm_feasible_now"),
    }
    probe = probe_from_portal_json(
        probe_id="azure_gpu_feasibility",
        portal="azure",
        doc=synthetic,
        intended_action="observe",
    )
    if doc.get("gpu_vm_feasible_now") is False:
        probe["repair_v2"]["forbidden_actions"] = list(
            set(probe["repair_v2"]["forbidden_actions"]) | {"create_vm", "create_gpu"}
        )
        probe["lens_hints"]["myeongni"]["flow_hint"] = "quota_zero_hold_gpu_spinup"
    return probe


def build_gate(
    *,
    nebius_doc: dict[str, Any] | None = None,
    azure_doc: dict[str, Any] | None = None,
    extra_probes: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    probes: list[dict[str, Any]] = []
    evidence: dict[str, str] = {}

    if nebius_doc:
        probes.append(
            probe_from_portal_json(
                probe_id="nebius_console",
                portal="nebius",
                doc=nebius_doc,
                intended_action="observe",
            )
        )
        evidence["nebius_console_setup"] = str(DEFAULT_NEBIUS)

    if azure_doc:
        probes.append(_azure_probe(azure_doc))
        evidence["azure_gpu_feasibility"] = str(DEFAULT_AZURE)

    for item in extra_probes or []:
        if isinstance(item, dict) and item.get("probe_id"):
            probes.append(item)

    if not probes:
        raise ValueError("no_probe_inputs")

    actions = [str(p.get("final_action") or "HOLD_UNKNOWN") for p in probes]
    worst = worst_final_action(actions)
    hold_actions = {
        "HOLD_HUMAN",
        "HOLD_PAYMENT",
        "HOLD_AUTH",
        "HOLD_DESTRUCTIVE",
        "HOLD_POINTER_DRIFT",
        "HOLD_UNKNOWN",
    }
    gate_pass = worst in {"ALLOW_READ", "ALLOW_PREFILL"}
    combined_all_passed = all(p.get("outcome_class") == "pass_candidate" for p in probes) and gate_pass

    return {
        "schema": "web_ops_regime_gate_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "track_wall": "b_track_research",
        "cost_policy": {
            "no_gpu_spinup": True,
            "no_new_billing_charges": True,
            "nebius_prepaid_only": True,
            "human_tier3_only_for": [
                "payment_card_tier3",
                "auth_oauth_tier3",
                "captcha_turnstile_tier3",
                "destructive_submit_human",
            ],
        },
        "probes": probes,
        "conflict_resolver": {
            "worst_final_action": worst,
            "probe_count": len(probes),
            "note": "Field→Lens hints→Conflict: worst HOLD wins; read-only portals should resolve ALLOW_READ.",
        },
        "combined_all_passed": combined_all_passed,
        "gate_pass": gate_pass,
        "evidence_bundle": evidence,
        "operator_hint_ko": (
            "GPU/결제 자동화 금지. ALLOW_READ·ALLOW_PREFILL만 에이전트 허용."
            if gate_pass
            else f"자동화 중단: {worst} — Tier-3 Human 또는 API 경로로 전환."
        ),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--nebius-json", type=Path, default=DEFAULT_NEBIUS)
    ap.add_argument("--nebius-benefit-json", type=Path, default=DEFAULT_NEBIUS_BENEFIT)
    ap.add_argument("--azure-json", type=Path, default=DEFAULT_AZURE)
    ap.add_argument("--skip-azure", action="store_true")
    ap.add_argument("--cdp-probe-json", type=Path, default=None)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    nebius = _merge_nebius_docs(_read_json(args.nebius_json), _read_json(args.nebius_benefit_json))
    azure = {} if args.skip_azure else _read_json(args.azure_json)
    if not nebius and not azure:
        print(json.dumps({"ok": False, "error": "no_probe_inputs"}, ensure_ascii=False))
        return 2

    extra: list[dict[str, Any]] = []
    if args.cdp_probe_json and args.cdp_probe_json.is_file():
        cdp_doc = _read_json(args.cdp_probe_json)
        cdp_probe = cdp_doc.get("probe")
        if isinstance(cdp_probe, dict):
            extra.append(cdp_probe)

    doc = build_gate(nebius_doc=nebius or None, azure_doc=azure or None, extra_probes=extra or None)
    if args.cdp_probe_json and extra:
        doc["evidence_bundle"]["web_ops_regime_cdp_probe"] = str(args.cdp_probe_json)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "out": str(args.out),
                "gate_pass": doc["gate_pass"],
                "worst_final_action": doc["conflict_resolver"]["worst_final_action"],
                "probe_count": doc["conflict_resolver"]["probe_count"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
