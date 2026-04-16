#!/usr/bin/env python3
"""Build Track C evidence pack from governed artifacts."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        obj = json.load(f)
    if not isinstance(obj, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return obj


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def build_payload(
    governance: dict[str, Any],
    biblical_gate: dict[str, Any],
    myeongri_gate: dict[str, Any],
    sasang_gate: dict[str, Any],
) -> dict[str, Any]:
    biblical_stability = biblical_gate.get("stability") if isinstance(biblical_gate.get("stability"), dict) else {}

    return {
        "schema": "track_c_evidence_pack_v1",
        "generated_at_utc": _utc_now(),
        "governance": {
            "final_regime": governance.get("final_regime"),
            "final_action_allowed": governance.get("final_action_allowed"),
            "is_fallback": governance.get("is_fallback"),
            "final_score": governance.get("final_score"),
            "veto_reason_codes": governance.get("veto_reason_codes", []),
        },
        "engine_readiness": {
            "biblical_core": {
                "precommercial_ready": biblical_gate.get("precommercial_ready"),
                "stage": biblical_gate.get("stage"),
                "stability_go": biblical_stability.get("stability_go"),
                "current_ready_streak": biblical_stability.get("current_ready_streak"),
                "streak_required": biblical_stability.get("streak_required"),
            },
            "myeongri_v4_1": {
                "standalone_commercial_ready": myeongri_gate.get("standalone_commercial_ready"),
                "stage": myeongri_gate.get("stage"),
                "accuracy": (myeongri_gate.get("metrics") or {}).get("accuracy"),
                "abs_train_test_acc_gap": (myeongri_gate.get("metrics") or {}).get("abs_train_test_acc_gap"),
            },
            "sasang_strict": {
                "commercial_ready": sasang_gate.get("commercial_ready"),
                "stage": sasang_gate.get("stage"),
                "runtime_go_ratio": ((sasang_gate.get("gates") or {}).get("G3_runtime_go_ratio") or {}).get("observed_ratio"),
            },
        },
        "commercial_scope": {
            "track_c_mode": "risk_warning_and_ip_licensing",
            "advisory_restriction": "No direct buy/sell recommendation. Risk posture and warning products only.",
            "required_disclaimer": "Not investment advice; final decisions remain with client operators.",
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build Track C evidence pack.")
    repo_root_default = Path(__file__).resolve().parents[1]
    parser.add_argument("--repo-root", type=Path, default=repo_root_default)
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("docs/final/artifacts/track_c_evidence_pack_latest.json"),
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = args.repo_root.resolve()
    out_path = args.out if args.out.is_absolute() else (repo_root / args.out)

    governance = _load_json(repo_root / "docs/final/artifacts/integrated_governance_v1_latest.json")
    biblical = _load_json(repo_root / "docs/final/artifacts/kospi_biblical_single_lane_commercial_gate_v1_latest.json")
    myeongri = _load_json(repo_root / "docs/final/artifacts/kospi_myeongri_standalone_commercial_gate_v1_latest.json")
    sasang = _load_json(repo_root / "docs/final/artifacts/kospi_sasang_single_lane_commercial_gate_v1_latest.json")
    payload = build_payload(governance, biblical, myeongri, sasang)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(out_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

