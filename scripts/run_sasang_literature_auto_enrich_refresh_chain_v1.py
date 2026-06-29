#!/usr/bin/env python3
"""Literature auto-enrich refresh: stub enrich → resolve → supervised gate [HYPO]."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
OUT = ROOT / "reports/sasang_literature_auto_enrich_refresh_chain_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(name: str, script: str, extra: list[str] | None = None) -> dict[str, Any]:
    t0 = time.perf_counter()
    cmd = [PY, str(ROOT / "scripts" / script)] + (extra or [])
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    return {
        "name": name,
        "script": script,
        "exit_code": proc.returncode,
        "elapsed_sec": round(time.perf_counter() - t0, 2),
        "stdout_tail": (proc.stdout or "")[-300:],
        "ok": proc.returncode == 0,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()

    steps: list[dict[str, Any]] = []
    for name, script in (
        ("review_queue", "build_sasang_saju_joint_review_queue_from_catalog_v1.py"),
        ("auto_enrich", "auto_enrich_sasang_from_literature_stub_v1.py"),
        ("supervised_chain", "run_sasang_literature_supervised_chain_v1.py"),
    ):
        steps.append(_run(name, script))
        if not steps[-1]["ok"]:
            break

    gate_path = ROOT / "docs/final/artifacts/sasang_literature_supervised_gate_v1_latest.json"
    gate = json.loads(gate_path.read_text(encoding="utf-8-sig")) if gate_path.is_file() else {}

    doc = {
        "schema": "sasang_literature_auto_enrich_refresh_chain_v1",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "steps": steps,
        "all_ok": all(s["ok"] for s in steps),
        "literature_supervised_status": gate.get("literature_supervised_status"),
        "literature_supervised_rows": gate.get("rows"),
        "reproduce": "py scripts/run_sasang_literature_auto_enrich_refresh_chain_v1.py",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc["all_ok"], "literature_supervised_status": doc.get("literature_supervised_status")}))
    return 0 if doc["all_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
