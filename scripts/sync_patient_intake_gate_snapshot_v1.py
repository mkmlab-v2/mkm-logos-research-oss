#!/usr/bin/env python3
"""Sync patient intake SEND_GATE + templates into no1kmedi runtime memory."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GATE_SRC = ROOT / "docs/final/artifacts/patient_intake_send_gate_v1_latest.json"
TPL_SRC = ROOT / "docs/final/artifacts/patient_intake_notification_templates_v1.json"
DEST_DIR = ROOT / "projects/no1kmedi/memory/commercialization"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    missing = [p for p in (GATE_SRC, TPL_SRC) if not p.is_file()]
    if missing:
        print(json.dumps({"ok": False, "error": f"missing {[str(p) for p in missing]}"}))
        return 2

    if not args.dry_run:
        DEST_DIR.mkdir(parents=True, exist_ok=True)
        shutil.copy2(GATE_SRC, DEST_DIR / "patient_intake_send_gate_v1_latest.json")
        shutil.copy2(TPL_SRC, DEST_DIR / "patient_intake_notification_templates_v1.json")

    print(
        json.dumps(
            {
                "ok": True,
                "gate": str((DEST_DIR / "patient_intake_send_gate_v1_latest.json").relative_to(ROOT)).replace("\\", "/"),
                "templates": str((DEST_DIR / "patient_intake_notification_templates_v1.json").relative_to(ROOT)).replace(
                    "\\", "/"
                ),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
