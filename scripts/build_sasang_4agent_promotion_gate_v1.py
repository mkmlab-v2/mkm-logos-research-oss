#!/usr/bin/env python3
"""Build promotion gate decision for sasang 4-agent architecture.

This gate now supports a conservative fast-track:
`NON_GATING -> GATING_VETO_ONLY` when protective evidence is strong
but full promotion requirements are not satisfied.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _safe_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return obj if isinstance(obj, dict) else {}


def _decide_gate(
    *,
    all_core_pass: bool,
    protective_subset_pass: bool,
    human_approved: bool,
) -> tuple[str, bool, bool, str]:
    if all_core_pass and human_approved:
        return ("A_TRACK_PROMOTED_WITH_HUMAN_APPROVAL", False, True, "track_a_controlled_bridge")
    if all_core_pass:
        return ("A_TRACK_PROMOTION_CANDIDATE_READY", True, False, "candidate_waiting_human_review")
    if protective_subset_pass and human_approved:
        return ("GATING_VETO_ONLY_ACTIVE_WITH_HUMAN_APPROVAL", False, False, "veto_only_non_directional")
    if protective_subset_pass:
        return ("GATING_VETO_ONLY_CANDIDATE", True, False, "veto_only_non_directional")
    return ("HOLD", True, False, "hold_no_promotion")


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    art = root / "docs" / "final" / "artifacts"
    protocol_path = art / "sasang_4agent_collision_btrack_protocol_latest.json"
    brief_path = art / "sasang_4agent_patent_brief_latest.json"
    disclosure_path = art / "sasang_4agent_invention_disclosure_latest.json"
    fusion_gate_path = art / "sasang_4agent_fusion_gate_latest.json"
    human_approval_path = art / "sasang_4agent_human_approval_latest.json"
    out_json = art / "sasang_4agent_promotion_gate_latest.json"
    out_md = art / "sasang_4agent_promotion_gate_latest.md"

    protocol = _safe_json(protocol_path)
    brief = _safe_json(brief_path)
    disclosure = _safe_json(disclosure_path)
    fusion_gate = _safe_json(fusion_gate_path)
    human_approval = _safe_json(human_approval_path)
    if not protocol:
        raise SystemExit(f"missing protocol artifact: {protocol_path}")

    exp = protocol.get("experiment") if isinstance(protocol.get("experiment"), dict) else {}
    res = protocol.get("results") if isinstance(protocol.get("results"), dict) else {}
    gate = protocol.get("promotion_gate_hint") if isinstance(protocol.get("promotion_gate_hint"), dict) else {}

    ticks = int(exp.get("ticks") or 0)
    sig_pass = bool(res.get("statistical_significance_pass_p_lt_0_05"))
    mdd_reduction_abs = float(res.get("mdd_reduction_abs") or 0.0)
    research_only = str(protocol.get("mode") or "").lower() == "research_only"
    non_gating = str(protocol.get("policy_label") or "").upper() == "NON_GATING"
    btrack_candidate = str(gate.get("decision") or "").upper() == "GO_CANDIDATE"
    human_approved = bool(human_approval.get("approved")) and (
        str(human_approval.get("schema") or "") == "sasang_4agent_human_approval_v1"
    )

    checks = {
        "ticks_gte_300": ticks >= 300,
        "significance_pass": sig_pass,
        "mdd_reduction_positive": mdd_reduction_abs > 0.0,
        "btrack_candidate_go": btrack_candidate,
        "patent_brief_present": bool(brief),
        "invention_disclosure_present": bool(disclosure),
        "policy_research_only": research_only,
        "policy_non_gating": non_gating,
        "fusion_gate_pass": str(fusion_gate.get("decision") or "") == "FUSION_GATE_PASS",
        "human_approval_present": bool(human_approval),
        "human_approval_approved": human_approved,
    }

    # Promotion to A-track requires explicit human gate even if all checks pass.
    all_core_pass = all(
        checks[k]
        for k in [
            "ticks_gte_300",
            "significance_pass",
            "mdd_reduction_positive",
            "btrack_candidate_go",
            "patent_brief_present",
            "invention_disclosure_present",
            "policy_research_only",
            "policy_non_gating",
            "fusion_gate_pass",
        ]
    )
    protective_subset_pass = all(
        checks[k]
        for k in [
            "ticks_gte_300",
            "significance_pass",
            "mdd_reduction_positive",
            "policy_research_only",
            "policy_non_gating",
            "fusion_gate_pass",
        ]
    )
    decision, human_review_gate_required, auto_bridge_allowed, gating_scope = _decide_gate(
        all_core_pass=all_core_pass,
        protective_subset_pass=protective_subset_pass,
        human_approved=human_approved,
    )

    payload = {
        "schema": "sasang_4agent_promotion_gate_v1",
        "generated_at_utc": _now_utc(),
        "inputs": {
            "protocol_artifact": str(protocol_path).replace("\\", "/"),
            "patent_brief_artifact": str(brief_path).replace("\\", "/"),
            "invention_disclosure_artifact": str(disclosure_path).replace("\\", "/"),
            "fusion_gate_artifact": str(fusion_gate_path).replace("\\", "/"),
            "human_approval_artifact": str(human_approval_path).replace("\\", "/"),
        },
        "checks": checks,
        "summary": {
            "ticks": ticks,
            "mdd_reduction_abs": mdd_reduction_abs,
            "significance_pass": sig_pass,
            "btrack_decision": gate.get("decision"),
        },
        "decision": decision,
        "gating_scope": gating_scope,
        "human_review_gate_required": human_review_gate_required,
        "auto_bridge_allowed": auto_bridge_allowed,
        "next_step": (
            "Bridge is permitted by explicit human approval; execute controlled Track A rollout with monitoring."
            if decision == "A_TRACK_PROMOTED_WITH_HUMAN_APPROVAL"
            else (
                "Prepare human review packet and explicit approval record before any Track A bridge."
                if decision == "A_TRACK_PROMOTION_CANDIDATE_READY"
                else (
                    "Protective evidence passed; allow veto-only gating after human approval, directional auto-bridge remains forbidden."
                    if decision in {"GATING_VETO_ONLY_CANDIDATE", "GATING_VETO_ONLY_ACTIVE_WITH_HUMAN_APPROVAL"}
                    else "Address failed checks and rerun B-track protocol."
                )
            )
        ),
    }
    if human_approved:
        payload["approved_at_utc"] = human_approval.get("approved_at_utc")
        payload["approved_by"] = human_approval.get("approver")
        payload["human_approval_ref"] = str(human_approval_path).replace("\\", "/")

    out_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    md = []
    md.append("# Sasang 4-Agent Promotion Gate")
    md.append("")
    md.append(f"- generated_at_utc: `{payload['generated_at_utc']}`")
    md.append(f"- decision: `{payload['decision']}`")
    md.append(f"- human_review_gate_required: `{payload['human_review_gate_required']}`")
    md.append(f"- auto_bridge_allowed: `{payload['auto_bridge_allowed']}`")
    md.append("")
    md.append("## Checks")
    for k, v in checks.items():
        md.append(f"- {k}: `{v}`")
    md.append("")
    md.append("## Summary")
    for k, v in payload["summary"].items():
        md.append(f"- {k}: `{v}`")
    md.append("")
    md.append(f"## Next Step\n- {payload['next_step']}")
    md.append("")
    out_md.write_text("\n".join(md), encoding="utf-8")

    print(str(out_json))
    print(str(out_md))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

