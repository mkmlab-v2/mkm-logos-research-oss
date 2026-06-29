#!/usr/bin/env python3
"""Full NotebookLM sources sync: build packs, Vault mirror, nlm push --refresh (B-track ops)."""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/notebooklm_full_sources_sync_v1_latest.json"
TMP = ROOT / "reports/tmp_nl_lens_upload"
MAP = ROOT / "reports/notebooklm_lens_packs_v1/notebook_ids.json"
MAP_TEMPLATE = ROOT / "docs/final/notebooklm_lens_pack_push_map_v1.template.json"
PORTFOLIO = ROOT / "docs/final/NOTEBOOKLM_MINIMAL_PORTFOLIO_V1.json"

sys.path.insert(0, str(ROOT / "scripts"))
from notebooklm_nlm_refresh_util_v1 import (  # noqa: E402
    list_sources,
    notebook_id_from_url_file,
    push_pack_dir,
    push_pack_index,
)


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(cmd: list[str], *, optional: bool = False) -> dict[str, Any]:
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, check=False)
    tail = (r.stdout or r.stderr or "").strip().splitlines()
    line = tail[-1] if tail else ""
    payload: dict[str, Any] = {"cmd": cmd, "exit_code": r.returncode}
    if line.startswith("{"):
        try:
            payload["result"] = json.loads(line)
        except json.JSONDecodeError:
            payload["tail"] = line[:300]
    else:
        payload["tail"] = line[:300]
    if r.returncode != 0 and not optional:
        payload["stderr"] = (r.stderr or "")[-400:]
    return payload


def _ensure_notebook_map() -> None:
    MAP.parent.mkdir(parents=True, exist_ok=True)
    if not MAP.is_file() and MAP_TEMPLATE.is_file():
        shutil.copy2(MAP_TEMPLATE, MAP)


def _portfolio_notebooks() -> list[dict[str, Any]]:
    data = json.loads(PORTFOLIO.read_text(encoding="utf-8"))
    return data.get("notebooks") or []


def main() -> int:
    phases: list[dict[str, Any]] = []

    build_steps = [
        ("build_lens_packs", [sys.executable, "scripts/build_notebooklm_lens_source_packs_v1.py"]),
        ("portfolio_map", [sys.executable, "scripts/build_notebooklm_minimal_portfolio_status_v1.py", "--write-notebook-map"]),
        ("build_ops_pack", [sys.executable, "scripts/build_notebooklm_ops_command_sync_pack_v1.py"]),
        ("build_core_fact_pack", [sys.executable, "scripts/build_notebooklm_core_fact_sync_pack_v1.py"]),
        ("build_comp_b_pack", [sys.executable, "scripts/build_notebooklm_compression_btrack_sync_pack_v1.py"]),
        ("build_clinician_pack", [sys.executable, "scripts/build_notebooklm_clinician_sync_pack_v1.py"]),
        ("build_consumer_pack", [sys.executable, "scripts/build_notebooklm_consumer_sync_pack_v1.py"]),
        ("build_smartfarm_pack", [sys.executable, "scripts/build_notebooklm_smartfarm_geumsan_sync_pack_v1.py"]),
    ]
    for name, cmd in build_steps:
        if name == "portfolio_map":
            _ensure_notebook_map()
        phases.append({"phase": name, **_run(cmd)})

    vault = _run(
        [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            "scripts/sync_notebooklm_sources_to_mkm_data_vault.ps1",
        ],
        optional=True,
    )
    phases.append({"phase": "vault_mirror", **vault})

    for script in (
        "push_han_vocology_pilot_artifacts_to_vault_v1.py",
        "push_han_vocology_curriculum_to_vault_v1.py",
    ):
        phases.append({"phase": script, **_run([sys.executable, f"scripts/{script}"], optional=True)})

    lens_push = _run(
        [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            "scripts/Push-NotebooklmLensPacks_v1.ps1",
            "-Refresh",
        ],
        optional=False,
    )
    phases.append({"phase": "push_lens_packs_refresh", **lens_push})

    pack_pushes: list[tuple[str, Path, Path]] = [
        ("push_ops", ROOT / "reports/notebooklm_ops_command_sync_pack_v1", ROOT / "reports/notebooklm_ops_command_notebook_url_v1.txt"),
        ("push_core_fact", ROOT / "reports/notebooklm_core_fact_sync_pack_v1", ROOT / "reports/notebooklm_core_fact_notebook_url_v1.txt"),
        ("push_comp_b", ROOT / "reports/notebooklm_compression_btrack_sync_pack_v1", ROOT / "reports/notebooklm_compression_btrack_notebook_url_v1.txt"),
        ("push_clinician", ROOT / "reports/notebooklm_clinician_sync_pack_v1", ROOT / "reports/notebooklm_clinician_notebook_url_v1.txt"),
        ("push_consumer", ROOT / "reports/notebooklm_consumer_sync_pack_v1", ROOT / "reports/notebooklm_consumer_notebook_url_v1.txt"),
    ]
    for name, pack, url_file in pack_pushes:
        if not url_file.is_file():
            phases.append({"phase": name, "ok": False, "skipped": True, "reason": "url_file_missing"})
            continue
        try:
            nb = notebook_id_from_url_file(url_file)
            result = push_pack_index(pack_dir=pack, notebook_id=nb, refresh=True, tmp_dir=TMP)
            phases.append({"phase": name, **result})
        except Exception as exc:  # noqa: BLE001
            phases.append({"phase": name, "ok": False, "error": str(exc)})

    lens_dir_pushes: list[tuple[str, str, str]] = [
        ("push_prophecy", "LENS_PROPHECY", "beb8bdbb-0b89-4ed2-a6fa-d586a9bee546"),
        ("push_ltm_graph_ops", "LTM_GRAPH_OPS", "9bc26140-70c4-47d0-b9ea-bd3a394916a9"),
    ]
    for name, lens_key, default_nb in lens_dir_pushes:
        pack = ROOT / "reports/notebooklm_lens_packs_v1" / lens_key
        nb = default_nb
        if MAP.is_file():
            data = json.loads(MAP.read_text(encoding="utf-8"))
            nb = str((data.get("lens_notebook_id") or {}).get(lens_key) or default_nb)
        if not pack.is_dir():
            phases.append({"phase": name, "ok": False, "skipped": True, "reason": "pack_missing"})
            continue
        result = push_pack_dir(pack_dir=pack, notebook_id=nb, refresh=True, tmp_dir=TMP)
        phases.append({"phase": name, **result})

    theory = _run(
        [sys.executable, "scripts/push_notebooklm_theory_mathematization_pack_nlm_v1.py", "--refresh"],
        optional=True,
    )
    phases.append({"phase": "push_theory_mathematization", **theory})

    han_report = ROOT / "reports/han_vocology_pilot_final_report_v1_latest.md"
    if han_report.is_file() and MAP.is_file():
        try:
            from notebooklm_nlm_refresh_util_v1 import delete_by_title, notebook_id_from_url_file

            theory_url = ROOT / "reports/notebooklm_theory_mathematization_notebook_url_v1.txt"
            if theory_url.is_file():
                nb = notebook_id_from_url_file(theory_url)
                title = "Han_Vocology_KM_VHI_Pilot_Final_M19.md"
                delete_by_title(nb, title)
                r = subprocess.run(
                    ["nlm", "source", "add", nb, "--file", str(han_report), "--title", title, "--wait"],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                phases.append(
                    {
                        "phase": "push_han_vocology_final_report",
                        "ok": r.returncode == 0,
                        "notebook_id": nb,
                        "title": title,
                        "exit_code": r.returncode,
                    }
                )
        except Exception as exc:  # noqa: BLE001
            phases.append({"phase": "push_han_vocology_final_report", "ok": False, "error": str(exc)})

    smartfarm = _run(
        [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            "scripts/push_notebooklm_smartfarm_delta_nlm_v1.ps1",
            "-Refresh",
        ],
        optional=True,
    )
    phases.append({"phase": "push_smartfarm_delta", **smartfarm})

    live_counts: list[dict[str, Any]] = []
    for nb in _portfolio_notebooks():
        uid = nb.get("uuid")
        if not uid:
            continue
        live_counts.append(
            {
                "key": nb.get("key"),
                "name": nb.get("canonical_name"),
                "uuid": uid,
                "source_count": len(list_sources(str(uid))),
            }
        )

    hard_fail = 0
    push_fail = sum(
        1
        for p in phases
        if p.get("fail", 0) > 0 or (p.get("ok") is False and not p.get("skipped"))
    )
    build_fail = sum(
        1
        for p in phases
        if p.get("exit_code", 0) != 0
        and str(p.get("phase", "")).startswith("build")
        and not (
            p.get("phase") == "build_comp_b_pack"
            and (p.get("result") or {}).get("copied", 0) > 0
        )
    )
    lens_ok = lens_push.get("exit_code", 1) == 0
    ok = lens_ok and push_fail == 0 and build_fail == 0

    report = {
        "schema": "notebooklm_full_sources_sync_v1",
        "ok": ok,
        "generated_at_utc": _utc(),
        "phases": phases,
        "live_source_counts": live_counts,
        "reproduce": ["py scripts/run_notebooklm_full_sources_sync_v1.py"],
    }
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": ok, "phases": len(phases), "push_fail": push_fail, "out": str(OUT)}, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
