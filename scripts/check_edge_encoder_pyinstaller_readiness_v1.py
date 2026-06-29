#!/usr/bin/env python3
"""Gate: Edge Encoder PyInstaller spec/readiness [HYPO] B-track."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
READINESS = ROOT / "docs/final/artifacts/edge_encoder_pyinstaller_readiness_v1_latest.json"
SPEC = ROOT / "reports/edge_encoder_sdk_pyinstaller_v1_latest/edge_encoder_sdk_cli_v1.spec"
ENTRY = ROOT / "scripts/edge_encoder_sdk_frozen_entrypoint_v1.py"


def main() -> int:
    errors: list[str] = []
    if not ENTRY.is_file():
        errors.append(f"missing entrypoint {ENTRY}")
    if not SPEC.is_file():
        errors.append(f"missing spec {SPEC}; run build_edge_encoder_sdk_pyinstaller_v1.py")
    if not READINESS.is_file():
        errors.append(f"missing readiness {READINESS}")
    else:
        doc = json.loads(READINESS.read_text(encoding="utf-8"))
        if doc.get("schema") != "edge_encoder_pyinstaller_readiness_v1":
            errors.append("readiness schema mismatch")
        if doc.get("send_gate") != "HOLD":
            errors.append("send_gate must remain HOLD")
        status = str(doc.get("status") or "")
        if status not in ("spec_ready", "spec_ready_pyinstaller_missing", "binary_built"):
            errors.append(f"unexpected status {status!r}")

    print(json.dumps({"ok": not errors, "errors": errors}, ensure_ascii=False))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
