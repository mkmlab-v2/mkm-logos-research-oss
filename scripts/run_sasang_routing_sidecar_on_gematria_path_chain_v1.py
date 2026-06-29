#!/usr/bin/env python3
"""Chain: build sasang routing sidecar + gate (+ optional lens separation)."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/sasang_routing_sidecar_on_gematria_path_chain_v1_latest.json"
SIDECAR = ROOT / "docs/final/artifacts/sasang_routing_sidecar_on_gematria_path_v1_latest.json"
GATE = ROOT / "reports/sasang_routing_sidecar_on_gematria_path_gate_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(cmd: list[str]) -> tuple[int, str]:
    cp = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8")
    tail = (cp.stdout or cp.stderr or "").strip().splitlines()
    return cp.returncode, tail[-1] if tail else ""


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--skip-separation", action="store_true")
    args = ap.parse_args()

    steps: list[dict] = []
    ok = True

    for label, cmd in (
        ("build", [sys.executable, "scripts/build_sasang_routing_sidecar_on_gematria_path_v1.py"]),
        ("gate", [sys.executable, "scripts/check_sasang_routing_sidecar_on_gematria_path_v1.py"]),
    ):
        code, tail = _run(cmd)
        steps.append({"step": label, "exit_code": code, "tail": tail})
        ok = ok and code == 0

    if not args.skip_separation:
        code, tail = _run([sys.executable, "scripts/check_tkm_logos_sasang_lens_separation_v1.py"])
        steps.append({"step": "lens_separation", "exit_code": code, "tail": tail, "optional": True})
        # separation may fail if no encounter ledger rows — do not fail whole chain
        if code != 0:
            steps[-1]["note"] = "optional_smoke_failed"

    doc = {
        "schema": "sasang_routing_sidecar_on_gematria_path_chain_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "all_ok": ok,
        "send_gate": "HOLD",
        "research_only": True,
        "artifacts": {
            "sidecar": str(SIDECAR.relative_to(ROOT)).replace("\\", "/"),
            "gate": str(GATE.relative_to(ROOT)).replace("\\", "/"),
        },
        "steps": steps,
        "reproduce": "py scripts/run_sasang_routing_sidecar_on_gematria_path_chain_v1.py",
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": ok, "all_ok": ok, "out": str(OUT)}))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
