#!/usr/bin/env python3
"""Build patent/research brief from sasang 4-agent B-track artifact."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _safe_load(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return obj if isinstance(obj, dict) else {}


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    artifacts = root / "docs" / "final" / "artifacts"
    src = artifacts / "sasang_4agent_collision_btrack_protocol_latest.json"
    out_json = artifacts / "sasang_4agent_patent_brief_latest.json"
    out_md = artifacts / "sasang_4agent_patent_brief_latest.md"

    doc = _safe_load(src)
    if not doc:
        raise SystemExit(f"missing/invalid source artifact: {src}")

    exp = doc.get("experiment") if isinstance(doc.get("experiment"), dict) else {}
    res = doc.get("results") if isinstance(doc.get("results"), dict) else {}
    arch = doc.get("architecture") if isinstance(doc.get("architecture"), dict) else {}
    gate = doc.get("promotion_gate_hint") if isinstance(doc.get("promotion_gate_hint"), dict) else {}

    payload = {
        "schema": "sasang_4agent_patent_brief_v1",
        "generated_at_utc": _now_utc(),
        "source_artifact": str(src).replace("\\", "/"),
        "mode": doc.get("mode", "research_only"),
        "policy_label": doc.get("policy_label", "NON_GATING"),
        "core_claims": [
            "Intentional bias injection into four specialized agents (taeyang/soyang/taeeum/soeum).",
            "Conflict quantified as topological variance for regime-disagreement sensing.",
            "Asymmetric safety veto: defense agent can force HOLD against majority GO.",
            "Coordinator mode (Absolute Balance) as stateful arbitration, not fifth constitution.",
        ],
        "evidence_snapshot": {
            "ticks": exp.get("ticks"),
            "data_mode": exp.get("data_mode"),
            "mdd_baseline": res.get("mdd_baseline"),
            "mdd_model": res.get("mdd_model"),
            "mdd_reduction_abs": res.get("mdd_reduction_abs"),
            "mdd_reduction_pct_of_baseline": res.get("mdd_reduction_pct_of_baseline"),
            "p_bootstrap": res.get("mdd_reduction_p_value_bootstrap"),
            "p_permutation": res.get("mdd_reduction_p_value_permutation"),
            "significance_pass": res.get("statistical_significance_pass_p_lt_0_05"),
            "promotion_gate_decision": gate.get("decision"),
        },
        "safety_bounds": [
            "research_only boundary retained",
            "NON_GATING policy retained",
            "no auto-bridge to Track A",
        ],
        "next_actions": [
            "replicate across additional independent regime slices",
            "define claim language around asymmetrical veto and conflict metric",
            "prepare invention disclosure draft with reproducibility appendix",
        ],
    }

    out_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    md = []
    md.append("# Sasang 4-Agent Patent Brief")
    md.append("")
    md.append(f"- generated_at_utc: `{payload['generated_at_utc']}`")
    md.append(f"- source_artifact: `{payload['source_artifact']}`")
    md.append(f"- mode: `{payload['mode']}`")
    md.append(f"- policy_label: `{payload['policy_label']}`")
    md.append("")
    md.append("## Core Claims")
    for c in payload["core_claims"]:
        md.append(f"- {c}")
    md.append("")
    md.append("## Evidence Snapshot")
    for k, v in payload["evidence_snapshot"].items():
        md.append(f"- {k}: `{v}`")
    md.append("")
    md.append("## Safety Bounds")
    for s in payload["safety_bounds"]:
        md.append(f"- {s}")
    md.append("")
    md.append("## Next Actions")
    for n in payload["next_actions"]:
        md.append(f"- {n}")
    md.append("")
    out_md.write_text("\n".join(md), encoding="utf-8")

    print(str(out_json))
    print(str(out_md))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

