# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.84, L:0.83, K:0.5, M:0.66}
# Balance: 88
# Purpose: Gate LG report promotion using target-device measurement evidence.
# Keywords: LG, washer, measurement, gate, submit-ready
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
DEFAULT_REPORT = ART / "lg_washer_integrity_validation_report_v1_latest.json"
DEFAULT_MEASURED = ART / "lg_washer_target_device_measurement_v1.json"
DEFAULT_OUT = ART / "lg_washer_measurement_gate_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _f(v: Any) -> float | None:
    if isinstance(v, (int, float)):
        return float(v)
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    ap.add_argument("--measured", type=Path, default=DEFAULT_MEASURED)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--strict", action="store_true", help="Exit non-zero when gate is not GO")
    args = ap.parse_args()

    report = _load_json(args.report)
    measured_exists = args.measured.exists()
    measured = _load_json(args.measured) if measured_exists else {}

    report_metrics = (((report.get("evaluation_protocol") or {}).get("metrics")) or {})
    measured_metrics = (measured.get("metrics") or {}) if isinstance(measured, dict) else {}

    reasons: list[str] = []
    status = "HOLD"

    m_status = str(measured.get("status", "")).strip().lower() if isinstance(measured, dict) else ""
    if not measured_exists:
        reasons.append("measurement_file_missing")
    elif m_status not in {"measured", "validated"}:
        reasons.append("measurement_status_not_measured")

    latency = measured_metrics.get("latency_ms") if isinstance(measured_metrics, dict) else None
    critical = _f(measured_metrics.get("critical_field_accuracy"))
    conflict = _f(measured_metrics.get("conflict_detection_rate"))

    if not isinstance(latency, dict):
        reasons.append("latency_ms_missing")
    else:
        if _f(latency.get("p95")) is None:
            reasons.append("latency_p95_missing")
        if _f(latency.get("p99")) is None:
            reasons.append("latency_p99_missing")

    if critical is None:
        reasons.append("critical_field_accuracy_missing")
    if conflict is None:
        reasons.append("conflict_detection_rate_missing")

    if not reasons:
        status = "GO"

    out_doc = {
        "schema": "lg_washer_measurement_gate_v1",
        "generated_at_utc": _utc_now(),
        "report_ref": str(args.report.relative_to(ROOT)).replace("\\", "/") if args.report.is_relative_to(ROOT) else str(args.report),
        "measurement_ref": str(args.measured.relative_to(ROOT)).replace("\\", "/") if args.measured.is_relative_to(ROOT) else str(args.measured),
        "status": status,
        "reasons": reasons,
        "report_metrics_snapshot": report_metrics,
        "measured_metrics_snapshot": measured_metrics,
        "promotion_rule_ko": "측정 파일 status=measured/validated + latency(p95,p99) + critical/conflict 지표 존재 시 GO",
        "next_action_ko": "HOLD면 타깃 보드 실측 JSON 채운 뒤 재실행",
    }

    args.out.write_text(json.dumps(out_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(args.out))
    print(status)

    if args.strict and status != "GO":
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
