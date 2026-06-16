"""[HYPO-4] Passive cross-audit chain for MASK HYPO runners + registry (B-track).

research_only · masked corpus replay only · no live traffic · non-gating.
"""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

CHAIN_STEPS: list[dict[str, str | list[str]]] = [
    {
        "step_id": "registry_sync",
        "hypo_id": "HYPO-3",
        "script": "scripts/run_compression_mask_shadow_registry_sync_v1.py",
        "report_glob": "reports/compression_mask_shadow_registry_v1_latest.json",
    },
    {
        "step_id": "biz_overlay",
        "hypo_id": "HYPO-1a",
        "script": "scripts/run_en_business_template_overlay_scan_v1.py",
        "report_glob": "reports/en_business_template_overlay_scan_v1_latest.json",
    },
    {
        "step_id": "biz_shadow_bind",
        "hypo_id": "HYPO-2",
        "script": "scripts/run_en_business_shadow_router_bind_v1.py",
        "report_glob": "reports/en_business_shadow_router_bind_v1_latest.json",
    },
    {
        "step_id": "cs_wtt_overlay",
        "hypo_id": "HYPO-1b",
        "script": "scripts/run_ko_premium_cs_wtt_template_overlay_scan_v1.py",
        "report_glob": "reports/ko_premium_cs_wtt_template_overlay_scan_v1_latest.json",
    },
]

# SKU-COORD sibling — axis isolated from MASK KPI (FAIL-COMP-004)
COORD_SIBLING_STEP: dict[str, str | list[str]] = {
    "step_id": "rib55_coord_passive",
    "hypo_id": "COORD-1",
    "script": "scripts/run_rib55_coord_passive_audit_v1.py",
    "script_args": ["--skip-pytest"],
    "report_glob": "docs/final/artifacts/rib55_coord_passive_audit_v1_latest.json",
    "axis": "SKU-COORD",
}


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_stdout_json(text: str) -> dict[str, Any] | None:
    for line in reversed((text or "").strip().splitlines()):
        line = line.strip()
        if line.startswith("{") and line.endswith("}"):
            try:
                doc = json.loads(line)
                return doc if isinstance(doc, dict) else None
            except json.JSONDecodeError:
                continue
    return None


def run_chain_step(
    meta: dict[str, str | list[str]],
    *,
    workspace_root: Path,
    python_exe: str | None = None,
) -> dict[str, Any]:
    script_path = workspace_root / str(meta["script"])
    py = python_exe or sys.executable
    cmd = [py, str(script_path)] + list(meta.get("script_args") or [])
    proc = subprocess.run(
        cmd,
        cwd=str(workspace_root),
        capture_output=True,
        text=True,
        check=False,
    )
    stdout_doc = _parse_stdout_json(proc.stdout)
    report_path = workspace_root / meta["report_glob"]
    report_summary: dict[str, Any] | None = None
    if report_path.is_file():
        try:
            report_doc = json.loads(report_path.read_text(encoding="utf-8-sig"))
            if isinstance(report_doc, dict):
                report_summary = {
                    "schema": report_doc.get("schema"),
                    "aggregate": report_doc.get("aggregate"),
                }
        except Exception:
            report_summary = None
    return {
        "step_id": meta["step_id"],
        "hypo_id": meta.get("hypo_id"),
        "axis": meta.get("axis"),
        "script": meta["script"],
        "exit_code": int(proc.returncode),
        "ok": proc.returncode == 0,
        "stdout_tail": (proc.stdout or "")[-800:],
        "stderr_tail": (proc.stderr or "")[-400:] if proc.stderr else "",
        "stdout_json": stdout_doc,
        "report_path": report_path.as_posix() if report_path.is_file() else None,
        "report_summary": report_summary,
    }


def run_passive_cross_audit(
    *,
    workspace_root: Path = ROOT,
    python_exe: str | None = None,
    include_coord_sibling: bool = True,
) -> dict[str, Any]:
    steps: list[dict[str, Any]] = []
    for meta in CHAIN_STEPS:
        steps.append(run_chain_step(meta, workspace_root=workspace_root, python_exe=python_exe))
    coord_sibling: dict[str, Any] | None = None
    if include_coord_sibling:
        coord_sibling = run_chain_step(COORD_SIBLING_STEP, workspace_root=workspace_root, python_exe=python_exe)
    failed = [s["step_id"] for s in steps if not s["ok"]]
    coord_failed = coord_sibling is not None and not coord_sibling.get("ok")
    if coord_failed and coord_sibling:
        failed.append(coord_sibling["step_id"])
    return {
        "schema": "compression_mask_hypo_passive_cross_audit_v1",
        "generated_at_utc": _utc(),
        "hypothesis_tier": "B",
        "research_only": True,
        "shadow_only": True,
        "non_gating": True,
        "send_gate": "HOLD",
        "track_a_active_untouched": True,
        "input_policy": "masked_corpus_jsonl_replay_only",
        "forbidden": [
            "live_trade_traffic",
            "production_domain_router_mutation",
            "customer_sla_headline_from_hypo_min_saving",
            "mask_kpi_merge_with_coord_sibling",
        ],
        "workspace_root": workspace_root.as_posix(),
        "steps": steps,
        "coord_sibling": coord_sibling,
        "aggregate": {
            "step_count": len(steps) + (1 if coord_sibling else 0),
            "pass_count": sum(1 for s in steps if s["ok"]) + (1 if coord_sibling and coord_sibling.get("ok") else 0),
            "fail_count": len(failed),
            "failed_step_ids": failed,
            "all_steps_pass": len(failed) == 0,
            "mask_step_count": len(steps),
            "coord_sibling_included": coord_sibling is not None,
        },
        "reproduce": "py scripts/run_compression_mask_hypo_passive_cross_audit_v1.py",
    }


def write_cross_audit_report(report: dict[str, Any], *, report_path: Path, artifact_path: Path) -> None:
    payload = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(payload, encoding="utf-8")
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    artifact_path.write_text(payload, encoding="utf-8")
