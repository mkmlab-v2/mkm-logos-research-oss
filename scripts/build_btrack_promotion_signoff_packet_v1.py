# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.82, L:0.86, K:0.55, M:0.68}
# Balance: 88
# Purpose: Aggregate B-track promotion gate artifacts into a single human sign-off packet.
# Keywords: promotion, gates, signoff, btrack, lg, prophecy
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path("C:/workspace")
ART = ROOT / "docs" / "final" / "artifacts"

DEFAULT_PROPHECY_GATE = ART / "prophecy_promotion_gates_v1_latest.json"
DEFAULT_CODEBOOK_DRIFT = ART / "codebook_codepack_drift_latest.json"
DEFAULT_MEASUREMENT_GATE = ART / "lg_washer_measurement_gate_latest.json"
DEFAULT_ESTIMATION_READY = ART / "lg_washer_estimation_readiness_latest.json"
DEFAULT_OUT = ART / "btrack_promotion_signoff_packet_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _rel(path: Path) -> str:
    return str(path.relative_to(ROOT)).replace("\\", "/") if path.is_relative_to(ROOT) else str(path)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--prophecy-gate", type=Path, default=DEFAULT_PROPHECY_GATE)
    ap.add_argument("--codebook-drift", type=Path, default=DEFAULT_CODEBOOK_DRIFT)
    ap.add_argument("--measurement-gate", type=Path, default=DEFAULT_MEASUREMENT_GATE)
    ap.add_argument("--estimation-readiness", type=Path, default=DEFAULT_ESTIMATION_READY)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    prophecy = _load(args.prophecy_gate)
    drift = _load(args.codebook_drift)
    measurement = _load(args.measurement_gate)
    estimation = _load(args.estimation_readiness)

    prophecy_ready = bool(prophecy.get("auto_promote_ready") is True)
    drift_stable = str(drift.get("drift_status", "")).upper() == "STABLE"
    measurement_go = str(measurement.get("status", "")).upper() == "GO"
    estimation_ready = str(estimation.get("status", "")).upper() == "ESTIMATION_READY"

    prophecy_decision = "READY_FOR_HUMAN_SIGNOFF" if prophecy_ready else "HOLD"
    lg_decision = "READY_FOR_HUMAN_SIGNOFF" if (drift_stable and measurement_go) else "HOLD"

    blockers: list[str] = []
    if not prophecy_ready:
        blockers.append("prophecy_auto_promote_ready_false")
    if not drift_stable:
        blockers.append("codebook_codepack_drift_detected")
    if not measurement_go:
        blockers.append("lg_measurement_gate_not_go")

    out = {
        "schema": "btrack_promotion_signoff_packet_v1",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "inputs": {
            "prophecy_gate": _rel(args.prophecy_gate),
            "codebook_drift": _rel(args.codebook_drift),
            "measurement_gate": _rel(args.measurement_gate),
            "estimation_readiness": _rel(args.estimation_readiness),
        },
        "track_status": {
            "prophecy": {
                "decision": prophecy_decision,
                "auto_promote_ready": prophecy.get("auto_promote_ready"),
                "strict_pass_streak": prophecy.get("strict_pass_streak"),
                "promotion_recommendation": prophecy.get("promotion_recommendation"),
            },
            "lg_washer": {
                "decision": lg_decision,
                "codebook_codepack_drift_status": drift.get("drift_status"),
                "measurement_gate_status": measurement.get("status"),
                "estimation_readiness_status": estimation.get("status"),
            },
        },
        "global": {
            "all_tracks_ready_for_human_signoff": (prophecy_decision == "READY_FOR_HUMAN_SIGNOFF" and lg_decision == "READY_FOR_HUMAN_SIGNOFF"),
            "blockers": blockers,
        },
        "notes_ko": [
            "prophecy는 auto_promote_ready=true여도 human sign-off 전 본선/실매매 자동 승격 금지",
            "lg_washer: measurement_gate는 GO 가능하나, measurement_kind가 local proxy면 제출 최종본으로 단정 금지",
            "estimation_readiness는 실측 존재 시 MEASUREMENT_PRIMARY로 표시되며 measurement_gate가 우선이다",
        ],
        "next_actions_ko": [
            "prophecy: 소액 live A/B 결과 포함 human sign-off 패킷 확정",
            "lg_washer: 타깃 보드 실측 JSON으로 교체 후 measurement_gate 재실행(현재는 로컬 벤치 프록시 가능 시 GO)",
        ],
    }

    args.out.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(args.out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
