#!/usr/bin/env python3
"""One-shot automation: vault mirror → bundle → NL pack → push → MCP register → wiki."""
from __future__ import annotations

import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
URL_FILE = ROOT / "reports" / "notebooklm_theory_mathematization_notebook_url_v1.txt"
NOTEBOOK_NAME = "23_MKM_THEORY_MATHEMATIZATION_2026Q2"
REPORT = ROOT / "docs/final/artifacts/mkm_theory_mathematization_automation_report_v1_latest.json"

STEPS: list[tuple[str, list[str]]] = [
    ("mirror_vault", [sys.executable, "scripts/mirror_mkm12_math_vault_to_workspace_v1.py"]),
    ("formula_bundle", [sys.executable, "scripts/build_mkm_formula_ssot_bundle_v1.py"]),
    ("worldview_crosslink_bridge", [sys.executable, "scripts/build_worldview_formula_crosslink_bridge_v1.py"]),
    ("gap_map", [sys.executable, "scripts/build_theory_reflection_gap_map_v1.py"]),
    ("promotion_registry", [sys.executable, "scripts/build_mkm_theory_formula_promotion_registry_v1.py"]),
    ("utf8_vault_manifest", [sys.executable, "scripts/build_notebooklm_vault_sync_utf8_manifest_v1.py"]),
    ("promotion_gate_dryrun", [sys.executable, "scripts/run_mkm_theory_formula_promotion_gate_dryrun_v1.py"]),
    ("theory_ops_overlay", [sys.executable, "scripts/build_mkm_ops_memory_theory_overlay_v1.py"]),
    ("build_nl_pack", [sys.executable, "scripts/build_notebooklm_theory_mathematization_pack_v1.py"]),
    ("wiki_synthesis", [sys.executable, "scripts/synthesize_llm_wiki_theory_mathematization_v1.py"]),
    ("push_nl_pack", [sys.executable, "scripts/push_notebooklm_theory_mathematization_pack_nlm_v1.py", "--refresh"]),
    ("register_mcp", [sys.executable, "scripts/register_notebooklm_theory_mathematization_mcp_v1.py"]),
    ("nl_guard_smoke", [sys.executable, "scripts/run_notebooklm_theory_mathematization_nl_guard_smoke_v1.py", "--skip-mcp"]),
    ("vault_utf8_mirror", [sys.executable, "scripts/mirror_theory_mathematization_paths_to_vault_v1.py"]),
    ("phase3_smoke", [sys.executable, "scripts/run_mkm_theory_mathematization_phase3_smoke_v1.py"]),
]


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run_step(name: str, cmd: list[str]) -> dict:
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    return {
        "step": name,
        "cmd": cmd,
        "exit_code": r.returncode,
        "stdout_tail": (r.stdout or "")[-800:],
        "stderr_tail": (r.stderr or "")[-400:] if r.stderr else None,
    }


def _ensure_notebook_url() -> dict:
    if URL_FILE.is_file():
        url = URL_FILE.read_text(encoding="utf-8").strip()
        if re.search(r"notebook/[0-9a-f-]{36}", url, re.I):
            return {"step": "ensure_notebook", "skipped": True, "url": url}
    r = subprocess.run(
        ["nlm", "notebook", "create", NOTEBOOK_NAME],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    out = (r.stdout or "") + (r.stderr or "")
    m = re.search(r"ID:\s*([0-9a-f-]{36})", out, re.I)
    if not m:
        m = re.search(r"([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})", out, re.I)
    if not m:
        return {"step": "ensure_notebook", "exit_code": r.returncode or 1, "error": out[-500:]}
    nb_id = m.group(1)
    url = f"https://notebooklm.google.com/notebook/{nb_id}"
    URL_FILE.write_text(url + "\n", encoding="utf-8")
    return {"step": "ensure_notebook", "exit_code": 0, "notebook_id": nb_id, "url": url}


def _vault_mirror_ps() -> dict:
    ps = ROOT / "scripts" / "sync_notebooklm_sources_to_mkm_data_vault.ps1"
    if not ps.is_file():
        return {"step": "vault_mirror_ps", "skipped": True, "reason": "script missing"}
    r = subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(ps),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    return {
        "step": "vault_mirror_ps",
        "exit_code": r.returncode,
        "stdout_tail": (r.stdout or "")[-600:],
        "stderr_tail": (r.stderr or "")[-300:] if r.stderr else None,
    }


def main() -> int:
    ts = utc_now()
    results: list[dict] = []
    results.append(_ensure_notebook_url())
    if results[-1].get("exit_code", 0) != 0 and not results[-1].get("skipped"):
        _write_report(ts, results, fail_fast=True)
        return 1

    for name, cmd in STEPS:
        row = _run_step(name, cmd)
        results.append(row)
        if row["exit_code"] != 0:
            _write_report(ts, results, fail_fast=True)
            return 1

    results.append(_vault_mirror_ps())
    vault_exit = results[-1].get("exit_code", 0)
    _write_report(ts, results, fail_fast=False)
    return 0 if vault_exit == 0 else 1


def _write_report(ts: str, results: list[dict], *, fail_fast: bool) -> None:
    report = {
        "schema": "mkm_theory_mathematization_automation_report_v1",
        "generated_at_utc": ts,
        "fail_fast": fail_fast,
        "steps": results,
        "notebook_url": URL_FILE.read_text(encoding="utf-8").strip() if URL_FILE.is_file() else None,
        "ok": all(r.get("exit_code", 0) == 0 or r.get("skipped") for r in results),
    }
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    raise SystemExit(main())
