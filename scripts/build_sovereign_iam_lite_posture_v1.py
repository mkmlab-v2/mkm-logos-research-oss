#!/usr/bin/env python3
"""Sovereign IAM-lite posture report v1 — B-track [HYPO] control plane only.

Evaluates account metadata against policy rules. Never reads or stores credential
plaintext (data plane excluded). Phase 2 (DPAPI ingest, HIBP live) is out of scope.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REGISTRY = ROOT / "docs/final/artifacts/sovereign_iam_lite_accounts_registry_v1_example.json"
DEFAULT_POLICY = ROOT / "docs/final/artifacts/sovereign_iam_lite_policy_v1_draft.json"
DEFAULT_REPORT = ROOT / "reports/sovereign_iam_lite_posture_latest.json"
DEFAULT_ARTIFACT = ROOT / "docs/final/artifacts/sovereign_iam_lite_posture_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _rule_matches(account: dict[str, Any], rule: dict[str, Any]) -> bool:
    if account.get("risk_tier") != rule.get("target_tier"):
        return False
    condition = rule.get("condition")
    if not isinstance(condition, dict):
        return False
    for key, expected in condition.items():
        if account.get(key) != expected:
            return False
    return True


def build_posture_report(
    *,
    registry: dict[str, Any],
    policy: dict[str, Any],
) -> dict[str, Any]:
    accounts = registry.get("accounts")
    if not isinstance(accounts, list) or not accounts:
        raise ValueError("registry.accounts must be a non-empty list")

    rules = policy.get("rules")
    if not isinstance(rules, list):
        raise ValueError("policy.rules must be a list")

    scoring = policy.get("scoring") if isinstance(policy.get("scoring"), dict) else {}
    base_score = int(scoring.get("base_score") or 100)
    critical_cap = int(scoring.get("critical_cap_score") or 35)
    tier_weights = scoring.get("tier_weights") if isinstance(scoring.get("tier_weights"), dict) else {}
    default_weight = 0.5

    drifts: list[dict[str, Any]] = []
    penalty_total = 0.0
    critical_breach = False

    for account in accounts:
        if not isinstance(account, dict):
            continue
        tier = str(account.get("risk_tier") or "")
        weight = float(tier_weights.get(tier, default_weight))
        for rule in rules:
            if not isinstance(rule, dict):
                continue
            if not _rule_matches(account, rule):
                continue
            penalty = int(rule.get("penalty_score") or 0) * weight
            penalty_total += penalty
            action = str(rule.get("action") or "")
            if action == "trigger_critical_drift" and tier == "tier_1_critical":
                critical_breach = True
            drifts.append(
                {
                    "account_id": account.get("account_id"),
                    "service_name": account.get("service_name"),
                    "risk_tier": tier,
                    "violated_rule": rule.get("rule_id"),
                    "action": action,
                    "weighted_penalty": round(penalty, 2),
                    "remediation": rule.get("remediation_runbook"),
                }
            )

    raw_score = max(0, base_score - int(round(penalty_total)))
    if critical_breach:
        posture_score = min(critical_cap, raw_score)
    else:
        posture_score = raw_score

    return {
        "schema": "sovereign_iam_lite_posture_v1",
        "generated_at_utc": _utc_now(),
        "lane": "ops",
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "data_plane_excluded": True,
        "send_gate": "HOLD",
        "ready_for_external_send": False,
        "readiness_all_ok": False,
        "disclaimer": policy.get("disclaimer"),
        "disclaimer_ko": policy.get("disclaimer_ko"),
        "scoring_mode": scoring.get("mode") or "critical_cap_v1",
        "critical_breach_detected": critical_breach,
        "posture_score": posture_score,
        "penalty_total_weighted": round(penalty_total, 2),
        "total_accounts_scanned": len(accounts),
        "drift_count": len(drifts),
        "critical_drifts_detected": sum(
            1 for d in drifts if d.get("action") == "trigger_critical_drift"
        ),
        "drifts": drifts,
        "registry_ref": "docs/final/artifacts/sovereign_iam_lite_accounts_registry_v1_example.json",
        "policy_ref": "docs/final/artifacts/sovereign_iam_lite_policy_v1_draft.json",
        "reproduce": "py scripts/build_sovereign_iam_lite_posture_v1.py",
    }


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    ap.add_argument("--policy", type=Path, default=DEFAULT_POLICY)
    ap.add_argument("--report-out", type=Path, default=DEFAULT_REPORT)
    ap.add_argument("--artifact-out", type=Path, default=DEFAULT_ARTIFACT)
    args = ap.parse_args()

    for label, path in (("registry", args.registry), ("policy", args.policy)):
        if not path.is_file():
            print(f"error: missing {label}: {path}", file=sys.stderr)
            return 1

    try:
        report = build_posture_report(
            registry=_load_json(args.registry.resolve()),
            policy=_load_json(args.policy.resolve()),
        )
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    _write_json(args.report_out.resolve(), report)
    _write_json(args.artifact_out.resolve(), report)
    print(
        f"WROTE: {args.report_out.resolve()} "
        f"score={report['posture_score']} "
        f"critical_breach={report['critical_breach_detected']} "
        f"drifts={report['drift_count']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
