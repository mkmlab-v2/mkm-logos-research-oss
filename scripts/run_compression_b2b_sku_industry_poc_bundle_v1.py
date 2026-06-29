#!/usr/bin/env python3
"""Run stateless PoC per B2B off-the-shelf SKU on industry demo JSONL. [HYPO]"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
SPEC = ROOT / "docs/final/artifacts/compression_b2b_off_the_shelf_shard_sku_v1.json"
POC_SCRIPT = ROOT / "scripts/run_customer_compression_stateless_poc_v1.py"
BUILD_SCRIPT = ROOT / "scripts/build_compression_b2b_industry_poc_corpus_v1.py"
DEFAULT_SUMMARY = ROOT / "reports/compression_b2b_sku_industry_poc_bundle_v1_latest.json"

SKU_CORPUS: dict[str, tuple[str, str]] = {
    "MKM-SCM-A1": (
        "data/compression/stateless_poc_scm_public_safe_v1.jsonl",
        "reports/customer_compression_stateless_poc_scm_a1_industry_literal_v1_latest.json",
    ),
    "MKM-CHAT-D1": (
        "data/compression/stateless_poc_chat_public_safe_v1.jsonl",
        "reports/customer_compression_stateless_poc_chat_d1_industry_literal_v1_latest.json",
    ),
    "MKM-FIN-E1": (
        "data/compression/stateless_poc_finance_public_safe_v1.jsonl",
        "reports/customer_compression_stateless_poc_fin_e1_industry_literal_v1_latest.json",
    ),
    "MKM-MED-G1": (
        "data/compression/stateless_poc_health_public_safe_v1.jsonl",
        "reports/customer_compression_stateless_poc_med_g1_industry_literal_v1_latest.json",
    ),
}


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_aggregate(report_path: Path) -> dict[str, Any]:
    if not report_path.is_file():
        return {}
    doc = json.loads(report_path.read_text(encoding="utf-8"))
    agg = doc.get("aggregate") if isinstance(doc.get("aggregate"), dict) else {}
    sku_ctx = doc.get("sku_context") if isinstance(doc.get("sku_context"), dict) else {}
    return {
        "case_count": doc.get("case_count"),
        "cases_passed": doc.get("cases_passed"),
        "cases_passed_jaccard_floor": doc.get("cases_passed_jaccard_floor"),
        "mean_token_saving_rate_proxy": agg.get("mean_token_saving_rate_proxy"),
        "mean_jaccard_proxy": agg.get("mean_jaccard_proxy"),
        "mean_jaccard_all_cases": agg.get("mean_jaccard_proxy_all_cases"),
        "compression_profile": doc.get("compression_profile"),
        "must_keep_overlay_applied": (doc.get("must_keep_overlay") or {}).get("applied"),
        "forced_shard_id": sku_ctx.get("forced_shard_id"),
        "routing_wiring": sku_ctx.get("routing_wiring"),
        "sample_router_shard_id": (doc.get("cases") or [{}])[0].get("router_shard_id")
        if isinstance(doc.get("cases"), list) and doc.get("cases")
        else None,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="B2B SKU industry PoC bundle.")
    ap.add_argument("--skip-build", action="store_true")
    ap.add_argument("--rows-per-sku", type=int, default=30)
    ap.add_argument(
        "--compression-profile",
        default="literal",
        choices=["economy", "fidelity", "literal"],
        help="Default literal for B2B industry short-text PoC [HYPO].",
    )
    ap.add_argument("--auto-b2b-overlay", action="store_true", default=True)
    ap.add_argument("--no-auto-b2b-overlay", action="store_false", dest="auto_b2b_overlay")
    ap.add_argument("--sku", action="append", default=[], help="Limit to one or more external SKUs.")
    ap.add_argument("--relax-pass-gate", action="store_true", default=True)
    ap.add_argument("--no-relax-pass-gate", action="store_false", dest="relax_pass_gate")
    ap.add_argument("--out-summary", type=Path, default=DEFAULT_SUMMARY)
    args = ap.parse_args()

    if not args.skip_build:
        rc = subprocess.call(
            [
                sys.executable,
                str(BUILD_SCRIPT),
                "--rows-per-sku",
                str(max(1, args.rows_per_sku)),
            ],
            cwd=str(ROOT),
        )
        if rc != 0:
            return rc

    selected = list(SKU_CORPUS.keys())
    if args.sku:
        selected = [s for s in args.sku if s in SKU_CORPUS]
        unknown = [s for s in args.sku if s not in SKU_CORPUS]
        if unknown:
            print(f"error: unknown sku(s): {unknown}", file=sys.stderr)
            return 2
        if not selected:
            print("error: no valid sku selected", file=sys.stderr)
            return 2

    steps: list[dict[str, Any]] = []
    for external_sku in selected:
        corpus_rel, report_rel = SKU_CORPUS[external_sku]
        corpus = (ROOT / corpus_rel).resolve()
        report = (ROOT / report_rel).resolve()
        if not corpus.is_file():
            print(f"error: missing corpus: {corpus}", file=sys.stderr)
            return 2
        cmd = [
            sys.executable,
            str(POC_SCRIPT),
            "--input-jsonl",
            str(corpus),
            "--sku",
            external_sku,
            "--sku-spec-json",
            str(SPEC),
            "--compression-profile",
            args.compression_profile,
            "--max-cases",
            str(max(1, args.rows_per_sku)),
            "--out-json",
            str(report),
        ]
        if args.auto_b2b_overlay:
            cmd.append("--auto-b2b-overlay")
        if args.relax_pass_gate:
            cmd.append("--relax-pass-gate")
        print("RUN", " ".join(cmd))
        proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
        step = {
            "external_sku": external_sku,
            "corpus_path": str(corpus).replace("\\", "/"),
            "report_path": str(report).replace("\\", "/"),
            "exit_code": proc.returncode,
            "stdout_tail": proc.stdout.strip().splitlines()[-3:],
            "stderr_tail": proc.stderr.strip().splitlines()[-3:] if proc.stderr else [],
        }
        if proc.returncode == 0:
            step.update(_read_aggregate(report))
        steps.append(step)
        if proc.returncode != 0:
            print(proc.stdout)
            print(proc.stderr, file=sys.stderr)
            break

    summary = {
        "schema": "compression_b2b_sku_industry_poc_bundle_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "send_gate": "HOLD",
        "compression_profile_default": args.compression_profile,
        "rows_per_sku": args.rows_per_sku,
        "must_keep_overlay": bool(args.auto_b2b_overlay),
        "spec_path": str(SPEC).replace("\\", "/"),
        "bundle_ok": all(s.get("exit_code") == 0 for s in steps) and bool(steps),
        "steps": steps,
    }
    out_path = args.out_summary.resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {out_path}")
    return 0 if summary["bundle_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
