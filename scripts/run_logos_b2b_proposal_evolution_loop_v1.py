#!/usr/bin/env python3
"""Logos → B2B proposal auto-evolution loop: inference → goal verifier → MASTER_SUMMARY."""

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
OUT_DEFAULT = ROOT / "reports/logos_b2b_proposal_evolution_loop_v1_latest.json"
DIGEST_MD = ROOT / "reports/logos_b2b_proposal_evolution_loop_digest_v1_latest.md"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(name: str, cmd: list[str]) -> dict[str, Any]:
    t0 = time.perf_counter()
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    return {
        "name": name,
        "cmd": cmd,
        "exit_code": proc.returncode,
        "elapsed_sec": round(time.perf_counter() - t0, 2),
        "stdout_tail": (proc.stdout or "")[-400:],
        "stderr_tail": (proc.stderr or "")[-200:],
        "ok": proc.returncode == 0,
    }


def _build_digest(doc: dict[str, Any]) -> str:
    steps = doc.get("steps") or []
    lines = [
        "# Logos → B2B Proposal Evolution Loop",
        "",
        f"> `{doc.get('generated_at_utc')}` · [TRACK B / HYPO] · NON_GATING",
        "",
        f"- **overall_ok:** `{doc.get('ok')}`",
        f"- **verdict:** `{doc.get('verdict')}`",
        f"- **b2b_target:** `{doc.get('b2b_target_id')}`",
        "",
        "## 단계",
        "",
    ]
    for s in steps:
        lines.append(f"- `{s.get('name')}`: exit={s.get('exit_code')} ok={s.get('ok')}")
    lines.extend(
        [
            "",
            "## 산출물",
            "",
            "- artifact: `docs/final/artifacts/logos_b2b_proposal_logic_artifact_v1_latest.json`",
            "- verifier: `reports/logos_b2b_proposal_goal_verifier_v1_latest.json`",
            "- MASTER_SUMMARY: `docs/final/artifacts/logos_b2b_proposal_master_summary_v1_latest.json`",
            "- MD: `reports/logos_b2b_proposal_master_summary_v1_latest.md`",
            "",
            "---",
            f"재현: `{doc.get('reproduce')}`",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    ap.add_argument("--skip-barrier-refresh", action="store_true")
    args = ap.parse_args()

    steps: list[dict[str, Any]] = []

    if not args.skip_barrier_refresh:
        steps.append(
            _run(
                "gwangmyeong_barrier_audit",
                [PY, "scripts/check_gwangmyeong_baekje_b2b_training_spec_v1.py"],
            )
        )

    steps.append(_run("inference", [PY, "scripts/build_logos_b2b_proposal_logic_artifact_v1.py"]))
    steps.append(_run("goal_verifier", [PY, "scripts/verify_logos_b2b_proposal_goal_v1.py"]))
    steps.append(_run("master_summary", [PY, "scripts/merge_logos_b2b_proposal_master_summary_v1.py"]))

    verifier_path = ROOT / "reports/logos_b2b_proposal_goal_verifier_v1_latest.json"
    verdict = "UNKNOWN"
    if verifier_path.is_file():
        try:
            vdoc = json.loads(verifier_path.read_text(encoding="utf-8-sig"))
            verdict = str(vdoc.get("verdict", "UNKNOWN"))
        except (json.JSONDecodeError, OSError):
            pass

    overall_ok = all(s["ok"] for s in steps)

    doc = {
        "schema": "logos_b2b_proposal_evolution_loop_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "non_gating": True,
        "research_only": True,
        "track_a_bridge": False,
        "b2b_target_id": "gwangmyeong_baekje",
        "steps": steps,
        "ok": overall_ok,
        "verdict": verdict,
        "reproduce": "py scripts/run_logos_b2b_proposal_evolution_loop_v1.py",
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    DIGEST_MD.write_text(_build_digest(doc), encoding="utf-8")

    print(json.dumps({"ok": overall_ok, "verdict": verdict, "out": str(args.out)}, ensure_ascii=False))
    return 0 if overall_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
