#!/usr/bin/env python3
"""B2B industry Evidence v1 chain: literal+overlay bundle, gap, failure panel, reproduce refresh [HYPO]."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "reports/compression_b2b_evidence_v1_industry_chain_v1_latest.json"

INDUSTRY_BUNDLE = ROOT / "scripts/run_compression_b2b_sku_industry_poc_bundle_v1.py"
GAP = ROOT / "scripts/build_compression_b2b_industry_sku_gap_report_v1.py"
FAILURE = ROOT / "scripts/build_compression_b2b_industry_failure_panel_v1.py"
SHORT_CAP_COMPARE = ROOT / "scripts/build_compression_b2b_short_context_cap_compare_v1.py"
REPRODUCE = ROOT / "scripts/build_compression_public_reproduce_pack_v1.py"
EVIDENCE_INDEX = ROOT / "scripts/build_compression_public_evidence_pack_v0_index_v1.py"
WORKFLOW = ROOT / "scripts/build_compression_b2b_recommended_workflow_v1.py"


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _run(label: str, cmd: list[str], *, cwd: Path = ROOT) -> dict[str, Any]:
    rc = subprocess.call(cmd, cwd=str(cwd))
    return {"step": label, "cmd": cmd, "exit_code": rc}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--rows-per-sku", type=int, default=30)
    ap.add_argument(
        "--compression-profile",
        default="literal",
        choices=["economy", "fidelity", "literal", "short_cap"],
    )
    ap.add_argument("--skip-industry-bundle", action="store_true")
    ap.add_argument("--skip-gap", action="store_true")
    ap.add_argument("--skip-failure-panel", action="store_true")
    ap.add_argument("--skip-reproduce", action="store_true")
    ap.add_argument("--skip-evidence-index", action="store_true")
    ap.add_argument("--skip-workflow", action="store_true")
    args = ap.parse_args()

    py = sys.executable
    steps: list[dict[str, Any]] = []

    if not args.skip_industry_bundle:
        cmd = [
            py,
            str(INDUSTRY_BUNDLE),
            "--rows-per-sku",
            str(max(1, args.rows_per_sku)),
            "--compression-profile",
            "literal" if args.compression_profile == "short_cap" else args.compression_profile,
            "--auto-b2b-overlay",
        ]
        steps.append(_run("industry_literal_overlay_bundle", cmd))

    if not args.skip_gap:
        steps.append(_run("industry_sku_gap_report", [py, str(GAP)]))

    if not args.skip_failure_panel:
        steps.append(_run("industry_failure_panel", [py, str(FAILURE)]))

    compare_path = ROOT / "reports/compression_b2b_short_context_cap_compare_v1_latest.json"
    if compare_path.is_file():
        steps.append(
            {
                "step": "short_context_cap_compare_reuse",
                "path": str(compare_path).replace("\\", "/"),
                "exit_code": 0,
            }
        )
    elif SHORT_CAP_COMPARE.is_file():
        steps.append(_run("short_context_cap_compare", [py, str(SHORT_CAP_COMPARE)]))

    if not args.skip_reproduce:
        steps.append(_run("public_reproduce_pack_refresh", [py, str(REPRODUCE)]))

    if not args.skip_evidence_index:
        steps.append(_run("evidence_pack_v0_index_refresh", [py, str(EVIDENCE_INDEX)]))

    if not args.skip_workflow:
        steps.append(_run("b2b_recommended_workflow_refresh", [py, str(WORKFLOW)]))

    chain_ok = all(s.get("exit_code") == 0 for s in steps) and bool(steps)
    summary: dict[str, Any] = {
        "schema": "compression_b2b_evidence_v1_industry_chain_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypothesis_tier": "B",
        "send_gate": "HOLD",
        "ready_for_external_send": False,
        "ad_headline_ready": False,
        "rows_per_sku": args.rows_per_sku,
        "compression_profile": args.compression_profile,
        "industry_profile_policy": {
            "default": "literal + auto_b2b_overlay",
            "short_text_fallback": "short_context_cap (0.35 @ 40 tok) when economy min_saving_floor hurts J",
            "track_a_bridge": False,
        },
        "chain_ok": chain_ok,
        "steps": steps,
        "outputs": {
            "industry_bundle": "reports/compression_b2b_sku_industry_poc_bundle_v1_latest.json",
            "gap_report": "reports/compression_b2b_industry_sku_gap_report_v1_latest.json",
            "failure_panel": "reports/compression_b2b_industry_failure_panel_v1_latest.json",
            "short_cap_compare": "reports/compression_b2b_short_context_cap_compare_v1_latest.json",
            "reproduce_pack": "docs/final/artifacts/compression_public_reproduce_pack_v1_latest.json",
            "evidence_index": "docs/final/artifacts/compression_public_evidence_pack_v0_index_latest.json",
            "recommended_workflow": "docs/final/artifacts/compression_b2b_recommended_workflow_v1_latest.json",
        },
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if not args.skip_workflow and WORKFLOW.is_file():
        subprocess.call([py, str(WORKFLOW)], cwd=str(ROOT))

    print(json.dumps({"ok": chain_ok, "output": str(args.out_json), "steps": len(steps)}, ensure_ascii=False))
    return 0 if chain_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
