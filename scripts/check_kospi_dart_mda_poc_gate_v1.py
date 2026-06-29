#!/usr/bin/env python3
"""Gate A mechanical check — KOSPI DART MD&A PoC (16-query fixture).

Writes docs/final/artifacts/kospi_dart_mda_poc_latest.json

Pass (exit 0):
  - orphan_paragraph_ref_rate == 0 on in-scope queries
  - scope_refusal_rate == 1 on out-of-scope queries
  - numeric_unverified_rate == 0 on in-scope answers

Gate B (human timing 20%) is NOT part of this exit code.

Reproduce:
  py scripts/check_kospi_dart_mda_poc_gate_v1.py
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
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.kospi_dart_mda_poc_lib_v1 import (  # noqa: E402
    build_deterministic_answer,
    is_scope_violation_query,
    scope_refusal_payload,
)

INGEST = ROOT / "scripts/ingest_dart_mda_section_v1.py"
QUERIES_FIXTURE = ROOT / "docs/final/fixtures/kospi_dart_mda_poc_queries_v1.json"
CORPUS_DEFAULT = ROOT / "docs/final/artifacts/kospi_dart_mda_corpus_v1_latest.json"
OUT_DEFAULT = ROOT / "docs/final/artifacts/kospi_dart_mda_poc_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def ensure_corpus(corpus_path: Path, *, skip_ingest: bool) -> dict[str, Any]:
    if not skip_ingest or not corpus_path.is_file():
        proc = subprocess.run(
            [sys.executable, str(INGEST), "--mode", "fixture", "--out", str(corpus_path)],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            raise RuntimeError(f"ingest_failed: {proc.stderr or proc.stdout}")
    return json.loads(corpus_path.read_text(encoding="utf-8-sig"))


def evaluate(corpus: dict[str, Any], queries_doc: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    items = queries_doc.get("items") or []
    checks: list[dict[str, Any]] = []
    errors: list[str] = []

    in_scope = [it for it in items if it.get("scope") == "in"]
    out_scope = [it for it in items if it.get("scope") == "out"]

    orphan_failures = 0
    numeric_failures = 0
    in_answered = 0

    for it in in_scope:
        qid = str(it.get("id") or "")
        query = str(it.get("query_ko") or "")
        if is_scope_violation_query(query):
            orphan_failures += 1
            checks.append({"id": f"{qid}_scope", "ok": False, "detail": "in_scope mis-tagged as violation"})
            errors.append(f"{qid}: in_scope query flagged violation")
            continue
        ans = build_deterministic_answer(query, corpus)
        ok = bool(ans.get("ok")) and ans.get("citation_valid") is True
        if ans.get("ok"):
            in_answered += 1
        if not ok:
            orphan_failures += 1
            if ans.get("numeric_check", {}).get("numeric_valid") is False:
                numeric_failures += 1
        checks.append(
            {
                "id": qid,
                "ok": ok,
                "detail": "citation_lock" if ok else json.dumps(
                    {
                        "citation_check": ans.get("citation_check"),
                        "numeric_check": ans.get("numeric_check"),
                        "error": ans.get("error"),
                    },
                    ensure_ascii=False,
                ),
            }
        )
        if not ok:
            errors.append(f"{qid}: citation/numeric gate failed")

    scope_refused = 0
    for it in out_scope:
        qid = str(it.get("id") or "")
        query = str(it.get("query_ko") or "")
        expected = str(it.get("expect_error_code") or "SCOPE_VIOLATION_HONEST_REFUSAL")
        refusal = scope_refusal_payload(query)
        ok = (
            refusal.get("error_code") == expected
            and refusal.get("canon_status") == "not_acquired"
            and is_scope_violation_query(query)
        )
        if ok:
            scope_refused += 1
        else:
            errors.append(f"{qid}: scope refusal failed")
        checks.append({"id": qid, "ok": ok, "detail": refusal.get("error_code")})

    n_in = len(in_scope) or 1
    n_out = len(out_scope) or 1
    orphan_rate = orphan_failures / n_in
    numeric_rate = numeric_failures / n_in
    refusal_rate = scope_refused / n_out

    gate_a = {
        "orphan_paragraph_ref_rate": round(orphan_rate, 4),
        "numeric_unverified_rate": round(numeric_rate, 4),
        "scope_refusal_rate": round(refusal_rate, 4),
        "n_in_scope": len(in_scope),
        "n_out_of_scope": len(out_scope),
        "n_in_scope_answered": in_answered,
    }

    mechanical_ok = orphan_rate == 0.0 and numeric_rate == 0.0 and refusal_rate == 1.0
    if not mechanical_ok:
        if orphan_rate != 0.0:
            errors.append(f"orphan_paragraph_ref_rate={orphan_rate}")
        if numeric_rate != 0.0:
            errors.append(f"numeric_unverified_rate={numeric_rate}")
        if refusal_rate != 1.0:
            errors.append(f"scope_refusal_rate={refusal_rate}")

    report = {
        "schema": "kospi_dart_mda_poc_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "send_gate": "HOLD",
        "hypothesis_tier": "B",
        "wires_to_scoring_core": False,
        "canon_status": corpus.get("canon_status", "fixture_only"),
        "ok": mechanical_ok,
        "corpus_artifact": _rel(CORPUS_DEFAULT),
        "queries_fixture": _rel(QUERIES_FIXTURE),
        "gate_a_mechanical": gate_a,
        "gate_b_human_timing": {
            "status": "awaiting_commander_trials",
            "artifact": "reports/kospi_dart_mda_poc_human_timing_v1_latest.json",
            "builder": "scripts/build_kospi_dart_mda_poc_human_timing_v1.py",
        },
        "checks": checks,
        "errors": errors,
        "reproduce": "py scripts/check_kospi_dart_mda_poc_gate_v1.py",
    }
    return mechanical_ok, report


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--corpus", type=Path, default=CORPUS_DEFAULT)
    ap.add_argument("--queries", type=Path, default=QUERIES_FIXTURE)
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    ap.add_argument("--skip-ingest", action="store_true")
    args = ap.parse_args()

    try:
        corpus = ensure_corpus(args.corpus, skip_ingest=args.skip_ingest)
        queries_doc = json.loads(args.queries.read_text(encoding="utf-8-sig"))
        ok, report = evaluate(corpus, queries_doc)
    except (RuntimeError, json.JSONDecodeError, OSError) as exc:
        report = {
            "schema": "kospi_dart_mda_poc_v1",
            "generated_at_utc": _utc(),
            "research_only": True,
            "send_gate": "HOLD",
            "ok": False,
            "error": str(exc),
            "reproduce": "py scripts/check_kospi_dart_mda_poc_gate_v1.py",
        }
        ok = False

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    mirror = ROOT / "reports/kospi_dart_mda_poc_latest.json"
    mirror.parent.mkdir(parents=True, exist_ok=True)
    mirror.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": ok, "artifact": _rel(args.out)}, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
