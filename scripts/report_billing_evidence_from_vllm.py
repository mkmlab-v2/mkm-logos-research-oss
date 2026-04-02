#!/usr/bin/env python3
"""Build billing_evidence_latest.json from vLLM benchmark JSON + optional invoice."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCHEMA = "billing_evidence_v1"


def _candidate_token_totals(rows: list[dict[str, Any]]) -> tuple[int, int, int]:
    inp = out = 0
    for r in rows:
        if str(r.get("lane") or "") != "candidate":
            continue
        pt = r.get("prompt_tokens")
        ct = r.get("completion_tokens")
        if pt is not None:
            inp += int(pt)
        if ct is not None:
            out += int(ct)
    return inp, out, inp + out


def _pick_benchmark_path(root: Path) -> Path | None:
    candidates = [
        root / "reports/constitution/btrack_pilot/vllm_ab_benchmark_auto_latest.json",
        root / "reports/constitution/btrack_pilot/vllm_ab_benchmark_latest.json",
    ]
    for p in candidates:
        if p.is_file():
            return p
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", required=True)
    ap.add_argument("--period-label", default="waiting_queue_monthly_check")
    ap.add_argument("--input-usd-per-1k-tokens", type=float, default=0.0)
    ap.add_argument("--output-usd-per-1k-tokens", type=float, default=0.0)
    ap.add_argument("--invoice-input", default="")
    args = ap.parse_args()

    root = Path(".").resolve()
    out = Path(args.output).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)

    bench_path = _pick_benchmark_path(root)
    rows: list[dict[str, Any]] = []
    source_report = ""
    if bench_path:
        source_report = str(bench_path)
        try:
            doc = json.loads(bench_path.read_text(encoding="utf-8"))
            rows = list(doc.get("rows") or [])
        except json.JSONDecodeError:
            rows = []

    input_tokens, output_tokens, total_tokens = _candidate_token_totals(rows)
    if total_tokens == 0 and bench_path is None:
        # No benchmark file: keep zeros; downstream may still use invoice cost.
        source_report = str(root / "reports/constitution/btrack_pilot/vllm_ab_benchmark_auto_latest.json")

    pricing_configured = (args.input_usd_per_1k_tokens > 0.0) or (args.output_usd_per_1k_tokens > 0.0)
    blended_per_1k = (args.input_usd_per_1k_tokens + args.output_usd_per_1k_tokens) / 2.0
    api_cost_usd = (total_tokens / 1000.0) * blended_per_1k if pricing_configured and total_tokens else None

    invoice_path: Path | None = Path(args.invoice_input).resolve() if args.invoice_input else None
    invoice_audit_ready = True
    invoice_provenance = "none"
    if invoice_path and invoice_path.is_file():
        try:
            inv = json.loads(invoice_path.read_text(encoding="utf-8"))
            invoice_provenance = str(inv.get("invoice_provenance") or "provider_file")
            ac = inv.get("api_cost_usd")
            if ac is not None:
                api_cost_usd = float(ac)
            invoice_audit_ready = "replace_with" not in json.dumps(inv)
        except (json.JSONDecodeError, TypeError, ValueError):
            invoice_audit_ready = False

    if api_cost_usd is None:
        api_cost_usd = 0.0

    source_tier = "invoice_audit" if (invoice_path and invoice_path.is_file()) else "benchmark_estimate"

    ts = datetime.now(timezone.utc).isoformat()
    payload = {
        "schema": SCHEMA,
        "ts_utc": ts,
        "source_report": source_report,
        "invoice_input": str(invoice_path) if invoice_path else "",
        "invoice_provenance": invoice_provenance,
        "invoice_audit_ready": invoice_audit_ready,
        "source_tier": source_tier,
        "period_label": args.period_label,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": total_tokens,
        "input_usd_per_1k_tokens": args.input_usd_per_1k_tokens,
        "output_usd_per_1k_tokens": args.output_usd_per_1k_tokens,
        "pricing_configured": pricing_configured,
        "api_cost_usd": round(float(api_cost_usd), 8),
        "note": "invoice_audit_ready=false if invoice JSON still contains replace_with* placeholders.",
    }
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"WROTE: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
