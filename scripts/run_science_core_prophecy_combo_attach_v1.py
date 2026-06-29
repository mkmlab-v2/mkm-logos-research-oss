#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Prophecy lens combo backtest gated by science_core governance attach [HYPO]."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_GOV = ROOT / "docs/final/artifacts/science_core_governance_bundle_v1_latest.json"
DEFAULT_OUT = ROOT / "docs/final/artifacts/prophecy_lens_combo_backtest_science_core_v1_latest.json"
DEFAULT_SCORE = ROOT / "reports/btrack_prophecy_score_science_core_panel_v1.json"
DEFAULT_SIDECAR = ROOT / "reports/btrack_prophecy_score_insight_sidecar_science_core_panel_v1.json"
DEFAULT_SCIENCE_JSONL = ROOT / "reports/btrack_science_core_per_date_kospi_v1.jsonl"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def resolve_governance_attach(governance_path: Path) -> dict[str, Any]:
    if not governance_path.is_file():
        return {
            "governance_path": str(governance_path),
            "exists": False,
            "composite_attach_recommended": False,
            "recommended_lane": None,
            "track_a_ready": False,
            "live_trading_ready": False,
            "skip_reason": "governance_bundle_missing",
        }
    doc = json.loads(governance_path.read_text(encoding="utf-8-sig"))
    attach = doc.get("composite_attach") or {}
    promo = doc.get("promotion_gate") or {}
    recommended = attach.get("recommended_lane")
    composite = bool(attach.get("composite_attach_recommended"))
    return {
        "governance_path": str(governance_path),
        "exists": True,
        "composite_attach_recommended": composite,
        "recommended_lane": recommended,
        "track_a_ready": bool(promo.get("track_a_ready")),
        "live_trading_ready": bool(promo.get("live_trading_ready")),
        "research_only": bool(doc.get("research_only", True)),
        "skip_reason": None if composite else "composite_attach_not_recommended",
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--governance-json", type=Path, default=DEFAULT_GOV)
    ap.add_argument("--score-json", type=Path, default=DEFAULT_SCORE)
    ap.add_argument("--sidecar-json", type=Path, default=DEFAULT_SIDECAR)
    ap.add_argument("--science-jsonl", type=Path, default=DEFAULT_SCIENCE_JSONL)
    ap.add_argument("--target-instrument", default="kospi")
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--force-run", action="store_true", help="Run combo even if attach gate false (research).")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)

    gate = resolve_governance_attach(args.governance_json)
    run_combo = bool(gate.get("composite_attach_recommended")) or bool(args.force_run)

    if not run_combo:
        payload = {
            "schema": "science_core_prophecy_combo_attach_v1",
            "generated_at_utc": _utc_now(),
            "research_only": True,
            "governance_gate": gate,
            "combo_backtest_ran": False,
            "note_ko": "composite attach 미권고 — prophecy combo science arms 스킵. Track A·실매매 합선 없음.",
        }
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"SKIP: composite attach false -> {args.output}")
        return 0

    if args.dry_run:
        print(f"DRY_RUN: would run prophecy combo attach lane={gate.get('recommended_lane')}")
        return 0

    cmd = [
        sys.executable,
        str(ROOT / "scripts/run_prophecy_lens_combo_backtest_v1.py"),
        "--score-json",
        str(args.score_json),
        "--sidecar-json",
        str(args.sidecar_json),
        "--target-instrument",
        str(args.target_instrument),
        "--include-science-core",
        "--science-jsonl",
        str(args.science_jsonl),
        "--logos-vote-mode",
        "omit",
        "--output",
        str(args.output),
    ]
    proc = subprocess.run(cmd, cwd=str(ROOT), check=False)
    wrapper = {
        "schema": "science_core_prophecy_combo_attach_v1",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "governance_gate": gate,
        "combo_backtest_ran": proc.returncode == 0,
        "combo_backtest_exit_code": proc.returncode,
        "combo_output": str(args.output),
        "recommended_lane": gate.get("recommended_lane"),
        "note_ko": (
            "governance composite attach 통과 시에만 science-core prophecy combo 실행. "
            "Track A·실매매 자동 승격 아님."
        ),
    }
    sidecar_path = args.output.with_name("prophecy_lens_combo_science_core_attach_gate_v1_latest.json")
    sidecar_path.parent.mkdir(parents=True, exist_ok=True)
    sidecar_path.write_text(json.dumps(wrapper, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"combo_exit={proc.returncode} gate={gate.get('recommended_lane')} wrapper={sidecar_path}")
    return proc.returncode


if __name__ == "__main__":
    raise SystemExit(main())
