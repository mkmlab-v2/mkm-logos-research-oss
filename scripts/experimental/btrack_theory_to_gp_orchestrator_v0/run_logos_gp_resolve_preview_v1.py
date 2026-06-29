#!/usr/bin/env python3
"""Unified Logos GP resolve preview: June 4 + AI equity 5 (B-track)."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PKG = Path(__file__).resolve().parent
DEFAULT_OUT = ROOT / "reports" / "general_prophecy_logos_gp_monthly_preview_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(script: str, extra: list[str] | None = None) -> dict:
    cmd = [sys.executable, str(PKG / script), *(extra or [])]
    cp = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, check=False)
    payload = {}
    if cp.stdout.strip():
        try:
            payload = json.loads(cp.stdout.strip().splitlines()[-1])
        except json.JSONDecodeError:
            payload = {"raw_stdout": cp.stdout.strip()[-500:]}
    return {
        "script": script,
        "exit_code": cp.returncode,
        "payload": payload,
        "stderr_tail": (cp.stderr or "")[-300:],
    }


def _load_eval_summary(path: Path) -> dict | None:
    if not path.is_file():
        return None
    doc = json.loads(path.read_text(encoding="utf-8-sig"))
    rows = []
    for qid, ev in (doc.get("evaluations") or {}).items():
        rows.append(
            {
                "question_id": qid,
                "outcome_binary": ev.get("outcome_binary"),
                "window_rows": ev.get("window_rows"),
                "deadline_passed": ev.get("deadline_passed"),
            }
        )
    return {
        "schema": doc.get("schema"),
        "csv_last_date": doc.get("csv_last_date") or doc.get("csv_meta"),
        "rows": rows,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--force-apply", action="store_true")
    ap.add_argument("--run-brier", action="store_true")
    ap.add_argument("--skip-june", action="store_true")
    ap.add_argument("--skip-equity", action="store_true")
    ns = ap.parse_args()

    flags: list[str] = []
    if ns.apply:
        flags.append("--apply")
    if ns.force_apply:
        flags.append("--force-apply")
    if ns.run_brier:
        flags.append("--run-brier")

    steps: list[dict] = []
    if not ns.skip_june:
        steps.append(_run("resolve_logos_june_gp_v1.py", flags))
    if not ns.skip_equity:
        steps.append(_run("run_logos_ai_equity_gp_resolve_preview_v1.py", flags))

    ok = all(s["exit_code"] == 0 for s in steps) if steps else False
    body = {
        "schema": "general_prophecy_logos_gp_monthly_preview_v1",
        "generated_at_utc": _utc(),
        "hypothesis_tier": "B",
        "research_only": True,
        "apply_requested": ns.apply or ns.force_apply,
        "steps": steps,
        "ok": ok,
        "summaries": {
            "june": _load_eval_summary(ROOT / "reports/general_prophecy_logos_june_resolve_eval_v1_latest.json"),
            "sox": _load_eval_summary(ROOT / "reports/general_prophecy_sox_resolve_eval_v1_latest.json"),
            "nvda": _load_eval_summary(ROOT / "reports/general_prophecy_nvda_resolve_eval_v1_latest.json"),
            "qqq": _load_eval_summary(ROOT / "reports/general_prophecy_qqq_resolve_eval_v1_latest.json"),
        },
        "chains": {
            "preflight": "py scripts/experimental/btrack_theory_to_gp_orchestrator_v0/check_logos_gp_resolve_preflight_v1.py",
            "prior_ssot": "docs/final/artifacts/logos_gp_prior_provenance_v1.json",
        },
    }
    ns.out_json.parent.mkdir(parents=True, exist_ok=True)
    ns.out_json.write_text(json.dumps(body, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": ok, "out": str(ns.out_json)}, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
