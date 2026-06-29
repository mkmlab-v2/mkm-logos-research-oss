#!/usr/bin/env python3
"""Refresh MS proposal paste artifacts + optional Windows clipboard."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
MS_PACK = ROOT / "reports/external_validation_ms_evidence_pack_v1_latest"
OUT_DEFAULT = ROOT / "reports/ms_proposal_paste_ready_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _clipboard(text: str) -> bool:
    try:
        proc = subprocess.run(
            ["powershell", "-NoProfile", "-Command", "Set-Clipboard -Value $input"],
            input=text,
            text=True,
            capture_output=True,
            timeout=15,
        )
        return proc.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    ap.add_argument("--skip-ms-pack", action="store_true")
    ap.add_argument("--clipboard", action="store_true", help="Copy one-pager KO to Windows clipboard")
    ap.add_argument("--clipboard-target", choices=("one_pager", "headlines"), default="one_pager")
    args = ap.parse_args()

    ms_pack_ok = False
    if not args.skip_ms_pack:
        proc = subprocess.run(
            [PY, "scripts/build_external_validation_ms_evidence_pack_v1.py"],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        ms_pack_ok = proc.returncode == 0
        if not ms_pack_ok:
            print(proc.stderr or proc.stdout, file=sys.stderr)

    one_pager = MS_PACK / "ms_proposal_one_pager_ko_v1.txt"
    headlines = MS_PACK / "ms_proposal_headline_links_v1.txt"
    logos_pointer = MS_PACK / "ms_track_b_logos_internal_pointer_v1.txt"

    artifacts: dict[str, Any] = {}
    for label, path in (
        ("one_pager_ko", one_pager),
        ("headline_links", headlines),
        ("logos_track_b_pointer", logos_pointer),
    ):
        if path.is_file():
            text = path.read_text(encoding="utf-8")
            artifacts[label] = {
                "path": str(path.relative_to(ROOT)).replace("\\", "/"),
                "chars": len(text),
                "ready": True,
            }
        else:
            artifacts[label] = {"path": str(path.relative_to(ROOT)).replace("\\", "/"), "ready": False}

    clipboard_ok: bool | None = None
    if args.clipboard:
        target = one_pager if args.clipboard_target == "one_pager" else headlines
        if target.is_file():
            clipboard_ok = _clipboard(target.read_text(encoding="utf-8"))
        else:
            clipboard_ok = False

    paste_ready = artifacts.get("one_pager_ko", {}).get("ready") is True
    doc = {
        "schema": "ms_proposal_paste_ready_v1",
        "generated_at_utc": _utc(),
        "lane": "ms_proposal",
        "disclaimer": "internal_only — external send still human/counsel gate",
        "ms_pack_rebuilt": ms_pack_ok or args.skip_ms_pack,
        "paste_ready": paste_ready,
        "artifacts": artifacts,
        "clipboard": {
            "requested": args.clipboard,
            "target": args.clipboard_target if args.clipboard else None,
            "ok": clipboard_ok,
        },
        "human_gates_remain": [
            "VPS nginx / open-bench public binding (Tier 3)",
            "paid billing API enablement (counsel)",
            "actual email/Word paste send (operator)",
        ],
        "reproduce": "py scripts/refresh_ms_proposal_paste_artifacts_v1.py",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": paste_ready, "clipboard_ok": clipboard_ok, "out": str(args.out)}, ensure_ascii=False))
    return 0 if paste_ready else 1


if __name__ == "__main__":
    raise SystemExit(main())
