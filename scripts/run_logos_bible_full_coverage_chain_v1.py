#!/usr/bin/env python3
"""Logos Bible full-corpus work chain — audit baseline + optional preset expansion (no design/CSS).

  py scripts/run_logos_bible_full_coverage_chain_v1.py
  py scripts/run_logos_bible_full_coverage_chain_v1.py --include-preset-expansion
"""
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
OUT = ROOT / "reports/logos_bible_full_coverage_chain_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _run(name: str, cmd: list[str], *, timeout: int = 600) -> dict[str, Any]:
    proc = subprocess.run(
        cmd,
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=timeout,
    )
    tail = ((proc.stdout or "") + (proc.stderr or "")).strip()
    if len(tail) > 1200:
        tail = tail[-1200:]
    return {"step": name, "exit_code": proc.returncode, "ok": proc.returncode == 0, "tail": tail}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--include-preset-expansion", action="store_true")
    ap.add_argument("--include-corpus-bundle", action="store_true")
    ap.add_argument("--output", type=Path, default=OUT)
    args = ap.parse_args()

    steps: list[dict[str, Any]] = []
    steps.append(_run("coverage_audit", [PY, "scripts/build_logos_bible_full_coverage_audit_v1.py"]))

    if args.include_corpus_bundle:
        steps.append(_run("corpus_graph_bundle", [PY, "scripts/build_logos_corpus_graph_bundle_v1.py"]))

    if args.include_preset_expansion:
        steps.append(
            _run(
                "preset_expansion",
                [PY, "scripts/run_logos_studio_preset_expansion_chain_v1.py"],
                timeout=900,
            )
        )

    failed = [s["step"] for s in steps if not s.get("ok")]
    doc = {
        "schema": "logos_bible_full_coverage_chain_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "send_gate": "HOLD",
        "ok": len(failed) == 0,
        "failed_steps": failed,
        "steps": steps,
        "audit_artifact": "docs/final/artifacts/logos_bible_full_coverage_audit_v1_latest.json",
        "reproduce": "py scripts/run_logos_bible_full_coverage_chain_v1.py",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc["ok"], "failed": failed, "out": str(args.output)}))
    return 0 if doc["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
