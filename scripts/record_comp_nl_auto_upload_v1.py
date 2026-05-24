#!/usr/bin/env python3
"""Record NL B-track auto upload result on disk (no transcript merge)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PILOT = ROOT / "reports/constitution/btrack_pilot"
LOG = ROOT / "reports/notebooklm_btrack_lens_pack_push_latest.log"
OUT = PILOT / "comp_nl_auto_upload_result_v1.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    log_tail = ""
    if LOG.is_file():
        lines = LOG.read_text(encoding="utf-8", errors="replace").splitlines()
        log_tail = "\n".join(lines[-40:])

    ok = fail = skip = 0
    for line in log_tail.splitlines():
        if " ok=" in line and "fail=" in line and "===" in line:
            # === Done ok=20 fail=0 skip=2 ===
            parts = line.replace("===", "").strip().split()
            for p in parts:
                if p.startswith("ok="):
                    ok = int(p.split("=", 1)[1])
                elif p.startswith("fail="):
                    fail = int(p.split("=", 1)[1])
                elif p.startswith("skip="):
                    skip = int(p.split("=", 1)[1])

    doc = {
        "schema": "comp_nl_auto_upload_result_v1",
        "generated_at_utc": _utc(),
        "commander_approved": True,
        "method": "nlm_cli",
        "script": "scripts/Push-NotebooklmBtrackLensPacks_v1.ps1",
        "packs": {
            "COMPRESSION_BTRACK": {
                "notebook_id": "aba1f8b1-be62-4367-ac7f-b1a997bb77d4",
                "notebook_label": "MKM_CORE_INTELLIGENCE_V1",
            },
            "IJEOMA_BTRACK": {
                "notebook_id": "af639d3e-b455-4f3f-8e25-47f58d962c60",
                "notebook_label": "ijeoma_b_research",
            },
        },
        "ok": ok,
        "fail": fail,
        "skip": skip,
        "success": fail == 0 and ok > 0,
        "log_path": str(LOG.relative_to(ROOT)).replace("\\", "/"),
        "log_tail": log_tail,
    }
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"wrote": OUT.name, "success": doc["success"], "ok": ok, "fail": fail}, ensure_ascii=False))
    return 0 if doc["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
