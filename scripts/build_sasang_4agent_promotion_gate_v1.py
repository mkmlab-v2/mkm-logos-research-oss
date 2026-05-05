#!/usr/bin/env python3
"""Build promotion gate decision for sasang 4-agent architecture."""

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


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    art = root / "docs" / "final" / "artifacts"
    protocol_path = art / "sasang_4agent_collision_btrack_protocol_latest.json"
    brief_path = art / "sasang_4agent_patent_brief_latest.json"
    disclosure_path = art / "sasang_4agent_invention_disclosure_latest.json"
    fusion_gate_path = art / "sasang_4agent_fusion_gate_latest.json"
    out_json = art / "sasang_4agent_promotion_gate_latest.json"
    out_md = art / "sasang_4agent_promotion_gate_latest.md"

    protocol = _safe_json(protocol_path)
    brief = _safe_json(brief_path)
    disclosure = _safe_json(disclosure_path)
    fusion_gate = _safe_json(fusion_gate_path)
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
    decision = "A_TRACK_PROMOTION_CANDIDATE_READY" if all_core_pass else "HOLD"
    human_review_gate_required = True
    auto_bridge_allowed = False

    payload = {
        "schema": "sasang_4agent_promotion_gate_v1",
        "generated_at_utc": _now_utc(),
        "inputs": {
            "protocol_artifact": str(protocol_path).replace("\\", "/"),
            "patent_brief_artifact": str(brief_path).replace("\\", "/"),
            "invention_disclosure_artifact": str(disclosure_path).replace("\\", "/"),
            "fusion_gate_artifact": str(fusion_gate_path).replace("\\", "/"),
        },
        "checks": checks,
        "summary": {
            "ticks": ticks,
            "mdd_reduction_abs": mdd_reduction_abs,
            "significance_pass": sig_pass,
            "btrack_decision": gate.get("decision"),
        },
        "decision": decision,
        "human_review_gate_required": human_review_gate_required,
        "auto_bridge_allowed": auto_bridge_allowed,
        "next_step": (
            "Prepare human review packet and explicit approval record before any Track A bridge."
            if decision == "A_TRACK_PROMOTION_CANDIDATE_READY"
            else "Address failed checks and rerun B-track protocol."
        ),
    }

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

