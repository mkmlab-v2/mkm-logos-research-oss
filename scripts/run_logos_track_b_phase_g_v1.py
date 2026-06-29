#!/usr/bin/env python3
"""Phase G — B2B phase F + themed GraphRAG seed audit + digest + dual-backend refresh."""

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
OUT_DEFAULT = ROOT / "reports/logos_track_b_phase_g_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(name: str, cmd: list[str], *, timeout: int = 900) -> dict[str, Any]:
    t0 = time.perf_counter()
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=timeout)
    return {
        "name": name,
        "cmd": cmd,
        "exit_code": proc.returncode,
        "elapsed_sec": round(time.perf_counter() - t0, 2),
        "stdout_tail": (proc.stdout or "")[-400:],
        "stderr_tail": (proc.stderr or "")[-300:],
        "ok": proc.returncode == 0,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    ap.add_argument("--skip-phase-f", action="store_true")
    ap.add_argument("--xref-min-votes", type=int, default=10)
    args = ap.parse_args()

    steps: list[dict[str, Any]] = []

    if not args.skip_phase_f:
        steps.append(
            _run(
                "phase_f",
                [PY, "scripts/run_logos_b2b_phase_f_v1.py", "--skip-phase-e", "--xref-min-votes", str(args.xref_min_votes)],
            )
        )

    steps.append(_run("themed_graphrag_seed_audit", [PY, "scripts/audit_logos_themed_graphrag_seed_retrieval_v1.py"]))
    steps.append(_run("dual_backend_eval", [PY, "scripts/build_logos_themed_retrieval_dual_backend_eval_v1.py"]))
    steps.append(_run("dual_digest", [PY, "scripts/build_logos_commander_dual_theme_digest_v1.py"]))

    audit_path = ROOT / "reports/logos_themed_graphrag_seed_retrieval_v1_latest.json"
    audit_summary: dict[str, Any] = {}
    if audit_path.is_file():
        try:
            audit_summary = json.loads(audit_path.read_text(encoding="utf-8-sig")).get("summary") or {}
        except json.JSONDecodeError:
            pass

    overall_ok = all(s["ok"] for s in steps)
    doc = {
        "schema": "logos_track_b_phase_g_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "non_gating": True,
        "research_only": True,
        "graphrag_seed_audit": audit_summary,
        "steps": steps,
        "artifacts": {
            "digest": "reports/logos_track_b_commander_dual_theme_digest_latest.md",
            "graphrag_audit": "reports/logos_themed_graphrag_seed_retrieval_v1_latest.json",
            "dual_backend": "reports/logos_themed_retrieval_dual_backend_v1_latest.json",
            "phase_f": "reports/logos_b2b_phase_f_v1_latest.json",
        },
        "ok": overall_ok,
        "reproduce": "py scripts/run_logos_track_b_phase_g_v1.py",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": overall_ok, "out": str(args.out)}, ensure_ascii=False))
    return 0 if overall_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
