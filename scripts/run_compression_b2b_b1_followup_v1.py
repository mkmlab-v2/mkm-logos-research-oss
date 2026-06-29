#!/usr/bin/env python3
"""B1 followup: must_keep overlay wired into stateless V2 API + failure panel. [HYPO]"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable

SKU_CORPUS: dict[str, tuple[str, str]] = {
    "MKM-SCM-A1": (
        "data/compression/stateless_poc_scm_public_safe_v1.jsonl",
        "reports/customer_compression_stateless_poc_scm_a1_overlay_v1_latest.json",
    ),
    "MKM-CHAT-D1": (
        "data/compression/stateless_poc_chat_public_safe_v1.jsonl",
        "reports/customer_compression_stateless_poc_chat_d1_overlay_v1_latest.json",
    ),
    "MKM-FIN-E1": (
        "data/compression/stateless_poc_finance_public_safe_v1.jsonl",
        "reports/customer_compression_stateless_poc_fin_e1_overlay_v1_latest.json",
    ),
    "MKM-MED-G1": (
        "data/compression/stateless_poc_health_public_safe_v1.jsonl",
        "reports/customer_compression_stateless_poc_med_g1_overlay_v1_latest.json",
    ),
}

DEFAULT_OUT = ROOT / "reports/compression_b2b_b1_followup_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _run(cmd: list[str], label: str) -> int:
    print(f"RUN [{label}]", " ".join(cmd))
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    if proc.stdout.strip():
        print(proc.stdout.strip()[-600:])
    if proc.returncode != 0 and proc.stderr.strip():
        print(proc.stderr.strip()[-600:], file=sys.stderr)
    return proc.returncode


def _read_summary(report: Path) -> dict[str, Any]:
    if not report.is_file():
        return {}
    doc = json.loads(report.read_text(encoding="utf-8-sig"))
    agg = doc.get("aggregate") or {}
    cc = doc.get("case_count") or 0
    cp = doc.get("cases_passed") or 0
    overlay = doc.get("must_keep_overlay") or {}
    return {
        "case_count": cc,
        "cases_passed": cp,
        "pass_rate": round(cp / cc, 4) if cc else 0.0,
        "mean_jaccard_proxy": agg.get("mean_jaccard_proxy"),
        "mean_jaccard_all_cases": agg.get("mean_jaccard_proxy_all_cases"),
        "mean_saving_proxy": agg.get("mean_token_saving_rate_proxy"),
        "overlay_applied": overlay.get("applied"),
        "overlay_term_count": overlay.get("term_count"),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--max-cases", type=int, default=30)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    steps: list[dict[str, Any]] = []
    chain_ok = True

    for sku, (corpus_rel, report_rel) in SKU_CORPUS.items():
        rc = _run(
            [
                PY,
                "scripts/run_customer_compression_stateless_poc_v1.py",
                "--input-jsonl",
                corpus_rel,
                "--sku",
                sku,
                "--auto-b2b-overlay",
                "--max-cases",
                str(args.max_cases),
                "--out-json",
                report_rel,
                "--relax-pass-gate",
            ],
            label=f"poc_overlay_{sku}",
        )
        report = ROOT / report_rel
        step = {"external_sku": sku, "exit_code": rc, "report_path": report_rel, **_read_summary(report)}
        steps.append(step)
        if rc != 0:
            chain_ok = False

    rc = _run([PY, "scripts/build_compression_b2b_industry_failure_panel_v1.py"], label="failure_panel")
    if rc != 0:
        chain_ok = False

    # Refresh primary industry bundle + gap from overlay reports
    bundle_steps = []
    for sku, (_, report_rel) in SKU_CORPUS.items():
        report = ROOT / report_rel
        if report.is_file():
            bundle_steps.append({"external_sku": sku, "report_path": report_rel, **_read_summary(report)})
    bundle_doc = {
        "schema": "compression_b2b_sku_industry_poc_bundle_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "send_gate": "HOLD",
        "wiring": "must_keep_overlay_v2_api",
        "bundle_ok": chain_ok,
        "steps": bundle_steps,
    }
    bundle_path = ROOT / "reports/compression_b2b_sku_industry_poc_bundle_v1_latest.json"
    bundle_path.write_text(json.dumps(bundle_doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    rc = _run([PY, "scripts/build_compression_b2b_industry_sku_gap_report_v1.py"], label="gap_report")
    if rc != 0:
        chain_ok = False

    panel_path = ROOT / "reports/compression_b2b_industry_failure_panel_v1_latest.json"
    panel = json.loads(panel_path.read_text(encoding="utf-8-sig")) if panel_path.is_file() else {}

    doc = {
        "schema": "compression_b2b_b1_followup_v1",
        "generated_at_utc": _utc(),
        "send_gate": "HOLD",
        "ad_headline_ready": False,
        "chain_ok": chain_ok,
        "wiring": "must_keep_overlay_terms → /v2/compress → evaluate_report",
        "steps": steps,
        "failure_panel_path": panel_path.as_posix() if panel_path.is_file() else None,
        "failure_panel_summary": panel.get("summary"),
        "gap_report_path": "reports/compression_b2b_industry_sku_gap_report_v1_latest.json",
    }
    out = args.out_json.resolve()
    out.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {out}")
    return 0 if chain_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
