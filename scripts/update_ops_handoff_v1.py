#!/usr/bin/env python3
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path


AUTO_START = "<!-- AUTO_OPS_V1_START -->"
AUTO_END = "<!-- AUTO_OPS_V1_END -->"


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _ensure_mission_log(root: Path) -> Path:
    mission = root / "MISSION_LOG.md"
    if mission.exists():
        return mission
    tpl = root / "MISSION_LOG.template.md"
    mission.write_text(tpl.read_text(encoding="utf-8"), encoding="utf-8")
    return mission


def _update_mission_log(path: Path, mission_id: str, mission_text: str, next_action: str, status: str) -> None:
    content = path.read_text(encoding="utf-8")
    row = f"| {mission_id} | {mission_text} | `{next_action}` | {status} |"
    if row in content:
        return
    anchor = "| — | (비어 있음) | — | — |"
    if anchor in content:
        content = content.replace(anchor, row)
    else:
        marker = "## Active"
        idx = content.find(marker)
        if idx != -1:
            insert_at = content.find("\n", idx)
            content = content[: insert_at + 1] + "\n" + row + "\n" + content[insert_at + 1 :]
        else:
            content = content + "\n\n## Active\n\n" + row + "\n"
    path.write_text(content, encoding="utf-8")


def _update_snapshot(path: Path, mission_id: str, mission_text: str, next_action: str, status: str) -> None:
    content = path.read_text(encoding="utf-8")
    block = (
        f"{AUTO_START}\n"
        f"## Auto Ops Handoff (v1)\n\n"
        f"- `updated_at_utc:` {_now_utc()}\n"
        f"- `mission_id:` {mission_id}\n"
        f"- `mission:` {mission_text}\n"
        f"- `status:` {status}\n"
        f"- `next_action:` `{next_action}`\n"
        f"{AUTO_END}"
    )
    if AUTO_START in content and AUTO_END in content:
        s = content.index(AUTO_START)
        e = content.index(AUTO_END) + len(AUTO_END)
        content = content[:s] + block + content[e:]
    else:
        content = content.replace("# Current ops snapshot (ephemeral handoff)\n", "# Current ops snapshot (ephemeral handoff)\n\n" + block + "\n", 1)
    path.write_text(content, encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description="Update MISSION_LOG and CURRENT_OPS_SNAPSHOT in one shot.")
    ap.add_argument("--workspace-root", default="C:/workspace")
    ap.add_argument("--mission-id", required=True)
    ap.add_argument("--mission", required=True)
    ap.add_argument("--next-action", required=True)
    ap.add_argument("--status", default="in_progress")
    args = ap.parse_args()

    root = Path(args.workspace_root).resolve()
    mission_log = _ensure_mission_log(root)
    snapshot = root / "docs" / "final" / "CURRENT_OPS_SNAPSHOT.md"

    _update_mission_log(
        mission_log,
        mission_id=str(args.mission_id),
        mission_text=str(args.mission),
        next_action=str(args.next_action),
        status=str(args.status),
    )
    _update_snapshot(
        snapshot,
        mission_id=str(args.mission_id),
        mission_text=str(args.mission),
        next_action=str(args.next_action),
        status=str(args.status),
    )
    print(f"UPDATED: {mission_log}")
    print(f"UPDATED: {snapshot}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
