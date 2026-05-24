#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validate Logos metaphor DB themes, rebuild cards/slice/appendix, optional pytest and showroom VPS sync."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT / "docs/research/logos_metaphor_db_v1"
STOP_FILE = DEFAULT_DB / "LOGOS_THEME_RUN.stop"
STATE_PATH = ROOT / "reports/logos_theme_run_state_v1_latest.json"
LOG_PATH = ROOT / "reports/logos_theme_integrate_log.jsonl"
BUILD_CARD = ROOT / "scripts/build_logos_research_card_v1.py"
BUILD_SLICE = ROOT / "scripts/build_showroom_logos_research_slice_v1.py"
BUILD_APPENDIX = ROOT / "scripts/build_logos_b2b_appendix_v1.py"
DEPLOY_PS1 = ROOT / "projects/bitcoin-trading/ops/windows-rehearsal/deploy_showroom_static.ps1"
SYNC_PS1 = ROOT / "scripts/sync_showroom_to_vps.ps1"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _count_themes(db_dir: Path) -> int:
    return len(list(db_dir.glob("theme_*.json")))


def _load_state() -> dict[str, Any]:
    if not STATE_PATH.is_file():
        return {}
    return json.loads(STATE_PATH.read_text(encoding="utf-8-sig"))


def _save_state(payload: dict[str, Any]) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _append_log(row: dict[str, Any]) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def _run(cmd: list[str], *, cwd: Path) -> int:
    print("[logos-theme-integrate]", " ".join(cmd), flush=True)
    return subprocess.run(cmd, cwd=cwd).returncode


def main() -> int:
    ap = argparse.ArgumentParser(description="Logos theme integrate chain (Track B, NON_GATING)")
    ap.add_argument("--workspace-root", type=Path, default=ROOT)
    ap.add_argument("--db-dir", type=Path, default=DEFAULT_DB)
    ap.add_argument("--skip-pytest", action="store_true")
    ap.add_argument("--skip-deploy", action="store_true")
    ap.add_argument("--force-deploy", action="store_true", help="Deploy even if theme count unchanged")
    ap.add_argument("--dry-run", action="store_true", help="Print steps only")
    ap.add_argument(
        "--skip-if-unchanged",
        action="store_true",
        help="Exit 0 without validate/pytest when theme_count matches state file",
    )
    args = ap.parse_args()

    root = args.workspace_root.resolve()
    db_dir = args.db_dir if args.db_dir.is_absolute() else (root / args.db_dir)
    stop = db_dir / "LOGOS_THEME_RUN.stop"

    if stop.is_file() and not args.dry_run:
        msg = f"STOP file present: {stop} — integrate skipped"
        print(msg, flush=True)
        _append_log(
            {
                "timestamp_utc": _utc_now(),
                "stage": "integrate",
                "decision": "skipped_stop_file",
                "stop_file": str(stop),
            }
        )
        return 0

    theme_count = _count_themes(db_dir)
    prev = _load_state()
    prev_count = int(prev.get("theme_count", -1))
    deploy_needed = args.force_deploy or theme_count != prev_count

    if args.dry_run:
        print(f"dry_run theme_count={theme_count} prev={prev_count} deploy_needed={deploy_needed}")
        return 0

    if args.skip_if_unchanged and theme_count == prev_count and not args.force_deploy:
        print(
            f"[logos-theme-integrate] skip-if-unchanged: theme_count={theme_count} (no work)",
            flush=True,
        )
        _append_log(
            {
                "timestamp_utc": _utc_now(),
                "stage": "integrate",
                "decision": "skipped_unchanged",
                "theme_count": theme_count,
            }
        )
        return 0

    py = sys.executable
    steps: list[tuple[str, list[str]]] = [
        ("validate", [py, str(root / BUILD_CARD.relative_to(ROOT)), "--validate-only", "--db-dir", str(db_dir)]),
        (
            "cards",
            [
                py,
                str(root / BUILD_CARD.relative_to(ROOT)),
                "--out-dir",
                str(root / "reports/logos_metaphor_cards_v1"),
                "--db-dir",
                str(db_dir),
            ],
        ),
        ("slice", [py, str(root / BUILD_SLICE.relative_to(ROOT))]),
        ("appendix", [py, str(root / BUILD_APPENDIX.relative_to(ROOT))]),
    ]
    if not args.skip_pytest:
        steps.append(
            (
                "pytest",
                [
                    py,
                    "-m",
                    "pytest",
                    "tests/test_build_logos_research_card_v1.py",
                    "tests/test_build_showroom_logos_research_slice_v1.py",
                    "-q",
                ],
            )
        )

    for name, cmd in steps:
        rc = _run(cmd, cwd=root)
        if rc != 0:
            _append_log(
                {
                    "timestamp_utc": _utc_now(),
                    "stage": name,
                    "decision": "failed",
                    "theme_count": theme_count,
                    "exit_code": rc,
                }
            )
            return rc

    deploy_rc = 0
    if not args.skip_deploy and deploy_needed:
        ps = [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(root / DEPLOY_PS1.relative_to(ROOT)),
            "-WorkspaceRoot",
            str(root),
        ]
        deploy_rc = _run(ps, cwd=root)
        if deploy_rc == 0:
            sync = [
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(root / SYNC_PS1.relative_to(ROOT)),
                "-SkipDotenvUserSync",
            ]
            deploy_rc = _run(sync, cwd=root)
    elif args.skip_deploy:
        print("[logos-theme-integrate] deploy skipped (--skip-deploy)", flush=True)
    else:
        print(
            f"[logos-theme-integrate] deploy skipped (theme_count unchanged: {theme_count})",
            flush=True,
        )

    state = {
        "schema": "logos_theme_run_state_v1",
        "updated_utc": _utc_now(),
        "theme_count": theme_count,
        "prev_theme_count": prev_count,
        "deploy_ran": bool(not args.skip_deploy and deploy_needed and deploy_rc == 0),
        "track": "B",
        "gating_status": "NON_GATING",
    }
    _save_state(state)
    _append_log(
        {
            "timestamp_utc": _utc_now(),
            "stage": "integrate",
            "decision": "ok" if deploy_rc == 0 else "deploy_failed",
            **state,
            "exit_code": deploy_rc,
        }
    )
    return deploy_rc


if __name__ == "__main__":
    raise SystemExit(main())
