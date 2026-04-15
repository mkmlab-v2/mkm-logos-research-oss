from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ART = Path("docs/final/artifacts")
SNAPSHOT_DEFAULT = ART / "prophecy_two_track_snapshot_v1_latest.json"
OUT_DEFAULT = ART / "prophecy_2050_two_track_v1_latest.json"


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def build(snapshot: dict[str, Any]) -> dict[str, Any]:
    track_a_summary = ((snapshot.get("track_a_trading_theory") or {}).get("summary") or {})
    track_b_summary = ((snapshot.get("track_b_historical_omen") or {}).get("registry_summary") or {})

    return {
        "schema": "prophecy_2050_two_track_v1",
        "version": "1.0.0",
        "generated_at_utc": _now(),
        "scope": {
            "start_year": 2026,
            "end_year": 2050,
            "method": "biblical_resource_guided_scenario",
            "disclaimer": (
                "Non-deterministic scenario document. Track A is measurable/operational; "
                "Track B is historical-omen interpretation and must not trigger live orders."
            ),
        },
        "fusion_policy": {
            "auto_merge_to_live_trading": False,
            "track_b_must_not_trigger_orders": True,
            "track_b_for_live_execution": False,
        },
        "track_a_trading_theory": {
            "current_state": track_a_summary,
            "operational_bands": [
                {
                    "period": "2026-2030",
                    "thesis": "High-volatility expansion with frequent regime flips.",
                    "monitoring_focus": [
                        "external_reality_gate mode drift (recent vs equivalent_n)",
                        "dominant_share concentration risk",
                        "stability streak continuity",
                    ],
                    "action_default": "guarded / no auto escalation",
                },
                {
                    "period": "2031-2040",
                    "thesis": "Structural repricing cycles and trust-friction markets.",
                    "monitoring_focus": [
                        "persistent class-bias drift",
                        "cross-cycle equivalent-n reliability decay",
                        "execution safety gate strictness",
                    ],
                    "action_default": "risk-first with conservative sizing",
                },
                {
                    "period": "2041-2050",
                    "thesis": "Long-horizon uncertainty convergence; prioritize survivability.",
                    "monitoring_focus": [
                        "compound drawdown control",
                        "signal-to-noise degradation watch",
                        "gate contract integrity over alpha chasing",
                    ],
                    "action_default": "capital preservation priority",
                },
            ],
            "hard_constraints": [
                "No myeongri/sasang fusion in this lane.",
                "No commercialization declaration under sample shortage.",
                "No live-trading enable unless stability_go=true and blockers are empty.",
            ],
        },
        "track_b_historical_omen": {
            "current_state": track_b_summary,
            "era_signs": [
                {
                    "period": "2026-2030",
                    "sign_cluster": "Acceleration and meaning-friction",
                    "interpretation": (
                        "Technology speed increases while social trust lags; "
                        "discernment pressure grows in institutions and communities."
                    ),
                    "response": "Build local trust networks and integrity-first decision culture.",
                },
                {
                    "period": "2031-2040",
                    "sign_cluster": "System reconfiguration and narrative conflict",
                    "interpretation": (
                        "Governance, money, and information systems rewire repeatedly; "
                        "truth-vs-manipulation conflict intensifies."
                    ),
                    "response": "Maintain epistemic discipline and scenario-based preparedness.",
                },
                {
                    "period": "2041-2050",
                    "sign_cluster": "Convergence and ethical bifurcation",
                    "interpretation": (
                        "Efficiency and control capabilities rise, but value fractures deepen; "
                        "human dignity and stewardship become central tests."
                    ),
                    "response": "Prioritize dignity, mercy, and long-term covenantal accountability.",
                },
            ],
            "evaluation_rail": "B / OBSERVATION_ONLY",
            "forbidden_for_live_execution": True,
        },
        "handoff": {
            "next_artifact": "docs/final/artifacts/prophecy_two_track_snapshot_v1_latest.json",
            "notes": [
                "Use this as long-horizon narrative overlay, not a point forecast.",
                "Rebuild when track_a summary or general prophecy registry materially changes.",
            ],
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Build 2050 two-track prophecy document")
    ap.add_argument("--snapshot", type=Path, default=SNAPSHOT_DEFAULT)
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    args = ap.parse_args()

    snapshot = _load(args.snapshot)
    out = build(snapshot)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(args.out.resolve())}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
