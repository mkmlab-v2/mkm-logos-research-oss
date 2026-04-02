#!/usr/bin/env python3
"""Join billing + hallucination evidence with optional compression / canary / turboquant reports."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCHEMA = "cost_watch_monitor_v1"


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def _compression_block(doc: dict[str, Any] | None) -> dict[str, Any]:
    if not doc:
        return {"status": "missing", "reason": "report_not_found"}
    cm = doc.get("compression_metrics") or {}
    if cm:
        return {
            "status": "ok",
            "global_token_saving_rate": cm.get("global_token_saving_rate"),
            "case_count": cm.get("case_count"),
            "avg_reconstruction_fidelity_jaccard": cm.get("avg_reconstruction_fidelity_jaccard"),
            "avg_sensitive_integrity": cm.get("avg_sensitive_integrity"),
        }
    return {"status": "partial", "reason": "no_compression_metrics"}


def _canary_block(doc: dict[str, Any] | None) -> dict[str, Any]:
    if not doc:
        return {"status": "missing", "reason": "report_not_found"}
    if doc.get("skipped"):
        return {"status": "skipped", "reason": str(doc.get("skip_reason") or "")}
    summ = doc.get("summary") or {}
    p95 = summ.get("p95_latency_delta_pct")
    qd = summ.get("quality_delta")
    p95_mean = p95.get("mean") if isinstance(p95, dict) else None
    q_mean = qd.get("mean") if isinstance(qd, dict) else None
    return {
        "status": "ok",
        "stable": bool(doc.get("stable")),
        "go_rate": summ.get("go_rate"),
        "valid_runs": summ.get("valid_runs"),
        "total_runs": summ.get("total_runs"),
        "p95_latency_delta_pct_mean": p95_mean,
        "quality_delta_mean": q_mean,
    }


def _turboquant_block(doc: dict[str, Any] | None) -> dict[str, Any]:
    if not doc:
        return {"status": "missing", "reason": "report_not_found"}
    return {
        "status": "ok",
        "query_speedup_x": doc.get("query_speedup_x"),
        "build_speedup_x": doc.get("build_speedup_x"),
        "evidence_tier": doc.get("evidence_tier"),
        "synthetic_command_detected": doc.get("synthetic_command_detected"),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", required=True)
    ap.add_argument("--billing-input", required=True)
    ap.add_argument("--hallucination-input", required=True)
    args = ap.parse_args()

    root = Path(".").resolve()
    out = Path(args.output).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)

    billing_path = Path(args.billing_input).resolve()
    hall_path = Path(args.hallucination_input).resolve()
    billing = _read_json(billing_path) or {}
    hall = _read_json(hall_path) or {}

    compression_path = root / "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json"
    canary_path = root / "reports/constitution/btrack_pilot/vllm_ab_canary_repeat_latest.json"
    turbo_path = root / "reports/constitution/btrack_pilot/rag_turboquant_poc_latest.json"

    comp_doc = _read_json(compression_path)
    canary_doc = _read_json(canary_path)
    turbo_doc = _read_json(turbo_path)

    ts = datetime.now(timezone.utc).isoformat()
    pricing_ok = bool(billing.get("pricing_configured"))
    hall_ok = hall.get("zero_claim_eligible") is True and (hall.get("quality_fail_count") in (0, None))

    blocking: list[str] = []
    if not pricing_ok:
        blocking.append("billing_pricing_not_configured")

    payload = {
        "schema": SCHEMA,
        "ts_utc": ts,
        "sources": {
            "compression_report": str(compression_path),
            "vllm_canary_report": str(canary_path),
            "turboquant_report": str(turbo_path),
            "hallucination_input": str(hall_path),
            "billing_input": str(billing_path),
        },
        "compression": _compression_block(comp_doc),
        "vllm_canary": _canary_block(canary_doc),
        "turboquant_poc": _turboquant_block(turbo_doc),
        "hallucination_eval": {
            "status": "ok" if hall else "missing",
            "sample_count": hall.get("sample_count"),
            "quality_pass_rate": hall.get("quality_pass_rate"),
            "hallucination_proxy_rate": hall.get("hallucination_proxy_rate"),
            "zero_claim_eligible": hall.get("zero_claim_eligible"),
            "min_sample_for_zero_claim": hall.get("min_sample_for_zero_claim"),
        },
        "billing": {
            "status": "ok" if billing else "missing",
            "period_label": billing.get("period_label"),
            "api_cost_usd": billing.get("api_cost_usd"),
            "input_tokens": billing.get("input_tokens"),
            "output_tokens": billing.get("output_tokens"),
            "pricing_configured": billing.get("pricing_configured"),
            "source_tier": billing.get("source_tier"),
            "invoice_provenance": billing.get("invoice_provenance"),
            "invoice_audit_ready": billing.get("invoice_audit_ready"),
        },
        "claim_guardrails": {
            "can_claim_hallucination_zero": bool(hall_ok),
            "can_claim_margin_uplift_50": False,
            "blocking_reasons": blocking,
        },
        "note": "This monitor is evidence-join only. It does not certify margin uplift without real billing data.",
    }
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"WROTE: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
