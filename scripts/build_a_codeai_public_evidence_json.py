#!/usr/bin/env python3
"""
Build public evidence JSON for a-codeai.com benchmark pages.

Source artifacts (SSOT):
- docs/final/artifacts/l1_inverse_decoder_commercialization_checklist_v1.json
- docs/final/artifacts/l1_inverse_decoder_swap_typo_objective_v4_ab_v1.json
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _pick_gain_value(checklist: dict[str, Any], ab: dict[str, Any]) -> float | None:
    criteria = checklist.get("criteria", [])
    for item in criteria:
        if item.get("id") == "C1_swap_typo_uplift":
            actual = item.get("actual", {})
            exact = actual.get("exact_delta")
            if isinstance(exact, (int, float)):
                return float(exact)
    delta = ab.get("delta_vs_baseline", {})
    fallback = delta.get("swap_typo_exact_delta")
    if isinstance(fallback, (int, float)):
        return float(fallback)
    return None


def _round4(value: float | None) -> float | None:
    if value is None:
        return None
    return round(float(value), 4)


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def validate_inputs(checklist: dict[str, Any], ab: dict[str, Any]) -> None:
    decision = checklist.get("decision", {})
    _require(isinstance(decision, dict), "Missing decision object in checklist.")
    _require(isinstance(decision.get("status"), str), "Missing decision.status in checklist.")

    criteria = checklist.get("criteria")
    _require(isinstance(criteria, list) and len(criteria) > 0, "Missing checklist criteria list.")

    delta = ab.get("delta_vs_baseline", {})
    _require(isinstance(delta, dict), "Missing delta_vs_baseline object in A/B artifact.")
    _require(
        isinstance(delta.get("swap_typo_exact_delta"), (int, float)),
        "Missing delta_vs_baseline.swap_typo_exact_delta in A/B artifact.",
    )


def build_payload(checklist: dict[str, Any], ab: dict[str, Any]) -> dict[str, Any]:
    decision = checklist.get("decision", {})
    status = decision.get("status", "UNKNOWN")
    criteria = checklist.get("criteria", [])
    passed = sum(1 for c in criteria if c.get("pass") is True)
    total = len(criteria)
    gain = _round4(_pick_gain_value(checklist, ab))
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

    return {
        "schema": "a_codeai_public_evidence_v1",
        "generated_at_utc": now,
        "commercial_readiness": {
            "status": status,
            "criteria_passed": passed,
            "criteria_total": total,
            "source": "l1_inverse_decoder_commercialization_checklist_v1.json",
        },
        "hard_case_gain": {
            "metric": "swap_typo_objective_v4_exact_recovery_delta",
            "value": gain,
            "source": "l1_inverse_decoder_swap_typo_objective_v4_ab_v1.json",
        },
        "ops_safety": {
            "rollback_switch": "--disable-swap-typo-objective-v4",
            "track_split": "Track A / Track B separated",
        },
        "verification_pack": {
            "public_scope": [
                "KPI readiness status",
                "Hard-case gain delta",
                "Route/API health checks",
                "Rollback and lane-split policy",
            ],
            "non_public_scope": [
                "Core compression/reconstruction internals",
                "Candidate generation internals",
                "Proprietary policy tuning logic",
            ],
            "repro_commands": [
                "bash scripts/deploy/linux/check_a_codeai_public_routes.sh",
                "python3 scripts/build_a_codeai_public_evidence_json.py --repo-root .",
            ],
            "artifacts": [
                "docs/final/artifacts/l1_inverse_decoder_commercialization_checklist_v1.json",
                "docs/final/artifacts/l1_inverse_decoder_swap_typo_objective_v4_ab_v1.json",
                "scripts/deploy/nginx/a-codeai.com.evidence.latest.json.example",
            ],
        },
        "notes": [
            "Meaning-centric workloads first",
            "Literal-preserve lane recommended for strict fidelity workloads",
        ],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build A-CODEAI public evidence JSON.")
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Repository root path",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("scripts/deploy/nginx/a-codeai.com.evidence.latest.json.example"),
        help="Output path relative to repo root (or absolute path)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = args.repo_root.resolve()
    out_path = args.out if args.out.is_absolute() else (repo_root / args.out)

    checklist_path = repo_root / "docs/final/artifacts/l1_inverse_decoder_commercialization_checklist_v1.json"
    ab_path = repo_root / "docs/final/artifacts/l1_inverse_decoder_swap_typo_objective_v4_ab_v1.json"

    checklist = _load_json(checklist_path)
    ab = _load_json(ab_path)
    validate_inputs(checklist, ab)
    payload = build_payload(checklist, ab)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8", newline="\n") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print(f"[OK] wrote evidence json: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
