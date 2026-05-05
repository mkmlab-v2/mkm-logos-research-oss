#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build ``promotion_preflight_v1_latest.json`` for B-track atomic promotion gating.

Reads proposal JSON (when present) + control tower JSON, emits schema ``btrack_promotion_preflight_v1``.
Exit code is **0** when the output file is written (even if ``result`` is FAIL); non-zero only on I/O or invalid inputs.

Contract matches ``Apply-BtrackPromotionAtomic.ps1``:
``py run_btrack_promotion_preflight_v1.py --proposal P --control-tower C --out O``
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def read_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return json.loads(raw.replace("\ufeff", ""))


def sha256_file(path: Path) -> str | None:
    if not path.is_file():
        return None
    h = hashlib.sha256()
    try:
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                h.update(chunk)
        return h.hexdigest()
    except OSError:
        return None


def resolve_proposal_path(explicit: Path, root: Path) -> tuple[Path | None, dict[str, Any] | None]:
    """Return (path, doc) if a proposal JSON can be loaded."""
    if explicit.is_file():
        doc = read_json(explicit)
        return explicit, doc
    receipt = read_json(root / "reports/constitution/btrack_pilot/auto_scientist/promotion_apply_receipt_latest.json")
    if receipt and receipt.get("proposal_path"):
        alt = Path(str(receipt["proposal_path"]))
        if alt.is_file():
            return alt, read_json(alt)
    return None, None


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    default_proposal = root / "reports/constitution/btrack_pilot/auto_scientist/promotion_proposal_v1_latest.json"
    default_ct = root / "docs/final/artifacts/control_tower_latest.json"
    default_out = root / "docs/final/artifacts/promotion_preflight_v1_latest.json"

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--proposal", type=Path, default=default_proposal)
    ap.add_argument("--control-tower", type=Path, default=default_ct)
    ap.add_argument("--out", type=Path, default=default_out)
    args = ap.parse_args()

    ct_path = args.control_tower.resolve()
    ct = read_json(ct_path)
    if ct is None:
        print(f"run_btrack_promotion_preflight_v1: control tower not found: {ct_path}", file=sys.stderr)
        return 1

    prop_path_resolved, proposal = resolve_proposal_path(args.proposal.resolve(), root)

    report = ct.get("report") if isinstance(ct.get("report"), dict) else {}
    pr = ct.get("promotion_readiness") if isinstance(ct.get("promotion_readiness"), dict) else {}
    sr = ct.get("strategy_runtime") if isinstance(ct.get("strategy_runtime"), dict) else {}
    ops = ct.get("ops_summary") if isinstance(ct.get("ops_summary"), dict) else {}
    gate_snap = report.get("event_outcome_gate_snapshot") if isinstance(report.get("event_outcome_gate_snapshot"), dict) else {}
    autopush = report.get("autopush_latest_snapshot") if isinstance(report.get("autopush_latest_snapshot"), dict) else {}

    human_r = gate_snap.get("human_verified_ratio")
    if human_r is None:
        human_r = autopush.get("event_outcome_human_verified_ratio")
    if human_r is None:
        human_r = ops.get("human_verified_ratio")

    syn_r = gate_snap.get("synthetic_ratio")
    if syn_r is None:
        syn_r = autopush.get("event_outcome_synthetic_ratio")
    if syn_r is None:
        syn_r = ops.get("synthetic_ratio")

    readiness_status = str(pr.get("status") or ops.get("promotion_readiness") or "")
    threshold_health = str(sr.get("threshold_health") or ops.get("strategy_threshold_health") or "")

    if proposal:
        proposal_status = str(proposal.get("status") or "")
        decision = str(proposal.get("decision_recommendation") or "")
        cand_sel = proposal.get("candidate_selection") if isinstance(proposal.get("candidate_selection"), dict) else {}
        selected = str(cand_sel.get("selected_candidate_report") or "").strip()
    else:
        proposal_status = ""
        decision = ""
        selected = ""

    eff_status = proposal_status or str(report.get("proposal_status") or "")
    eff_decision = decision or str(report.get("gate_decision") or "")
    if not selected:
        selected = str(report.get("selected_candidate") or "").strip()

    candidate_path = Path(selected) if selected else None
    cand_sha = sha256_file(candidate_path) if candidate_path else None

    checks: dict[str, Any] = {
        "proposal_status": eff_status,
        "proposal_decision_recommendation": eff_decision,
        "promotion_readiness": readiness_status,
        "strategy_threshold_health": threshold_health or "unknown",
        "event_outcome_human_verified_ratio": human_r,
        "event_outcome_synthetic_ratio": syn_r,
        "selected_candidate_report": selected,
        "selected_candidate_sha256": cand_sha,
    }

    reasons: list[str] = []

    if eff_status != "PENDING_APPROVAL":
        reasons.append("proposal_not_approvable")

    if eff_decision != "PROPOSE_PROMOTION":
        reasons.append("proposal_not_approvable")

    if readiness_status != "GO_READY":
        reasons.append("promotion_readiness_not_go_ready")

    if threshold_health and threshold_health != "healthy":
        reasons.append("strategy_threshold_not_healthy")

    if not selected:
        reasons.append("selected_candidate_missing")
    elif cand_sha is None:
        reasons.append("selected_candidate_file_missing")

    # De-dupe while preserving order
    seen: set[str] = set()
    deduped = []
    for r in reasons:
        if r not in seen:
            seen.add(r)
            deduped.append(r)
    reasons = deduped

    result = "PASS" if not reasons else "FAIL"

    out_doc = {
        "schema": "btrack_promotion_preflight_v1",
        "generated_at_utc": _utc_now(),
        "proposal_path": str(prop_path_resolved) if prop_path_resolved else str(args.proposal.resolve()),
        "control_tower_path": str(ct_path),
        "checks": checks,
        "result": result,
        "reasons": reasons,
    }

    out_path = args.out.resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {out_path}")
    print(f"result={result} reasons={reasons}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
