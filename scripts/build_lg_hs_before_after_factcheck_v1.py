#!/usr/bin/env python3
"""Fact-Lock: LG HS before/after claims vs frozen artifacts (2026-05-16)."""

from __future__ import annotations

import json
import subprocess
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
REPORTS = ROOT / "reports" / "btrack_pilot"


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


def _per_shard_jaccard(active_path: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    data = json.loads(active_path.read_text(encoding="utf-8"))
    metrics = data.get("compression_metrics") or {}
    cases = metrics.get("cases") or []
    by_shard: dict[str, list[float]] = defaultdict(list)
    for case in cases:
        if not isinstance(case, dict):
            continue
        route = case.get("route") or {}
        sid = str(route.get("shard_id") or "unknown")
        jac = case.get("reconstruction_fidelity_jaccard")
        if isinstance(jac, (int, float)):
            by_shard[sid].append(float(jac))
    global_saving = metrics.get("global_token_saving_rate")
    rows: list[dict[str, Any]] = []
    for sid in sorted(by_shard):
        vals = by_shard[sid]
        rows.append(
            {
                "shard_id": sid,
                "case_count": len(vals),
                "avg_jaccard": sum(vals) / len(vals) if vals else None,
                "min_jaccard": min(vals) if vals else None,
                "note": "token_saving_rate is global-only on this bench; do not repeat per shard.",
            }
        )
    globals_block = {
        "case_count": metrics.get("case_count"),
        "global_token_saving_rate": global_saving,
        "avg_reconstruction_fidelity_jaccard": metrics.get("avg_reconstruction_fidelity_jaccard"),
        "min_reconstruction_fidelity_jaccard": metrics.get("min_reconstruction_fidelity_jaccard"),
    }
    return rows, globals_block


def _pytest_ultra_artifact_count() -> dict[str, Any]:
    cmd = [sys.executable, "-m", "pytest", "tests/test_ultra_compression_artifacts.py", "-q", "--tb=no"]
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    tail = (proc.stdout or "").strip()
    passed = None
    for line in tail.splitlines():
        if "passed" in line:
            parts = line.split()
            for i, p in enumerate(parts):
                if p == "passed" and i > 0:
                    try:
                        passed = int(parts[i - 1])
                    except ValueError:
                        pass
    return {"exit_code": proc.returncode, "pytest_tail": tail, "passed_count": passed}


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

    active_path = ART / "MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json"
    shard_rows, global_metrics = _per_shard_jaccard(active_path)

    shadow_path = REPORTS / "compression_shadow_auditor_latest.json"
    shadow = json.loads(shadow_path.read_text(encoding="utf-8")) if shadow_path.is_file() else {}
    pytest_meta = _pytest_ultra_artifact_count()

    conc10_path = ART / "bench_l1_api_load_conc10_latest.json"
    conc10 = json.loads(conc10_path.read_text(encoding="utf-8")) if conc10_path.is_file() else {}
    vps_summary_path = ART / "bench_l1_api_load_summary_vps_latest.json"
    vps_summary = json.loads(vps_summary_path.read_text(encoding="utf-8")) if vps_summary_path.is_file() else {}
    corr_path = ART / "compression_board_ms_correlation_report_v1_latest.json"
    corr = json.loads(corr_path.read_text(encoding="utf-8")) if corr_path.is_file() else {}

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
            "domain_table_per_shard_saving": {
                "verdict": "FAIL_DO_NOT_USE",
                "fact": "global_token_saving_rate applies to full 40-case bench only; repeating ~47% on each shard row misleads.",
                "global_token_saving_rate": global_metrics.get("global_token_saving_rate"),
            },
            "domain_table_scm_avg_067": {
                "verdict": "FAIL_DO_NOT_USE",
                "fact": "SCM shard avg_jaccard ~0.866; min_jaccard 0.667 is worst-case within scm cases / global min — not domain average headline.",
                "scm_shard": next((r for r in shard_rows if r["shard_id"] == "zone_a_scm"), None),
            },
            "domain_table_timing_091": {
                "verdict": "FAIL_DO_NOT_USE",
                "fact": "zone_b_timing avg_jaccard ~0.845 on frozen bench (2 cases), not ~0.910.",
                "timing_shard": next((r for r in shard_rows if r["shard_id"] == "zone_b_timing"), None),
            },
            "shadow_auditor_17_of_17": {
                "verdict": "FAIL_DO_NOT_USE",
                "fact": "tests/test_ultra_compression_artifacts.py is 4 contract tests; not 17/17.",
                "pytest": pytest_meta,
                "shadow_auditor": {
                    "audit_ok": shadow.get("audit_ok"),
                    "pytest_target": (shadow.get("pytest") or {}).get("target"),
                },
                "accurate_wording": (
                    "Nightly Shadow Auditor: frozen KPI/active-report contract pytest + loss-pattern queue; "
                    "full 40-case re-bench only with --refresh-bench (weekly governance optional)."
                ),
            },
            "bench_conc10_as_production_sla": {
                "verdict": "PARTIAL_TRUE_REWORD_REQUIRED",
                "conc10": {
                    "bench_environment": conc10.get("bench_environment"),
                    "max_concurrent": conc10.get("max_concurrent"),
                    "approx_word_tokens": conc10.get("approx_word_tokens"),
                    "latency_ms": conc10.get("latency_ms"),
                    "pass_p95_vs_target": (conc10.get("draft_targets_comparison") or {}).get("pass_p95_vs_target"),
                },
                "vps_same_host_summary": {
                    "bench_environment": vps_summary.get("bench_environment"),
                    "latency_ms": vps_summary.get("latency_ms"),
                },
                "correlation_claim_allowed": (corr.get("derived") or {}).get("correlation_claim_allowed"),
                "note": "Do not cite loopback conc10 p95 as token-saving proof; separate RTT layer from bench saving.",
            },
            "jaccard_equals_meaning_percent": {
                "verdict": "FAIL_DO_NOT_USE",
                "fact": "Jaccard is token/word overlap proxy on 40-case bench; not semantic meaning %.",
            },
            "multi_shard_simultaneous_activation": {
                "verdict": "FAIL_DO_NOT_USE",
                "fact": (
                    "Track A compress path selects one winning shard per document via keyword score "
                    "(scripts/core/domain_router.py). Not multi-shard overlay on a single pass."
                ),
                "code_pointer": "scripts/core/domain_router.py · scripts/report_multilens_performance_eval.py",
                "accurate_wording": (
                    "41k lexicon always ON + best-fit zone_*.json shard; multi-shard union = roadmap only."
                ),
            },
            "plugin_lora_zero_training_cost": {
                "verdict": "FAIL_DO_NOT_USE",
                "fact": (
                    "No runtime weight LoRA on Track A compress path; JSON shard packs are KB-scale. "
                    "Export/curation and bench signoff still have engineering cost."
                ),
                "accurate_wording": "Runtime fine-tuning not required; not 'training cost $0 forever'.",
            },
            "zone_c_health_filename": {
                "verdict": "FAIL_DO_NOT_USE",
                "fact": "Health shard file is codebook/shards/zone_g_health.json (not zone_c_health).",
                "path": "codebook/shards/zone_g_health.json",
            },
            "plugin_shard_single_route": {
                "verdict": "FACT",
                "fact": (
                    "use_domain_router=True loads zone_*.json; route() picks max routing_keywords hit; "
                    "must_keep from that shard unions with master_codebook_lexicon_v1 when enabled."
                ),
                "shard_count_loaded": len(
                    list((ROOT / "codebook" / "shards").glob("zone_*.json"))
                )
                if (ROOT / "codebook" / "shards").is_dir()
                else None,
            },
        },
        "frozen_bench_shard_jaccard": shard_rows,
        "frozen_bench_global": global_metrics,
        "lg_safe_domain_table": [
            {
                "label": "Global (40-case bench)",
                "case_count": global_metrics.get("case_count"),
                "avg_jaccard": global_metrics.get("avg_reconstruction_fidelity_jaccard"),
                "min_jaccard": global_metrics.get("min_reconstruction_fidelity_jaccard"),
                "token_saving_rate": global_metrics.get("global_token_saving_rate"),
            },
            *[
                {
                    "label": row["shard_id"],
                    "case_count": row["case_count"],
                    "avg_jaccard": row["avg_jaccard"],
                    "min_jaccard": row["min_jaccard"],
                    "token_saving_rate": "(global only — not per-shard)",
                }
                for row in shard_rows
            ],
        ],
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
            "## LG-safe shard Jaccard (frozen active report)",
            "",
            "| Label | n | avg Jaccard | min Jaccard | token saving |",
            "|-------|---|-------------|-------------|--------------|",
        ]
    )
    for row in doc.get("lg_safe_domain_table") or []:
        saving = row.get("token_saving_rate")
        if isinstance(saving, (int, float)):
            saving_s = f"{float(saving) * 100:.2f}%"
        else:
            saving_s = str(saving)
        avg_j = row.get("avg_jaccard")
        min_j = row.get("min_jaccard")
        avg_s = f"{avg_j:.3f}" if isinstance(avg_j, (int, float)) else str(avg_j)
        min_s = f"{min_j:.3f}" if isinstance(min_j, (int, float)) else str(min_j)
        lines.append(f"| {row.get('label')} | {row.get('case_count')} | {avg_s} | {min_s} | {saving_s} |")

    lines.extend(
        [
            "",
            "## Governance proofs (accurate wording)",
            "",
            "- **Lexicon:** 41,775 terms frozen (`master_codebook_lexicon_v1_41775_rows_latest.json`).",
            "- **Shadow Auditor:** artifact contract pytest (**4 tests**, not 17/17) + KPI/active scan; optional `--refresh-bench` for full re-run.",
            "- **Latency:** `bench_l1_api_load_conc10` = local loopback, conc10, ~500 words — **not** production SLA; VPS p95 ~665–847 ms (2026-05-16 triplet). **Do not** link ms to token saving (`correlation_claim_allowed: false`).",
            "",
            "## Do not say externally",
            "",
            "- 7,680 hardware sweeps (use round2 grid **332** / evaluated **108** if needed)",
            "- export_not_found **80 cases** (say **40-case bench** or **codebook export was missing**)",
            "- Safety PLC certified / legal alibi complete / already won",
            "- **Per-shard 47% saving** (saving is global on 40-case bench only)",
            "- **SCM domain average 0.667** (use: scm min ~0.667, scm avg ~0.866, global min 0.667)",
            "- **Timing ~0.910** (use ~0.845 on 2 timing cases)",
            "- **Shadow Auditor 17/17 passed** (use **4 contract tests passed**)",
            "- **의미 89% 복원** (use **avg Jaccard ~0.885 proxy**)",
            "- **conc10 45/980 ms = 양산 보드 SLA** (cite environment + fail vs 200ms target; prefer VPS triplet for external RTT)",
            "",
            f"JSON SSOT: `docs/final/artifacts/lg_hs_before_after_factcheck_v1_latest.json`",
            "",
        ]
    )
    return "\n".join(lines)


if __name__ == "__main__":
    sys.exit(main())
