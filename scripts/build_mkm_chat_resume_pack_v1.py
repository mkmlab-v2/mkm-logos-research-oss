from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from mkm_ops_memory_index_lib_v1 import (
    DEFAULT_INDEX_PATH,
    missing_must_keep_tags,
    top_nodes_by_priority,
    utc_now_iso,
)

SCRIPT_ROOT = Path(__file__).resolve().parents[1]


def _read_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _build_ops_inject_text(pins: List[Dict[str, Any]]) -> str:
    parts: List[str] = []
    for pin in pins:
        parts.append(pin.get("essence") or "")
        for tag in pin.get("must_keep_tags") or []:
            parts.append(tag)
    return "\n".join(parts)


def _load_ops_pins(root: Path, *, top_n: int) -> List[Dict[str, Any]]:
    index_path = root / DEFAULT_INDEX_PATH.relative_to(SCRIPT_ROOT)
    if not index_path.is_file():
        return []
    index = _read_json(index_path)
    pins: List[Dict[str, Any]] = []
    for node_id, node in top_nodes_by_priority(index, top_n=top_n):
        pins.append(
            {
                "node_id": node_id,
                "essence": node.get("essence"),
                "must_keep_tags": node.get("must_keep_tags") or [],
                "file_path": node.get("file_path"),
                "line_range": node.get("line_range"),
            }
        )
    return pins


def main() -> int:
    root = SCRIPT_ROOT
    art = root / "docs" / "final" / "artifacts"

    dashboard = _read_json(art / "mkm_trackc_ops_dashboard_latest.json")
    acceptance = _read_json(art / "mkm_trackc_operational_acceptance_latest.json")

    ops_pins = _load_ops_pins(root, top_n=2)
    inject_text = _build_ops_inject_text(ops_pins)

    if ops_pins and inject_text:
        index_path = root / DEFAULT_INDEX_PATH.relative_to(SCRIPT_ROOT)
        gate_cmd = [
            sys.executable,
            str(root / "scripts" / "check_mkm_ops_memory_must_keep_gate_v1.py"),
            "--phase",
            "inject",
            "--index",
            str(index_path),
            "--payload-text",
            inject_text,
        ]
        proc = subprocess.run(gate_cmd, capture_output=True, text=True, cwd=str(root))
        if proc.returncode != 0:
            print(proc.stdout, file=sys.stderr)
            print(proc.stderr, file=sys.stderr)
            print("FAIL: ops memory inject gate (phase=inject)", file=sys.stderr)
            return 1
        print("ops memory inject gate (phase=inject): OK")

    resume: Dict[str, Any] = {
        "schema": "mkm_chat_resume_pack_v1",
        "generated_at_utc": utc_now_iso(),
        "research_only": True,
        "boundary_ack": "[HYPO] resume pack — ops index pins are B-track; no Track A·live merge",
        "quick_refs": {
            "central_memory": "docs/final/CENTRAL_AGENT_MEMORY_V1.md",
            "ops_memory_index": "storage/meta/mkm_ops_memory_index_v1.json",
            "ops_dashboard_md": "docs/final/artifacts/mkm_trackc_ops_dashboard_latest.md",
            "ops_dashboard_exec_md": "docs/final/artifacts/mkm_trackc_ops_dashboard_exec_latest.md",
            "acceptance_json": "docs/final/artifacts/mkm_trackc_operational_acceptance_latest.json",
            "runbook_checklist_md": "docs/final/artifacts/mkm_trackc_operations_runbook_checklist_latest.md",
            "core_prompt_gemini_athena": "docs/final/artifacts/MKM_CORE_PROMPT_GEMINI_ATHENA_V1.md",
        },
        "ops_memory_pins": ops_pins,
        "latest_status": {
            "system_status": (dashboard.get("system") or {}).get("status"),
            "promotion_decision": (dashboard.get("system") or {}).get("promotion_decision"),
            "trackc_packet_status": (dashboard.get("trackc") or {}).get("packet_status"),
            "acceptance_status": acceptance.get("status"),
        },
        "resume_commands": [
            "powershell -NoProfile -ExecutionPolicy Bypass -File scripts/run_mkm_trackc_operational_acceptance.ps1",
            "powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Set-PaddleOnboardingStatus.ps1 -Status IN_PROGRESS -Note \"Payout/legal onboarding steps in progress.\"",
            "py scripts/build_mkm_ops_memory_index_v1.py",
            "py scripts/build_mkm_chat_resume_pack_v1.py",
        ],
    }

    out_json = art / "mkm_chat_resume_pack_latest.json"
    out_md = art / "mkm_chat_resume_pack_latest.md"
    out_json.write_text(json.dumps(resume, ensure_ascii=False, indent=2), encoding="utf-8")

    md_lines = [
        "# MKM Chat Resume Pack",
        "",
        f"- generated_at_utc: `{resume['generated_at_utc']}`",
        f"- research_only: `{resume.get('research_only')}`",
        f"- system_status: `{resume['latest_status'].get('system_status')}`",
        f"- promotion_decision: `{resume['latest_status'].get('promotion_decision')}`",
        f"- trackc_packet_status: `{resume['latest_status'].get('trackc_packet_status')}`",
        f"- acceptance_status: `{resume['latest_status'].get('acceptance_status')}`",
        "",
    ]
    if ops_pins:
        md_lines += ["## Ops Memory Pins ([HYPO])", ""]
        for pin in ops_pins:
            tags = ", ".join(f"`{t}`" for t in pin.get("must_keep_tags") or [])
            md_lines.append(
                f"- **{pin['node_id']}** — {pin.get('essence')} · must_keep: {tags}"
            )
        md_lines.append("")

    md_lines += ["## Quick Refs"]
    for _, path in resume["quick_refs"].items():
        md_lines.append(f"- `{path}`")
    md_lines += [
        "",
        "## Resume Commands",
        "- `py scripts/build_mkm_ops_memory_index_v1.py`",
        "- `py scripts/build_mkm_chat_resume_pack_v1.py`",
    ]
    out_md.write_text("\n".join(md_lines) + "\n", encoding="utf-8")

    print(f"resume pack json written: {out_json}")
    print(f"resume pack md written: {out_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
