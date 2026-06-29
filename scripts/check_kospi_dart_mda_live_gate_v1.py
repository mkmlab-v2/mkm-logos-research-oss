#!/usr/bin/env python3
"""Observational live corpus gate — separate from fixture Gate A (non-blocking).

Evaluates live smoke artifact against kospi_dart_mda_live_smoke_queries_v1.json:
  - in_mda: citation lock hit expected
  - honest_miss: no_paragraph_hit expected (no hallucination)

Exit 0: skipped (no live corpus) OR gate pass OR awaiting live ingest.
Exit 1: live corpus present but expectations failed.

Reproduce:
  py scripts/check_kospi_dart_mda_live_gate_v1.py
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.kospi_dart_mda_poc_lib_v1 import build_deterministic_answer  # noqa: E402

QUERIES = ROOT / "docs/final/fixtures/kospi_dart_mda_live_smoke_queries_v1.json"
CORPUS_LIVE = ROOT / "reports/kospi_dart_mda_corpus_live_v1_latest.json"
SMOKE = ROOT / "reports/kospi_dart_mda_poc_live_smoke_v1_latest.json"
DEFAULT_OUT = ROOT / "reports/kospi_dart_mda_live_gate_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def evaluate(
    *,
    corpus_path: Path = CORPUS_LIVE,
    queries_path: Path = QUERIES,
) -> dict[str, Any]:
    if not corpus_path.is_file():
        return {
            "ok": True,
            "skipped": True,
            "reason": "missing_live_corpus",
            "schema": "kospi_dart_mda_live_gate_v1",
        }

    corpus = json.loads(corpus_path.read_text(encoding="utf-8-sig"))
    qdoc = json.loads(queries_path.read_text(encoding="utf-8-sig"))
    items = qdoc.get("items") or []

    results: list[dict[str, Any]] = []
    in_mda_ok = 0
    in_mda_total = 0
    honest_ok = 0
    honest_total = 0

    for item in items:
        qid = str(item.get("id") or "")
        query = str(item.get("query_ko") or "")
        expect = str(item.get("expect") or "in_mda")
        ans = build_deterministic_answer(query, corpus)
        got_hit = bool(ans.get("ok"))
        citation_valid = bool(ans.get("citation_valid")) if got_hit else False
        no_hit = not got_hit and str(ans.get("error") or "") == "no_paragraph_hit"

        if expect == "in_mda":
            in_mda_total += 1
            passed = got_hit and citation_valid
            if passed:
                in_mda_ok += 1
        elif expect == "honest_miss":
            honest_total += 1
            passed = no_hit
            if passed:
                honest_ok += 1
        else:
            passed = got_hit and citation_valid

        results.append(
            {
                "id": qid,
                "expect": expect,
                "query_ko": query,
                "passed": passed,
                "got_hit": got_hit,
                "citation_valid": citation_valid,
                "no_paragraph_hit": no_hit,
                "paragraph_ids": ans.get("allowed_paragraph_ids"),
            }
        )

    in_mda_rate = (in_mda_ok / in_mda_total) if in_mda_total else 1.0
    honest_rate = (honest_ok / honest_total) if honest_total else 1.0
    gate_pass = in_mda_total > 0 and in_mda_ok == in_mda_total and honest_ok == honest_total

    return {
        "ok": gate_pass,
        "skipped": False,
        "schema": "kospi_dart_mda_live_gate_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "send_gate": "HOLD",
        "corpus_artifact": str(corpus_path.relative_to(ROOT)).replace("\\", "/"),
        "corpus_paragraphs": len(corpus.get("paragraphs") or []),
        "queries_fixture": str(queries_path.relative_to(ROOT)).replace("\\", "/"),
        "live_gate": {
            "in_mda_pass": f"{in_mda_ok}/{in_mda_total}",
            "in_mda_pass_rate": round(in_mda_rate, 4),
            "honest_miss_pass": f"{honest_ok}/{honest_total}",
            "honest_miss_rate": round(honest_rate, 4),
            "gate_pass": gate_pass,
        },
        "results": results,
        "note_ko": "관측용 live gate — fixture Gate A와 분리. B2B 덱 승격 조건 아님.",
        "reproduce": "py scripts/check_kospi_dart_mda_live_gate_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--corpus", type=Path, default=CORPUS_LIVE)
    ap.add_argument("--queries", type=Path, default=QUERIES)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    doc = evaluate(corpus_path=args.corpus, queries_path=args.queries)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    mirror = ROOT / "docs/final/artifacts/kospi_dart_mda_live_gate_v1_latest.json"
    mirror.parent.mkdir(parents=True, exist_ok=True)
    mirror.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc.get("ok"), "skipped": doc.get("skipped"), "artifact": str(args.out)}, ensure_ascii=False))
    if doc.get("skipped"):
        return 0
    return 0 if doc.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
