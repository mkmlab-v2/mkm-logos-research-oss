# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.8, L:0.85, K:0.52, M:0.66}
# Balance: 86
# Purpose: Summarize whether estimation JSON is internally consistent; defer to measurement when present.
# Keywords: LG, washer, estimation, readiness, gate
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path("C:/workspace")
ART = ROOT / "docs" / "final" / "artifacts"
DEFAULT_EST = ART / "lg_washer_target_device_estimation_v1.json"
DEFAULT_MEAS = ART / "lg_washer_target_device_measurement_v1.json"
DEFAULT_OUT = ART / "lg_washer_estimation_readiness_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _is_num(v: Any) -> bool:
    return isinstance(v, (int, float))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--estimation", type=Path, default=DEFAULT_EST)
    ap.add_argument("--measurement", type=Path, default=DEFAULT_MEAS)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    est = _load(args.estimation)
    meas_exists = args.measurement.exists()
    meas = _load(args.measurement) if meas_exists else {}

    est_metrics = (est.get("estimated_metrics") or {}) if isinstance(est, dict) else {}
    lat = (est_metrics.get("latency_ms") or {}) if isinstance(est_metrics, dict) else {}

    reasons: list[str] = []
    if str(est.get("status", "")).strip() != "ESTIMATED_BASELINE":
        reasons.append("estimation_status_not_ESTIMATED_BASELINE")
    if not _is_num(lat.get("p95")):
        reasons.append("estimated_latency_p95_missing")
    if not _is_num(lat.get("p99")):
        reasons.append("estimated_latency_p99_missing")

    if meas_exists:
        m_status = str(meas.get("status", "")).strip().lower()
        if m_status in {"measured", "validated"}:
            # When real (or proxy) measurement exists, estimation readiness is informational only.
            # Do not mark TODO here; operators should follow measurement_gate instead.
            out_status = "MEASUREMENT_PRIMARY_SKIP_ESTIMATION"
            out = {
                "schema": "lg_washer_estimation_readiness_v1",
                "generated_at_utc": _utc_now(),
                "status": out_status,
                "reasons": [],
                "estimation_ref": str(args.estimation.relative_to(ROOT)).replace("\\", "/") if args.estimation.is_relative_to(ROOT) else str(args.estimation),
                "measurement_ref": str(args.measurement.relative_to(ROOT)).replace("\\", "/") if args.measurement.is_relative_to(ROOT) else str(args.measurement),
                "rule_ko": "실측이 존재하면 estimation_readiness는 참고용이며 measurement_gate가 우선이다",
            }
            args.out.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print(str(args.out))
            print(out_status)
            return 0

    status = "ESTIMATION_READY" if not reasons else "ESTIMATION_TODO"

    out = {
        "schema": "lg_washer_estimation_readiness_v1",
        "generated_at_utc": _utc_now(),
        "status": status,
        "reasons": reasons,
        "estimation_ref": str(args.estimation.relative_to(ROOT)).replace("\\", "/") if args.estimation.is_relative_to(ROOT) else str(args.estimation),
        "measurement_ref": str(args.measurement.relative_to(ROOT)).replace("\\", "/") if args.measurement.is_relative_to(ROOT) else str(args.measurement),
        "rule_ko": "ESTIMATION_READY는 참고 가능 상태일 뿐 measurement_gate 승격 근거가 아니다"
    }

    args.out.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(args.out))
    print(status)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
