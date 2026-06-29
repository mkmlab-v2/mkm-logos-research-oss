#!/usr/bin/env python3
"""Merge latest command-package paste line into mkm_chat_resume_pack_latest.json (+ MD header)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PASTE = ROOT / "reports" / "mkm_command_package_paste_latest.json"
DEFAULT_RESUME = ROOT / "docs/final/artifacts/mkm_chat_resume_pack_latest.json"
DEFAULT_RESUME_MD = ROOT / "docs/final/artifacts/mkm_chat_resume_pack_latest.md"
GOVERNANCE_JSON = ROOT / "reports" / "amsaeng_eosa_governance_cycle_latest.json"
MCP_HYGIENE_JSON = ROOT / "reports" / "mcp_hygiene_probe_latest.json"
TERMINAL_JANITOR_JSON = ROOT / "reports" / "cursor_terminal_janitor_latest.json"
EVOLUTION_RADAR_JSON = ROOT / "reports" / "mkm_evolution_radar_daily_v1_latest.json"


def _read_json(path: Path) -> Dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def build_stop_sequence_hints(
    *,
    workspace_root: Path = ROOT,
) -> Dict[str, Any]:
    """Lightweight summary from amsaeng / MCP / terminal janitor reports (observe-only merge)."""
    hints: Dict[str, Any] = {
        "schema": "mkm_stop_sequence_hints_v1",
        "ssot_scope": "docs/final/artifacts/amsaeng_eosa_governance_scope_v1.json",
    }
    gov = _read_json(workspace_root / GOVERNANCE_JSON.relative_to(ROOT))
    if gov:
        hints["amsaeng_worst_exit"] = gov.get("worst_exit")
        phases = gov.get("phases") or []
        hints["amsaeng_phase_exits"] = {
            str(p.get("name")): p.get("exit_code")
            for p in phases
            if isinstance(p, dict) and p.get("name") is not None
        }

    mcp = _read_json(workspace_root / MCP_HYGIENE_JSON.relative_to(ROOT))
    if not mcp:
        alt = workspace_root / "reports" / "amsaeng_eosa_mcp_hygiene_cycle_latest.json"
        mcp = _read_json(alt)
    if mcp:
        hints["mcp_prereq_exit"] = mcp.get("prereq_exit_code")
        before = mcp.get("stale_process_count_before")
        after = mcp.get("stale_process_count_after")
        if before is not None:
            hints["notebooklm_stale_count_before"] = before
        if after is not None:
            hints["notebooklm_stale_count_after"] = after
        if mcp.get("repair_ran"):
            hints["notebooklm_repair_ran"] = True

    janitor = _read_json(workspace_root / TERMINAL_JANITOR_JSON.relative_to(ROOT))
    if janitor:
        summary = janitor.get("summary") or {}
        hints["cursor_terminal_stopped_count"] = summary.get("stopped_count")
        hints["cursor_terminal_skipped_count"] = summary.get("skipped_count")

    alerts: List[str] = []
    radar = _read_json(workspace_root / EVOLUTION_RADAR_JSON.relative_to(ROOT))
    if radar and radar.get("schema") == "mkm_evolution_radar_daily_v1":
        pending = [
            c
            for c in (radar.get("candidates") or [])
            if isinstance(c, dict) and c.get("approval_status") == "pending"
        ]
        hints["evolution_radar_pending_count"] = len(pending)
        if pending:
            hints["evolution_radar_top_ids"] = [str(c.get("id")) for c in pending[:3]]
            alerts.append(f"evo_radar_pending={len(pending)}")

    if hints.get("amsaeng_worst_exit") not in (None, 0):
        alerts.append(f"amsaeng_worst_exit={hints['amsaeng_worst_exit']}")
    stale_after = hints.get("notebooklm_stale_count_after")
    if stale_after is not None and int(stale_after) > 0:
        alerts.append(f"notebooklm_stale_after={stale_after}")
    if hints.get("mcp_prereq_exit") not in (None, 0):
        alerts.append(f"mcp_prereq_exit={hints['mcp_prereq_exit']}")
    stopped = hints.get("cursor_terminal_stopped_count")
    if stopped is not None and int(stopped) > 0:
        alerts.append(f"cursor_terminals_stopped={stopped}")
    hints["alert_lines"] = alerts
    return hints


def merge_patrol_into_resume(
    *,
    paste_path: Path,
    resume_json: Path,
    resume_md: Path,
    workspace_root: Path = ROOT,
) -> bool:
    paste = _read_json(paste_path)
    if not paste.get("paste_line"):
        print(f"SKIP: no paste_line in {paste_path}")
        return False

    resume = _read_json(resume_json)
    if not resume:
        print(f"SKIP: resume pack missing at {resume_json}")
        return False

    patrol: Dict[str, Any] = {
        "schema": "mkm_last_ops_patrol_v1",
        "paste_line": paste.get("paste_line"),
        "package": paste.get("package"),
        "generated_at_local": paste.get("generated_at_local"),
        "process_exit_code": paste.get("process_exit_code"),
        "optional_fail_count": paste.get("optional_fail_count"),
        "required_failed": paste.get("required_failed"),
        "source_paste_json": (
            str(paste_path.relative_to(workspace_root)).replace("\\", "/")
            if paste_path.is_relative_to(workspace_root)
            else str(paste_path)
        ),
    }
    hints = build_stop_sequence_hints(workspace_root=workspace_root)
    if hints.get("alert_lines") or hints.get("amsaeng_worst_exit") is not None:
        patrol["stop_sequence_hints"] = hints

    resume["last_ops_patrol"] = patrol
    resume_json.write_text(
        json.dumps(resume, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    if resume_md.is_file():
        md = resume_md.read_text(encoding="utf-8-sig")
        block = (
            "## Last Ops Patrol (paste helper)\n\n"
            f"- `{patrol['paste_line']}`\n\n"
        )
        alert_lines = hints.get("alert_lines") or []
        if alert_lines:
            block += "- Stop sequence hints: " + "; ".join(alert_lines) + "\n\n"
        marker = "## Ops Memory Pins"
        if marker in md and "## Last Ops Patrol" not in md:
            md = md.replace(marker, block + marker, 1)
        elif "## Last Ops Patrol" not in md:
            insert_after = "## Quick Refs"
            if insert_after in md:
                md = md.replace(insert_after, block + insert_after, 1)
            else:
                md = md.rstrip() + "\n\n" + block
        else:
            lines = md.splitlines()
            out: list[str] = []
            in_patrol = False
            for line in lines:
                if line.startswith("## Last Ops Patrol"):
                    in_patrol = True
                    out.append("## Last Ops Patrol (paste helper)")
                    out.append("")
                    out.append(f"- `{patrol['paste_line']}`")
                    if alert_lines:
                        out.append(
                            "- Stop sequence hints: " + "; ".join(alert_lines)
                        )
                    out.append("")
                    continue
                if in_patrol and line.startswith("## "):
                    in_patrol = False
                if in_patrol:
                    continue
                out.append(line)
            md = "\n".join(out) + "\n"
        resume_md.write_text(md, encoding="utf-8")

    print(f"merged last_ops_patrol into {resume_json}")
    return True


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--paste-json", type=Path, default=DEFAULT_PASTE)
    ap.add_argument("--resume-json", type=Path, default=DEFAULT_RESUME)
    ap.add_argument("--resume-md", type=Path, default=DEFAULT_RESUME_MD)
    ap.add_argument("--workspace-root", type=Path, default=ROOT)
    args = ap.parse_args()

    ok = merge_patrol_into_resume(
        paste_path=args.paste_json,
        resume_json=args.resume_json,
        resume_md=args.resume_md,
        workspace_root=args.workspace_root,
    )
    return 0 if ok else 0


if __name__ == "__main__":
    raise SystemExit(main())
