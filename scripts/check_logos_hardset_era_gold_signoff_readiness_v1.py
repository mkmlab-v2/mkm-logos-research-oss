#!/usr/bin/env python3
"""Readiness gate for hardset v2 human gold overrides (B-track, not MS)."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OV = ROOT / "docs/final/artifacts/fixtures/logos_chronology_hardset_era_gold_overrides_v1.json"
DEFAULT_EVAL = ROOT / "docs/final/artifacts/logos_chronology_hardset_text_blind_v2_eval_v1_latest.json"
DEFAULT_OUT = ROOT / "reports/logos_hardset_era_gold_signoff_readiness_v1_latest.json"


def _load(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return obj if isinstance(obj, dict) else None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--overrides-json", type=Path, default=DEFAULT_OV)
    ap.add_argument("--eval-json", type=Path, default=DEFAULT_EVAL)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    ov = _load(args.overrides_json)
    ev = _load(args.eval_json)
    overrides = ov.get("overrides") if ov else []
    n_ov = len(overrides) if isinstance(overrides, list) else 0
    policy = ov.get("policy") if isinstance(ov, dict) else {}
    signed = bool(policy.get("human_signoff_completed")) if isinstance(policy, dict) else False

    blockers: list[str] = []
    if n_ov == 0:
        blockers.append("overrides_empty_run_bootstrap_or_fill_fixture")
    if not signed:
        blockers.append("human_signoff_completed_false")

    ev_status = ev.get("status") if ev else None
    ev_n = (ev.get("summary") or {}).get("n_non_synthetic") if ev else None

    ready = len(blockers) == 0
    doc = {
        "schema": "logos_hardset_era_gold_signoff_readiness_v1",
        "ready_for_human_margin_report": ready,
        "n_overrides": n_ov,
        "human_signoff_completed": signed,
        "eval_status": ev_status,
        "eval_n": ev_n,
        "blockers": blockers,
        "ms_citation_allowed": False,
        "allowed_ms_metric": "historical_text_blind_4_3pct_only",
        "fixture_path": "docs/final/artifacts/fixtures/logos_chronology_hardset_era_gold_overrides_v1.json",
        "commands_after_signoff": [
            "py scripts/build_logos_hardset_news_era_gold_v2_v1.py",
            "powershell -File scripts/Run-LogosChronologyHardsetParallel_v1.ps1",
        ],
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ready": ready, "blockers": blockers, "n_overrides": n_ov}, ensure_ascii=False))
    return 0 if ready else 2


if __name__ == "__main__":
    raise SystemExit(main())
