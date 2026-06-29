#!/usr/bin/env python3
"""Unified preflight: Logos June 4 + AI equity 5 general_prophecy questions."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PKG = Path(__file__).resolve().parent
OUT = ROOT / "reports/general_prophecy_logos_gp_resolve_preflight_v1_latest.json"


def _run_preflight(script: str, *, under_scripts: bool) -> dict:
    path = (ROOT / "scripts" / script) if under_scripts else (PKG / script)
    cp = subprocess.run(
        [sys.executable, str(path)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    payload = {}
    if cp.stdout.strip():
        try:
            payload = json.loads(cp.stdout.strip())
        except json.JSONDecodeError:
            payload = {}
    return {"script": script, "exit_code": cp.returncode, "payload": payload}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-json", type=Path, default=OUT)
    args = ap.parse_args()

    june = _run_preflight("check_general_prophecy_logos_june_resolve_preflight_v1.py", under_scripts=True)
    equity = _run_preflight("check_logos_ai_equity_gp_resolve_preflight_v1.py", under_scripts=False)

    june_doc = {}
    if (ROOT / "reports/general_prophecy_logos_june_resolve_preflight_v1_latest.json").is_file():
        june_doc = json.loads(
            (ROOT / "reports/general_prophecy_logos_june_resolve_preflight_v1_latest.json").read_text(encoding="utf-8-sig")
        )
    equity_doc = {}
    if (ROOT / "reports/general_prophecy_logos_ai_equity_resolve_preflight_v1_latest.json").is_file():
        equity_doc = json.loads(
            (ROOT / "reports/general_prophecy_logos_ai_equity_resolve_preflight_v1_latest.json").read_text(encoding="utf-8-sig")
        )

    all_q = (june_doc.get("questions") or []) + (equity_doc.get("questions") or [])
    ready = sum(1 for q in all_q if q.get("resolve_ready_now"))

    out_doc = {
        "schema": "general_prophecy_logos_gp_resolve_preflight_v1",
        "hypothesis_tier": "B",
        "research_only": True,
        "question_count": len(all_q),
        "resolve_ready_now": ready,
        "june_preflight": june_doc.get("schema"),
        "equity_preflight": equity_doc.get("schema"),
        "questions": all_q,
        "preview_chain": "py scripts/experimental/btrack_theory_to_gp_orchestrator_v0/run_logos_gp_resolve_preview_v1.py",
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(out_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    ok = june["exit_code"] == 0 and equity["exit_code"] == 0
    print(json.dumps({"ok": ok, "resolve_ready_now": ready, "out": str(args.out_json)}))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
