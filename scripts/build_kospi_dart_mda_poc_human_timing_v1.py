#!/usr/bin/env python3
"""Gate B human timing sheet — template for commander trials (non-blocking).

Target: manual DART cross-check vs PoC citation-click verify >= 20% time saved.

Reproduce:
  py scripts/build_kospi_dart_mda_poc_human_timing_v1.py
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
QUERIES = ROOT / "docs/final/fixtures/kospi_dart_mda_poc_queries_v1.json"
DEFAULT_OUT = ROOT / "reports/kospi_dart_mda_poc_human_timing_v1_latest.json"

# Three representative in-scope queries for timed trials (pricing §4 aligned).
TRIAL_QUERY_IDS = ("q01", "q05", "q11")


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_queries() -> dict[str, str]:
    doc = json.loads(QUERIES.read_text(encoding="utf-8-sig"))
    out: dict[str, str] = {}
    for item in doc.get("items") or []:
        if item.get("scope") == "in":
            out[str(item["id"])] = str(item.get("query_ko") or "")
    return out


def build_timing_sheet() -> dict[str, Any]:
    qmap = _load_queries()
    trials: list[dict[str, Any]] = []
    for idx, qid in enumerate(TRIAL_QUERY_IDS, start=1):
        trials.append(
            {
                "trial_id": idx,
                "query_id": qid,
                "query_ko": qmap.get(qid, ""),
                "manual_sec": None,
                "poc_click_verify_sec": None,
                "savings_ratio": None,
                "notes": "",
            }
        )
    return {
        "schema": "kospi_dart_mda_poc_human_timing_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "send_gate": "HOLD",
        "status": "awaiting_commander_trials",
        "target_savings_ratio_min": 0.20,
        "method_ko": (
            "동일 질의 3회: (A) 원문 MD&A 수동 대조 stopwatch vs "
            "(B) PoC 답변 [Ref: DART-MDNA-Pxxx] 클릭·원문 점프 stopwatch. "
            "savings_ratio = (manual - poc) / manual."
        ),
        "live_corpus_option": {
            "path": "reports/kospi_dart_mda_corpus_live_v1_latest.json",
            "synthesis_cmd": (
                "py scripts/synthesize_kospi_dart_mda_answer_v1.py "
                "--query \"<질의>\" --corpus reports/kospi_dart_mda_corpus_live_v1_latest.json"
            ),
            "note_ko": "fixture(q01/q05/q11) 또는 live corpus 동일 질의로 측정 가능",
        },
        "record_cmd": (
            "py scripts/record_kospi_dart_mda_poc_human_timing_v1.py "
            "--trial-id <1|2|3> --manual-sec <초> --poc-sec <초>"
        ),
        "trials": trials,
        "aggregate": {
            "mean_savings_ratio": None,
            "gate_b_pass": None,
        },
        "reproduce": "py scripts/build_kospi_dart_mda_poc_human_timing_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()
    doc = build_timing_sheet()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    mirror = ROOT / "reports/kospi_dart_mda_poc_human_timing_v1.json"
    mirror.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "artifact": str(args.out), "status": doc["status"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
