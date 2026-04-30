#!/usr/bin/env python3
"""Build invention disclosure draft (claim-centered) for Sasang 4-agent model."""

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
    brief_path = art / "sasang_4agent_patent_brief_latest.json"
    brief = _safe_json(brief_path)
    if not brief:
        raise SystemExit(f"missing/invalid brief: {brief_path}")

    ev = brief.get("evidence_snapshot") if isinstance(brief.get("evidence_snapshot"), dict) else {}
    core_claims = brief.get("core_claims") if isinstance(brief.get("core_claims"), list) else []
    safety = brief.get("safety_bounds") if isinstance(brief.get("safety_bounds"), list) else []

    disclosure_json = art / "sasang_4agent_invention_disclosure_latest.json"
    disclosure_md = art / "sasang_4agent_invention_disclosure_latest.md"

    payload = {
        "schema": "sasang_4agent_invention_disclosure_v1",
        "generated_at_utc": _now_utc(),
        "title": "Asymmetric Safety Arbitration Architecture with Intentional Bias Injection in Four-Agent Conflict System",
        "technical_field": "AI decision systems, risk-aware ensemble arbitration, regime-aware policy control",
        "problem_statement": (
            "Conventional single-model or symmetric ensemble systems fail to preserve safety under regime shocks; "
            "majority voting can override defensive signals and amplify drawdown."
        ),
        "proposed_solution": {
            "summary": (
                "Inject intentional computational bias into four specialized agents, quantify inter-agent conflict via "
                "topological variance, and apply asymmetric defense veto through an Absolute Balance coordinator mode."
            ),
            "core_claims": core_claims,
            "safety_bounds": safety,
        },
        "claim_set_draft": [
            {
                "id": "claim_1_independent",
                "type": "independent",
                "text": (
                    "A method for machine decision arbitration comprising: generating four specialized agent outputs "
                    "under intentionally distinct bias constraints; computing a conflict metric as variance over said outputs; "
                    "and enforcing an asymmetric veto rule wherein a designated defense agent signal forces HOLD regardless "
                    "of majority directional outputs."
                ),
            },
            {
                "id": "claim_2_dependent_bias",
                "type": "dependent",
                "text": (
                    "The method of claim 1, wherein bias constraints include at least one of macro-horizon weighting, "
                    "momentum weighting, similarity-threshold activation, and drawdown-penalty amplification."
                ),
            },
            {
                "id": "claim_3_dependent_conflict",
                "type": "dependent",
                "text": (
                    "The method of claim 1, wherein the conflict metric is tracked per regime window and used as a "
                    "chaos/disagreement indicator for policy gating."
                ),
            },
            {
                "id": "claim_4_dependent_safety_mode",
                "type": "dependent",
                "text": (
                    "The method of claim 1, wherein the coordinator operates as a stateful arbitration mode and is "
                    "explicitly not treated as an additional constitution class."
                ),
            },
        ],
        "evidence_anchor": {
            "ticks": ev.get("ticks"),
            "mdd_baseline": ev.get("mdd_baseline"),
            "mdd_model": ev.get("mdd_model"),
            "mdd_reduction_abs": ev.get("mdd_reduction_abs"),
            "mdd_reduction_pct_of_baseline": ev.get("mdd_reduction_pct_of_baseline"),
            "p_permutation": ev.get("p_permutation"),
            "significance_pass": ev.get("significance_pass"),
            "decision": ev.get("promotion_gate_decision"),
        },
        "legal_note": (
            "This draft is a technical invention-disclosure scaffold for internal review and does not constitute legal advice."
        ),
        "source_refs": [
            str(brief_path).replace("\\", "/"),
            str((art / "sasang_4agent_collision_btrack_protocol_latest.json")).replace("\\", "/"),
        ],
    }

    disclosure_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    md: list[str] = []
    md.append("# Sasang 4-Agent Invention Disclosure (Draft)")
    md.append("")
    md.append(f"- generated_at_utc: `{payload['generated_at_utc']}`")
    md.append(f"- title: `{payload['title']}`")
    md.append(f"- technical_field: `{payload['technical_field']}`")
    md.append("")
    md.append("## Problem Statement")
    md.append(payload["problem_statement"])
    md.append("")
    md.append("## Proposed Solution")
    md.append(payload["proposed_solution"]["summary"])
    md.append("")
    md.append("## Claim Set Draft")
    for c in payload["claim_set_draft"]:
        md.append(f"- {c['id']} ({c['type']}): {c['text']}")
    md.append("")
    md.append("## Evidence Anchor")
    for k, v in payload["evidence_anchor"].items():
        md.append(f"- {k}: `{v}`")
    md.append("")
    md.append("## Safety Bounds")
    for s in payload["proposed_solution"]["safety_bounds"]:
        md.append(f"- {s}")
    md.append("")
    md.append("## Legal Note")
    md.append(payload["legal_note"])
    md.append("")

    disclosure_md.write_text("\n".join(md), encoding="utf-8")
    print(str(disclosure_json))
    print(str(disclosure_md))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

