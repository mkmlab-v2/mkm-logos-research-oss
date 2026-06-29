#!/usr/bin/env python3
"""Shared live DART MD&A ingest + smoke runner for one corp."""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

RESOLVE = ROOT / "scripts/resolve_dart_corp_mda_rcept_no_v1.py"
INGEST = ROOT / "scripts/ingest_dart_mda_section_v1.py"
DEFAULT_QUERIES = ROOT / "docs/final/fixtures/kospi_dart_mda_live_smoke_queries_v1.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run_json(cmd: list[str]) -> tuple[int, dict[str, Any]]:
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, encoding="utf-8")
    doc: dict[str, Any] = {}
    if proc.stdout.strip():
        try:
            doc = json.loads(proc.stdout.strip().splitlines()[-1])
        except json.JSONDecodeError:
            doc = {"raw_stdout": proc.stdout[-500:]}
    if proc.returncode != 0 and not doc:
        doc = {"error": proc.stderr[-500:] or proc.stdout[-500:]}
    return proc.returncode, doc


def load_query_items(queries_path: Path) -> list[dict[str, Any]]:
    if not queries_path.is_file():
        return [
            {"id": "legacy01", "expect": "in_mda", "query_ko": "영업이익"},
            {"id": "legacy02", "expect": "honest_miss", "query_ko": "연구개발비"},
            {"id": "legacy03", "expect": "honest_miss", "query_ko": "배당"},
        ]
    doc = json.loads(queries_path.read_text(encoding="utf-8-sig"))
    return list(doc.get("items") or [])


def evaluate_corpus_queries(corpus: dict[str, Any], items: list[dict[str, Any]]) -> dict[str, Any]:
    from scripts.kospi_dart_mda_poc_lib_v1 import build_deterministic_answer  # noqa: WPS433

    synth_checks: list[dict[str, Any]] = []
    in_mda_ok = 0
    in_mda_total = 0
    honest_ok = 0
    honest_total = 0

    for item in items:
        q = str(item.get("query_ko") or "")
        expect = str(item.get("expect") or "in_mda")
        ans = build_deterministic_answer(q, corpus)
        got_hit = bool(ans.get("ok"))
        citation_valid = bool(ans.get("citation_valid")) if got_hit else None
        no_hit = not got_hit and str(ans.get("error") or "") == "no_paragraph_hit"

        if expect == "in_mda":
            in_mda_total += 1
            if got_hit and citation_valid:
                in_mda_ok += 1
        elif expect == "honest_miss":
            honest_total += 1
            if no_hit:
                honest_ok += 1

        synth_checks.append(
            {
                "id": item.get("id"),
                "expect": expect,
                "query": q,
                "ok": got_hit,
                "citation_valid": citation_valid,
                "no_paragraph_hit": no_hit,
                "expect_pass": (got_hit and citation_valid) if expect == "in_mda" else no_hit,
                "paragraph_ids": ans.get("allowed_paragraph_ids"),
            }
        )

    n_paras = len(corpus.get("paragraphs") or [])
    live_gate_pass = (
        n_paras >= 5
        and in_mda_total > 0
        and in_mda_ok == in_mda_total
        and honest_ok == honest_total
    )
    return {
        "corpus_paragraphs": n_paras,
        "live_smoke_queries": synth_checks,
        "live_gate": {
            "in_mda_pass": f"{in_mda_ok}/{in_mda_total}",
            "honest_miss_pass": f"{honest_ok}/{honest_total}",
            "gate_pass": live_gate_pass,
        },
        "live_smoke_pass": live_gate_pass,
    }


def run_corp_live_smoke(
    *,
    corp_code: str,
    corp_name_ko: str,
    slug: str,
    corpus_out: Path,
    queries_path: Path,
) -> dict[str, Any]:
    code, resolved = _run_json([PY, str(RESOLVE), "--corp-code", corp_code])
    if resolved.get("skipped"):
        return {
            "ok": True,
            "skipped": True,
            "reason": "missing_DART_API_KEY",
            "schema": "kospi_dart_mda_poc_live_smoke_v1",
            "slug": slug,
            "corp_code": corp_code,
        }
    if code != 0 or not resolved.get("ok"):
        return {
            "ok": False,
            "skipped": False,
            "schema": "kospi_dart_mda_poc_live_smoke_v1",
            "slug": slug,
            "corp_code": corp_code,
            "resolve": resolved,
        }

    rcept_no = str(resolved.get("rcept_no") or "")
    corp_name = str(resolved.get("corp_name") or corp_name_ko)
    ingest_cmd = [
        PY,
        str(INGEST),
        "--mode",
        "dart_api",
        "--rcept-no",
        rcept_no,
        "--corp-name-ko",
        corp_name,
        "--corp-code",
        corp_code,
        "--out",
        str(corpus_out),
    ]
    icode, ingest_summary = _run_json(ingest_cmd)
    if icode != 0:
        return {
            "ok": False,
            "skipped": False,
            "schema": "kospi_dart_mda_poc_live_smoke_v1",
            "slug": slug,
            "corp_code": corp_code,
            "resolve": resolved,
            "ingest": ingest_summary,
        }

    if not corpus_out.is_file():
        return {
            "ok": False,
            "error": "corpus_missing_after_ingest",
            "slug": slug,
            "corp_code": corp_code,
            "resolve": resolved,
        }

    corpus = json.loads(corpus_out.read_text(encoding="utf-8-sig"))
    items = load_query_items(queries_path)
    eval_doc = evaluate_corpus_queries(corpus, items)

    return {
        "ok": bool(eval_doc["live_smoke_pass"]),
        "skipped": False,
        "schema": "kospi_dart_mda_poc_live_smoke_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "send_gate": "HOLD",
        "slug": slug,
        "corp_code": corp_code,
        "corp_name_ko": corp_name,
        "resolve": {
            "rcept_no": rcept_no,
            "rcept_dt": resolved.get("rcept_dt"),
            "report_nm": resolved.get("report_nm"),
        },
        "corpus_artifact": str(corpus_out.relative_to(ROOT)).replace("\\", "/"),
        "queries_fixture": str(queries_path.relative_to(ROOT)).replace("\\", "/"),
        **eval_doc,
        "note_ko": "관측용 — fixture Gate A와 분리. honest_miss=MD&A 밖 질의는 미히트가 정상.",
    }
