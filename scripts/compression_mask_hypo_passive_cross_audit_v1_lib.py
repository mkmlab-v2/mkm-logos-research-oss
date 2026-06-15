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

CHAIN_STEPS: list[dict[str, str]] = [
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
    meta: dict[str, str],
    *,
    workspace_root: Path,
    python_exe: str | None = None,
) -> dict[str, Any]:
    script_path = workspace_root / meta["script"]
    py = python_exe or sys.executable
    proc = subprocess.run(
        [py, str(script_path)],
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
        "hypo_id": meta["hypo_id"],
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
) -> dict[str, Any]:
    steps: list[dict[str, Any]] = []
    for meta in CHAIN_STEPS:
        steps.append(run_chain_step(meta, workspace_root=workspace_root, python_exe=python_exe))
    failed = [s["step_id"] for s in steps if not s["ok"]]
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
        ],
        "workspace_root": workspace_root.as_posix(),
        "steps": steps,
        "aggregate": {
            "step_count": len(steps),
            "pass_count": sum(1 for s in steps if s["ok"]),
            "fail_count": len(failed),
            "failed_step_ids": failed,
            "all_steps_pass": len(failed) == 0,
        },
        "reproduce": "py scripts/run_compression_mask_hypo_passive_cross_audit_v1.py",
    }


def write_cross_audit_report(report: dict[str, Any], *, report_path: Path, artifact_path: Path) -> None:
    payload = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(payload, encoding="utf-8")
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    artifact_path.write_text(payload, encoding="utf-8")
