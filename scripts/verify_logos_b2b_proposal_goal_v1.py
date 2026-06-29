#!/usr/bin/env python3
"""Track B goal verifier — back-track B2B proposal claims against clause_refs and barriers."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
LOOP_SPEC = ROOT / "docs/final/artifacts/logos_b2b_proposal_evolution_loop_spec_v1.json"
DEFAULT_IN = ROOT / "docs/final/artifacts/logos_b2b_proposal_logic_artifact_v1_latest.json"
DEFAULT_OUT = ROOT / "reports/logos_b2b_proposal_goal_verifier_v1_latest.json"

FORBIDDEN_B2B = (
    "환자 유치",
    "환자 소개",
    "소개비",
    "완치",
    "효능을 보장",
    "매매",
    "실매매",
    "수익 보장",
    "투자자문",
)

NEGATION_AFTER_TERM = re.compile(
    r"(아닙|아니|금지|배제|하지 않|없|제외)",
    re.I,
)


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (json.JSONDecodeError, OSError):
        return None


def _valid_clause_refs(loop_spec: dict[str, Any]) -> set[str]:
    reg = loop_spec.get("clause_ref_registry") or {}
    return set(reg.keys())


def _verify_claim(
    claim: dict[str, Any],
    *,
    valid_refs: set[str],
    barrier_ok: dict[str, bool],
) -> dict[str, Any]:
    body = str(claim.get("body_ko") or "")
    labels = claim.get("labels") or []
    refs = claim.get("clause_refs") or []
    barriers = claim.get("barrier_ids") or []

    issues: list[str] = []
    if "[HYPO]" not in body:
        issues.append("missing_HYPO_tag")
    if "TRACK_B" not in labels:
        issues.append("missing_TRACK_B_label")

    orphan = [r for r in refs if r not in valid_refs]
    if orphan:
        issues.append(f"orphan_clause_refs:{','.join(orphan)}")

    forbidden: list[str] = []
    for w in FORBIDDEN_B2B:
        if w not in body or claim.get("claim_id") == "CLAIM-HUB-FORBIDDEN-DRIFT":
            continue
        idx = body.find(w)
        tail = body[idx + len(w) : idx + len(w) + 24]
        if NEGATION_AFTER_TERM.search(tail):
            continue
        forbidden.append(w)
    if forbidden:
        issues.append(f"forbidden_terms:{','.join(forbidden)}")

    for bid in barriers:
        if bid in barrier_ok and not barrier_ok[bid]:
            issues.append(f"barrier_fail:{bid}")

    if "ORPHAN" in ",".join(refs):
        issues.append("explicit_orphan_ref")

    ok = not issues
    return {
        "claim_id": claim.get("claim_id"),
        "ok": ok,
        "status": "PASS" if ok else "FAIL",
        "issues": issues,
        "clause_refs": refs,
    }


def verify(
    artifact: dict[str, Any],
    *,
    loop_spec: dict[str, Any],
    barrier_audit: dict[str, Any] | None,
) -> dict[str, Any]:
    valid_refs = _valid_clause_refs(loop_spec)
    barrier_ok: dict[str, bool] = {}
    if barrier_audit:
        for b in barrier_audit.get("barriers") or []:
            if isinstance(b, dict) and b.get("id"):
                barrier_ok[str(b["id"])] = bool(b.get("ok"))

    claim_results = []
    for claim in artifact.get("proposal_claims") or []:
        if not isinstance(claim, dict):
            continue
        claim_results.append(
            _verify_claim(claim, valid_refs=valid_refs, barrier_ok=barrier_ok)
        )

    all_claims_ok = all(c["ok"] for c in claim_results) if claim_results else False
    barrier_audit_ok = (barrier_audit or {}).get("ok") is True
    logos_transplant = artifact.get("logos_reasoning_transplant") or {}
    transplant_ok = logos_transplant.get("pedagogical_only") is True

    policy_issues: list[str] = []
    if artifact.get("track_a_bridge"):
        policy_issues.append("track_a_bridge_forbidden")
    if not artifact.get("research_only"):
        policy_issues.append("research_only_required")
    if not artifact.get("non_gating"):
        policy_issues.append("non_gating_required")

    overall_ok = all_claims_ok and barrier_audit_ok and transplant_ok and not policy_issues

    return {
        "schema": "logos_b2b_proposal_goal_verifier_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "non_gating": True,
        "research_only": True,
        "backtracking": {
            "mode": "clause_ref_and_barrier_audit",
            "valid_clause_ref_count": len(valid_refs),
            "barrier_audit_ok": barrier_audit_ok,
            "logos_pedagogical_transplant_only": transplant_ok,
        },
        "claims": claim_results,
        "policy_issues": policy_issues,
        "ok": overall_ok,
        "verdict": "PROMOTE_CANDIDATE" if overall_ok else "REFINE_REQUIRED",
        "reproduce": "py scripts/verify_logos_b2b_proposal_goal_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--in", dest="in_path", type=Path, default=DEFAULT_IN)
    ap.add_argument("--loop-spec", type=Path, default=LOOP_SPEC)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    artifact = _load(args.in_path)
    loop_spec = _load(args.loop_spec)
    if not artifact:
        raise SystemExit(f"missing artifact: {args.in_path}")
    if not loop_spec:
        raise SystemExit(f"missing loop spec: {args.loop_spec}")

    inputs = loop_spec.get("inputs") or {}
    barrier_path = ROOT / str(inputs.get("b2b_barrier_audit", "")).replace("\\", "/")
    barrier_audit = _load(barrier_path)

    doc = verify(artifact, loop_spec=loop_spec, barrier_audit=barrier_audit)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {"ok": doc["ok"], "verdict": doc["verdict"], "out": str(args.out.relative_to(ROOT)).replace("\\", "/")},
            ensure_ascii=False,
        )
    )
    return 0 if doc["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
