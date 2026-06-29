#!/usr/bin/env python3
"""Track B self-refinement — merge verifier-passed claims into MASTER_SUMMARY (deterministic)."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ARTIFACT = ROOT / "docs/final/artifacts/logos_b2b_proposal_logic_artifact_v1_latest.json"
DEFAULT_VERIFIER = ROOT / "reports/logos_b2b_proposal_goal_verifier_v1_latest.json"
DEFAULT_JSON_OUT = ROOT / "docs/final/artifacts/logos_b2b_proposal_master_summary_v1_latest.json"
DEFAULT_MD_OUT = ROOT / "reports/logos_b2b_proposal_master_summary_v1_latest.md"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (json.JSONDecodeError, OSError):
        return None


def _build_md(summary: dict[str, Any]) -> str:
    lines = [
        "# Logos → B2B Proposal MASTER_SUMMARY (Track B)",
        "",
        f"> 생성 `{summary.get('generated_at_utc')}` · **NON_GATING** · A-track·실매매 자동 합선 금지",
        "",
        "## 승격된 논리 클레임",
        "",
    ]
    for c in summary.get("promoted_claims") or []:
        lines.append(f"### `{c.get('claim_id')}`")
        lines.append("")
        lines.append(str(c.get("body_ko", "")))
        lines.append("")
        refs = c.get("clause_refs") or []
        lines.append(f"- clause_refs: {', '.join(refs)}")
        lines.append("")
    lines.append("## Logos 구조 이식 (pedagogical only)")
    lines.append("")
    transplant = summary.get("logos_structure_transplant") or {}
    lines.append(f"- pattern: `{transplant.get('pattern_id')}`")
    lines.append(f"- evidence_anchor_count: `{transplant.get('evidence_anchor_count')}`")
    lines.append(f"- pedagogical_only: `{transplant.get('pedagogical_only')}`")
    lines.append("")
    lines.append("---")
    lines.append(f"재현: `{summary.get('reproduce')}`")
    lines.append("")
    return "\n".join(lines)


def merge(
    artifact: dict[str, Any],
    verifier: dict[str, Any],
) -> dict[str, Any]:
    if not verifier.get("ok"):
        return {
            "schema": "logos_b2b_proposal_master_summary_v1",
            "version": "1.0.0",
            "generated_at_utc": _utc(),
            "promoted": False,
            "reason": "goal_verifier_not_pass",
            "verdict": verifier.get("verdict"),
            "reproduce": "py scripts/run_logos_b2b_proposal_evolution_loop_v1.py",
        }

    passed_ids = {c["claim_id"] for c in verifier.get("claims") or [] if c.get("ok")}
    promoted = [
        c
        for c in artifact.get("proposal_claims") or []
        if isinstance(c, dict) and c.get("claim_id") in passed_ids
    ]

    return {
        "schema": "logos_b2b_proposal_master_summary_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "non_gating": True,
        "research_only": True,
        "track_a_bridge": False,
        "live_trading_bridge": False,
        "promoted": True,
        "b2b_target_id": artifact.get("b2b_target_id"),
        "promoted_claims": promoted,
        "promoted_claim_count": len(promoted),
        "logos_structure_transplant": artifact.get("logos_reasoning_transplant"),
        "verifier_pointer": "reports/logos_b2b_proposal_goal_verifier_v1_latest.json",
        "artifact_pointer": "docs/final/artifacts/logos_b2b_proposal_logic_artifact_v1_latest.json",
        "human_commander_gate": {
            "final_authority": "human_commander",
            "external_send": "HOLD",
            "note": "MASTER_SUMMARY 승격 ≠ 외부 송출·Track A 승격",
        },
        "reproduce": "py scripts/merge_logos_b2b_proposal_master_summary_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--artifact", type=Path, default=DEFAULT_ARTIFACT)
    ap.add_argument("--verifier", type=Path, default=DEFAULT_VERIFIER)
    ap.add_argument("--json-out", type=Path, default=DEFAULT_JSON_OUT)
    ap.add_argument("--md-out", type=Path, default=DEFAULT_MD_OUT)
    ap.add_argument("--force-on-fail", action="store_true", help="Write refusal doc even when verifier fails")
    args = ap.parse_args()

    artifact = _load(args.artifact)
    verifier = _load(args.verifier)
    if not artifact:
        raise SystemExit(f"missing artifact: {args.artifact}")
    if not verifier:
        raise SystemExit(f"missing verifier: {args.verifier}")

    summary = merge(artifact, verifier)
    promoted = summary.get("promoted") is True

    args.json_out.parent.mkdir(parents=True, exist_ok=True)
    args.json_out.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if promoted or args.force_on_fail:
        args.md_out.parent.mkdir(parents=True, exist_ok=True)
        if promoted:
            args.md_out.write_text(_build_md(summary), encoding="utf-8")
        else:
            args.md_out.write_text(
                f"# MASTER_SUMMARY — 승격 거부\n\nverdict: `{summary.get('verdict')}`\n",
                encoding="utf-8",
            )

    print(
        json.dumps(
            {
                "ok": promoted,
                "promoted": promoted,
                "json_out": str(args.json_out.relative_to(ROOT)).replace("\\", "/"),
                "md_out": str(args.md_out.relative_to(ROOT)).replace("\\", "/") if promoted else None,
            },
            ensure_ascii=False,
        )
    )
    return 0 if promoted else 1


if __name__ == "__main__":
    raise SystemExit(main())
