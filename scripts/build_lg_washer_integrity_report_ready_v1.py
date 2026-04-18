from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path("C:/workspace")
ART = ROOT / "docs" / "final" / "artifacts"

INPUT_REPORT = ART / "lg_washer_integrity_validation_report_sample_v1.json"
EDGE_EVIDENCE = ART / "defense_edge_execution_evidence_v1.json"
OUTPUT_LATEST = ART / "lg_washer_integrity_validation_report_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _safe_float(value: Any) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _compute_sample_proxies(sample_records: list[dict[str, Any]]) -> dict[str, float | None]:
    if not sample_records:
        return {"conflict_detection_rate": None, "reask_rate": None}

    total = len(sample_records)
    reask_like = 0
    conflict_total = 0
    conflict_handled = 0

    for row in sample_records:
        action = (row.get("expected_action") or "").strip().lower()
        has_conflict = bool((row.get("conflict_hint") or "").strip())
        if action in {"reask", "reask_or_reject"}:
            reask_like += 1
        if has_conflict:
            conflict_total += 1
            if action == "reask_or_reject":
                conflict_handled += 1

    return {
        "conflict_detection_rate": (conflict_handled / conflict_total) if conflict_total else None,
        "reask_rate": reask_like / total,
    }


def main() -> int:
    report = _load_json(INPUT_REPORT)
    evidence = _load_json(EDGE_EVIDENCE)

    local_runtime = evidence.get("local_runtime_facts") or {}
    latency = local_runtime.get("latency_ms") or {}
    integrity = evidence.get("hybrid_integrity_facts") or {}
    sample_records = report.get("sample_records") or []
    proxies = _compute_sample_proxies(sample_records)

    metrics = (((report.get("evaluation_protocol") or {}).get("metrics")) or {})
    metrics["critical_field_accuracy"] = _safe_float(integrity.get("critical_field_integrity"))
    metrics["conflict_detection_rate"] = proxies["conflict_detection_rate"]
    metrics["reask_rate"] = proxies["reask_rate"]
    metrics["latency_ms"] = {
        "p50": _safe_float(latency.get("p50")),
        "p95": _safe_float(latency.get("p95")),
        "p99": _safe_float(latency.get("p99")),
    }
    report["evaluation_protocol"]["metrics"] = metrics

    report["status"] = "report_ready_local_baseline"
    report["generated_at_utc"] = _utc_now()
    report["evaluation_protocol"]["metric_basis"] = {
        "critical_field_accuracy": "defense_edge_execution_evidence_v1.hybrid_integrity_facts.critical_field_integrity",
        "latency_ms": "defense_edge_execution_evidence_v1.local_runtime_facts.latency_ms",
        "conflict_detection_rate": "sample_records expected_action/conflict_hint proxy (not blind holdout measured)",
        "reask_rate": "sample_records expected_action proxy (not blind holdout measured)",
    }
    report["evaluation_protocol"]["target_device_measurement_required"] = True
    report["evaluation_protocol"]["local_baseline_reference"] = str(
        EDGE_EVIDENCE.relative_to(ROOT)
    ).replace("\\", "/")

    note = report.get("program_context", {}).get("note") or ""
    report["program_context"]["note"] = (
        "로컬 기준선 수치 반영본(report_ready_local_baseline). "
        "타깃 디바이스 실측 전까지 제출 최종본으로 단정 금지. "
        f"기존 노트: {note}"
    ).strip()

    OUTPUT_LATEST.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(OUTPUT_LATEST))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
