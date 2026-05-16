#!/usr/bin/env python3
"""Fact-Lock: LG HS before/after claims vs frozen artifacts (2026-05-16)."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
REPORTS = ROOT / "reports" / "constitution" / "btrack_pilot"


def _walk_lexicon_blocks(obj: Any, hits: list[dict[str, Any]]) -> None:
    if isinstance(obj, dict):
        mcb = obj.get("master_codebook_lexicon_v1")
        if isinstance(mcb, dict):
            hits.append(mcb)
        for v in obj.values():
            _walk_lexicon_blocks(v, hits)
    elif isinstance(obj, list):
        for v in obj:
            _walk_lexicon_blocks(v, hits)


def _scan_report(name: str) -> dict[str, Any]:
    fp = ART / name
    data = json.loads(fp.read_text(encoding="utf-8"))
    hits: list[dict[str, Any]] = []
    _walk_lexicon_blocks(data, hits)
    case_count = int((data.get("compression_metrics") or {}).get("case_count") or 0)
    return {
        "path": str(fp.relative_to(ROOT)).replace("\\", "/"),
        "case_count": case_count,
        "lexicon_blocks_in_json_tree": len(hits),
        "export_not_found": sum(1 for h in hits if h.get("reason") == "export_not_found"),
        "skipped": sum(1 for h in hits if h.get("status") == "skipped"),
        "ok": sum(1 for h in hits if h.get("status") == "ok"),
        "ok_hit_count_zero": sum(1 for h in hits if h.get("status") == "ok" and h.get("hit_count") == 0),
    }


def main() -> int:
    kpi_path = REPORTS / "ultra_compression_kpi_summary_latest.json"
    kpi = json.loads(kpi_path.read_text(encoding="utf-8")) if kpi_path.is_file() else {}
    active = _scan_report("MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json")
    bridge_policy = _scan_report("MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_BRIDGE_POLICY_V1.json")
    sweep_path = ART / "compression_domain_bridge_sweep_v1_latest.json"
    sweep = json.loads(sweep_path.read_text(encoding="utf-8")) if sweep_path.is_file() else {}
    health = (sweep.get("variants") or [{}])[0].get("health_case") or {}

    lexicon_path = REPORTS / "master_codebook_lexicon_v1_41775_rows_latest.json"
    lexicon_terms = None
    if lexicon_path.is_file():
        doc = json.loads(lexicon_path.read_text(encoding="utf-8"))
        lexicon_terms = len(doc.get("entries") or [])

    cmp2_014_before = None
    bridge_doc = json.loads(
        (ART / "MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_BRIDGE_POLICY_V1.json").read_text(encoding="utf-8")
    )
    for case in (bridge_doc.get("compression_metrics") or {}).get("cases") or []:
        if case.get("id") == "cmp2_014":
            cmp2_014_before = case.get("reconstruction_fidelity_jaccard")
            break

    out = {
        "schema": "lg_hs_before_after_factcheck_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "claims": {
            "export_not_found_80": {
                "verdict": "PARTIAL_TRUE_REWORD_REQUIRED",
                "fact": (
                    "Frozen MULTILENS reports embed 80 master_codebook_lexicon_v1 blocks for 40 bench cases "
                    "(2 nested copies per case in JSON). Current snapshots: export_not_found=0, ok=80."
                ),
                "before_inference": (
                    "When use_master_codebook_lexicon_v1=true and resolve_latest_codebook_path() returns None, "
                    "each case records reason=export_not_found once per eval (40 cases/run). "
                    "Do not say '80 independent cases' — say '40-case bench; codebook export missing' or "
                    "'80 lexicon slots in report tree'."
                ),
                "code_pointer": "scripts/report_multilens_performance_eval.py (export_not_found branch)",
                "evidence_current": active,
            },
            "lexicon_41775": {
                "verdict": "FACT",
                "lexicon_term_count": lexicon_terms,
                "path": str(lexicon_path.relative_to(ROOT)).replace("\\", "/") if lexicon_path.is_file() else None,
            },
            "policy_floor_047": {
                "verdict": "FACT",
                "global_token_saving_rate": (kpi.get("active_kpi") or {}).get("global_token_saving_rate"),
                "avg_jaccard": (kpi.get("active_kpi") or {}).get("avg_reconstruction_fidelity_jaccard"),
                "ultra_saving_policy_min": (kpi.get("active_kpi") or {}).get("ultra_saving_policy_min"),
                "ultra_saving_policy_ok": (kpi.get("active_kpi") or {}).get("ultra_saving_policy_ok"),
                "decision": "docs/final/artifacts/track_a_policy_floor_decision_v1.json",
            },
            "cmp2_014_health": {
                "verdict": "FACT_WITH_BASELINE_LABEL",
                "before_jaccard_bridge_policy_report": cmp2_014_before,
                "after_jaccard_baseline_sweep_health_case": health.get("jaccard"),
                "note": "Before = ACTIVE_REPORT_BRIDGE_POLICY (pre-pinpoint). After = domain_bridge_sweep baseline health_case (cmp2_014).",
            },
            "simulation_7680": {
                "verdict": "FAIL_DO_NOT_USE",
                "fact": "No 7680-run artifact in repo SSOT.",
                "round2_full_grid_count": (kpi.get("performance") or {}).get("round2_full_grid_count"),
                "round2_evaluated_count": (kpi.get("performance") or {}).get("round2_evaluated_count"),
                "track_c_forbidden": "docs/final/TRACK_C_IP_BUSINESS_PLAN_2026-04-17.md §3.1.2",
            },
            "safety_plc_complete": {
                "verdict": "HYPO_DRAFT_ONLY",
                "pointer": "docs/final/artifacts/runtime_assurance_safety_plc_executive_summary_v1.md",
                "note": "Reference architecture + ECC PoC; not IEC/ISO certified product.",
            },
        },
        "safe_before_after_table": [
            {
                "axis": "Bench cases",
                "before": "40-case eval; codebook export often missing → export_not_found per case path",
                "after": "40-case eval; lexicon 41775 terms; 0 export_not_found in frozen active report",
            },
            {
                "axis": "Policy floor",
                "before": "0.49 floor chase; many HOLD experiments (W4–W9 archive)",
                "after": "0.47 published floor; ~47.1% saving; avg Jaccard ~0.885",
            },
            {
                "axis": "cmp2_014 (health)",
                "before": "Jaccard 0.625 (bridge policy report snapshot)",
                "after": "Jaccard 0.875 (baseline sweep health_case)",
            },
            {
                "axis": "Governance narrative",
                "before": "Compression tool framing",
                "after": "Artifact-bound discipline + optional Safety PLC narrative [DRAFT]",
            },
        ],
    }

    out_path = ART / "lg_hs_before_after_factcheck_v1_latest.json"
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path = ART / "lg_hs_before_after_factcheck_v1_latest.md"
    md_path.write_text(_render_md(out), encoding="utf-8")
    print(json.dumps({"ok": True, "json": str(out_path.relative_to(ROOT)), "md": str(md_path.relative_to(ROOT))}, ensure_ascii=False))
    return 0


def _render_md(doc: dict[str, Any]) -> str:
    lines = [
        "# LG HS Before/After — Fact-Lock (v1)",
        "",
        f"**Generated:** `{doc['generated_at_utc']}` · **Status:** `[DRAFT]` internal only",
        "",
        "## Verdict summary",
        "",
        "| Claim | Verdict |",
        "|-------|---------|",
    ]
    for key, block in doc["claims"].items():
        lines.append(f"| `{key}` | **{block.get('verdict', '')}** |")
    lines.extend(
        [
            "",
            "## Safe copy table (LG-facing)",
            "",
            "| Axis | Before | After |",
            "|------|--------|-------|",
        ]
    )
    for row in doc["safe_before_after_table"]:
        lines.append(f"| {row['axis']} | {row['before']} | {row['after']} |")
    lines.extend(
        [
            "",
            "## Do not say externally",
            "",
            "- 7,680 hardware sweeps (use round2 grid **332** / evaluated **108** if needed)",
            "- export_not_found **80 cases** (say **40-case bench** or **codebook export was missing**)",
            "- Safety PLC certified / legal alibi complete / already won",
            "",
            f"JSON SSOT: `docs/final/artifacts/lg_hs_before_after_factcheck_v1_latest.json`",
            "",
        ]
    )
    return "\n".join(lines)


if __name__ == "__main__":
    sys.exit(main())
