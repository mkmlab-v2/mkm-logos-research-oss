#!/usr/bin/env python3
"""Recommended MERGED/LIT_REVIEW SSOT gate chain: Phase A + B + router + Ollama handoff."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "docs" / "research" / "NEXT_GEN_HYBRID_AI_MKM_MERGED_LIT_REVIEW_2026-06-20.md"
DEFAULT_QUERY = "next gen hybrid AI memory edge cloud routing"
DEFAULT_OUT = ROOT / "reports" / "mkm_merged_lit_review_gate_chain_v1_latest.json"
CITATION_LOCK = ROOT / "scripts" / "check_research_lit_review_citation_lock_v1.py"
DOI_LOCK = ROOT / "scripts" / "check_research_lit_review_doi_lock_v1.py"
PMID_LOCK = ROOT / "scripts" / "check_research_lit_review_pmid_lock_v1.py"
FACT_SUPPORT = ROOT / "scripts" / "check_research_lit_review_fact_support_v1.py"
ROUTER_INDEX = ROOT / "scripts" / "build_mkm_deep_research_router_index_v1.py"
ROUTER_SHALLOW = ROOT / "scripts" / "build_mkm_research_router_to_shallow_v1.py"
DIGESTION_CHAIN = ROOT / "scripts" / "run_mkm_digestion_engine_chain_v1.py"
DEFAULT_MIN_TOTAL_IDS = 1
DEFAULT_MIN_TOTAL_CLAIMS = 1
DEFAULT_MIN_TOTAL_DOIS = 1
DEFAULT_MIN_TOTAL_PMIDS = 1


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _log(msg: str) -> None:
    print(msg, file=sys.stderr, flush=True)


def _posix_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def _run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="MERGED SSOT gate chain (recommended)")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--query", default=DEFAULT_QUERY)
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--min-pass-rate", type=float, default=0.85)
    parser.add_argument(
        "--min-total-ids",
        type=int,
        default=DEFAULT_MIN_TOTAL_IDS,
        help="Fail citation_lock when extracted arXiv ID count is below this (P0-1 vacuous pass block)",
    )
    parser.add_argument(
        "--min-total-claims",
        type=int,
        default=DEFAULT_MIN_TOTAL_CLAIMS,
        help="Fail fact_support when claim count is below this (P0-1 vacuous pass block)",
    )
    parser.add_argument(
        "--min-total-dois",
        type=int,
        default=DEFAULT_MIN_TOTAL_DOIS,
        help="Fail doi_lock when extracted DOI count is below this (only when DOIs present)",
    )
    parser.add_argument(
        "--skip-doi-lock",
        action="store_true",
        help="Skip Crossref DOI lock (default: run when DOIs are present in source)",
    )
    parser.add_argument(
        "--min-total-pmids",
        type=int,
        default=DEFAULT_MIN_TOTAL_PMIDS,
        help="Fail pmid_lock when extracted PMID count is below this (only when PMIDs present)",
    )
    parser.add_argument(
        "--skip-pmid-lock",
        action="store_true",
        help="Skip PubMed PMID lock (default: run when PMIDs are present in source)",
    )
    parser.add_argument("--skip-handoff", action="store_true")
    parser.add_argument(
        "--include-digestion",
        action="store_true",
        help="After citation/support PASS, dispatch digestion engine (default false for backward compat)",
    )
    parser.add_argument("--digestion-offline", action="store_true", help="Pass --offline to digestion chain")
    parser.add_argument(
        "--arxiv-batch-size",
        type=int,
        default=8,
        help="Forward to citation/support locks: online arXiv batch size",
    )
    parser.add_argument(
        "--arxiv-timeout",
        type=float,
        default=20.0,
        help="Forward to citation/support locks: online arXiv timeout seconds",
    )
    parser.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    md_path = args.input.resolve()
    if not md_path.is_file():
        print(json.dumps({"ok": False, "error": f"missing input: {md_path}"}, ensure_ascii=False))
        return 2

    steps: dict[str, Any] = {}

    _log("merged gate: step 1/6 citation_lock (Phase A arXiv)")
    lock_cmd = [
        sys.executable,
        str(CITATION_LOCK),
        "--input",
        str(md_path),
        "--min-pass-rate",
        str(args.min_pass_rate),
        "--min-total-ids",
        str(args.min_total_ids),
        "--arxiv-batch-size",
        str(args.arxiv_batch_size),
        "--arxiv-timeout",
        str(args.arxiv_timeout),
    ]
    if args.offline:
        lock_cmd.append("--offline")
    lock_proc = _run(lock_cmd)
    steps["citation_lock"] = {"exit_code": lock_proc.returncode, "stdout": lock_proc.stdout.strip()}
    if lock_proc.returncode != 0:
        print(json.dumps({"ok": False, "step": "citation_lock", "steps": steps}, ensure_ascii=False))
        return lock_proc.returncode
    citation_doc = json.loads(lock_proc.stdout.strip())

    doi_doc: dict[str, Any] | None = None
    if not args.skip_doi_lock:
        if str(ROOT) not in sys.path:
            sys.path.insert(0, str(ROOT))
        from scripts.check_research_lit_review_doi_lock_v1 import extract_dois

        dois_in_source = extract_dois(md_path.read_text(encoding="utf-8", errors="replace"))
        if not dois_in_source:
            _log("merged gate: step 1b/6 doi_lock skipped (no DOIs in source)")
            doi_doc = {
                "ok": True,
                "skipped": True,
                "reason": "no_dois_in_source",
                "total_dois": 0,
                "min_total_dois": args.min_total_dois,
            }
            steps["doi_lock"] = {"exit_code": 0, "skipped": True, "stdout": json.dumps(doi_doc, ensure_ascii=False)}
        else:
            _log("merged gate: step 1b/6 doi_lock (Crossref PoC)")
            doi_cmd = [
                sys.executable,
                str(DOI_LOCK),
                "--input",
                str(md_path),
                "--min-pass-rate",
                str(args.min_pass_rate),
                "--min-total-dois",
                str(args.min_total_dois),
                "--no-write",
            ]
            if args.offline:
                doi_cmd.append("--offline")
            doi_proc = _run(doi_cmd)
            steps["doi_lock"] = {"exit_code": doi_proc.returncode, "stdout": doi_proc.stdout.strip()}
            if doi_proc.returncode != 0:
                print(json.dumps({"ok": False, "step": "doi_lock", "steps": steps}, ensure_ascii=False))
                return doi_proc.returncode
            doi_doc = json.loads(doi_proc.stdout.strip())

    pmid_doc: dict[str, Any] | None = None
    if not args.skip_pmid_lock:
        if str(ROOT) not in sys.path:
            sys.path.insert(0, str(ROOT))
        from scripts.check_research_lit_review_pmid_lock_v1 import extract_pmids

        pmids_in_source = extract_pmids(md_path.read_text(encoding="utf-8", errors="replace"))
        if not pmids_in_source:
            _log("merged gate: step 1c/6 pmid_lock skipped (no PMIDs in source)")
            pmid_doc = {
                "ok": True,
                "skipped": True,
                "reason": "no_pmids_in_source",
                "total_pmids": 0,
                "min_total_pmids": args.min_total_pmids,
            }
            steps["pmid_lock"] = {"exit_code": 0, "skipped": True, "stdout": json.dumps(pmid_doc, ensure_ascii=False)}
        else:
            _log("merged gate: step 1c/6 pmid_lock (PubMed PoC)")
            pmid_cmd = [
                sys.executable,
                str(PMID_LOCK),
                "--input",
                str(md_path),
                "--min-pass-rate",
                str(args.min_pass_rate),
                "--min-total-pmids",
                str(args.min_total_pmids),
                "--no-write",
            ]
            if args.offline:
                pmid_cmd.append("--offline")
            pmid_proc = _run(pmid_cmd)
            steps["pmid_lock"] = {"exit_code": pmid_proc.returncode, "stdout": pmid_proc.stdout.strip()}
            if pmid_proc.returncode != 0:
                print(json.dumps({"ok": False, "step": "pmid_lock", "steps": steps}, ensure_ascii=False))
                return pmid_proc.returncode
            pmid_doc = json.loads(pmid_proc.stdout.strip())

    _log("merged gate: step 2/6 fact_support (Phase B)")
    fact_cmd = [
        sys.executable,
        str(FACT_SUPPORT),
        "--input",
        str(md_path),
        "--min-pass-rate",
        str(args.min_pass_rate),
        "--min-total-claims",
        str(args.min_total_claims),
        "--arxiv-batch-size",
        str(args.arxiv_batch_size),
        "--arxiv-timeout",
        str(args.arxiv_timeout),
    ]
    if args.offline:
        fact_cmd.append("--offline")
    fact_proc = _run(fact_cmd)
    steps["fact_support"] = {"exit_code": fact_proc.returncode, "stdout": fact_proc.stdout.strip()}
    if fact_proc.returncode != 0:
        print(json.dumps({"ok": False, "step": "fact_support", "steps": steps}, ensure_ascii=False))
        return fact_proc.returncode
    fact_doc = json.loads(fact_proc.stdout.strip())

    _log("merged gate: step 3/6 router_index")
    router_proc = _run(
        [
            sys.executable,
            str(ROUTER_INDEX),
            "--input-md",
            str(md_path),
            "--query",
            args.query,
        ]
    )
    steps["router_index"] = {"exit_code": router_proc.returncode, "stdout": router_proc.stdout.strip()}
    if router_proc.returncode != 0:
        print(json.dumps({"ok": False, "step": "router_index", "steps": steps}, ensure_ascii=False))
        return router_proc.returncode
    router_doc = json.loads(router_proc.stdout.strip())
    router_path = ROOT / str(router_doc["out_path"])

    shallow_doc: dict[str, Any] | None = None
    if not args.skip_handoff:
        _log("merged gate: step 4/6 router_to_shallow + handoff")
        shallow_proc = _run(
            [
                sys.executable,
                str(ROUTER_SHALLOW),
                "--input",
                str(router_path),
                "--with-handoff",
            ]
        )
        steps["router_to_shallow"] = {
            "exit_code": shallow_proc.returncode,
            "stdout": shallow_proc.stdout.strip(),
        }
        if shallow_proc.returncode != 0:
            print(json.dumps({"ok": False, "step": "router_to_shallow", "steps": steps}, ensure_ascii=False))
            return shallow_proc.returncode
        shallow_doc = json.loads(shallow_proc.stdout.strip())

    digestion_doc: dict[str, Any] | None = None
    if args.include_digestion:
        if str(ROOT) not in sys.path:
            sys.path.insert(0, str(ROOT))
        from scripts.mkm_dr2_digest_wiring_v1 import digest_eligible_from_merged

        md_text = md_path.read_text(encoding="utf-8", errors="replace")
        eligible, reason = digest_eligible_from_merged(md_text)
        if not eligible:
            _log(f"merged gate: digestion SKIPPED ({reason})")
            digestion_doc = {
                "ok": True,
                "skipped": True,
                "reason": reason,
                "digest_eligible": False,
                "authoritative_ssot_auto_apply": "LOCKED",
            }
            steps["digestion"] = {"exit_code": 0, "skipped": True, "stdout": json.dumps(digestion_doc, ensure_ascii=False)}
        else:
            _log("merged gate: digestion dispatch (post support PASS)")
            dig_cmd = [
                sys.executable,
                str(DIGESTION_CHAIN),
                "--input",
                str(md_path),
            ]
            if args.offline or args.digestion_offline:
                dig_cmd.append("--offline")
            dig_proc = _run(dig_cmd)
            steps["digestion"] = {
                "exit_code": dig_proc.returncode,
                "stdout": dig_proc.stdout.strip(),
                "stderr": dig_proc.stderr.strip() if dig_proc.returncode != 0 else "",
            }
            if dig_proc.returncode != 0:
                print(json.dumps({"ok": False, "step": "digestion", "steps": steps}, ensure_ascii=False))
                return dig_proc.returncode
            try:
                digestion_doc = json.loads(dig_proc.stdout.strip())
            except json.JSONDecodeError:
                digestion_doc = {"ok": True, "raw_stdout": dig_proc.stdout.strip()}
            digestion_doc = dict(digestion_doc or {})
            digestion_doc["digest_eligible"] = True
            digestion_doc["authoritative_ssot_auto_apply"] = "LOCKED"
            digestion_doc["note"] = "gate PASS ≠ SSOT truth promotion"

    doc = {
        "schema": "mkm_merged_lit_review_gate_chain_v1",
        "generated_at_utc": _utc_now(),
        "ok": True,
        "input_md": _posix_path(md_path),
        "query": args.query,
        "min_total_ids": args.min_total_ids,
        "min_total_claims": args.min_total_claims,
        "min_total_dois": args.min_total_dois,
        "min_total_pmids": args.min_total_pmids,
        "doi_lock_enabled": not args.skip_doi_lock,
        "pmid_lock_enabled": not args.skip_pmid_lock,
        "citation_lock": citation_doc,
        "doi_lock": doi_doc,
        "pmid_lock": pmid_doc,
        "fact_support": fact_doc,
        "router_index": router_doc,
        "router_to_shallow": shallow_doc,
        "digestion": digestion_doc,
        "include_digestion": bool(args.include_digestion),
        "authoritative_ssot_auto_apply": "LOCKED",
        "research_only": True,
        "send_gate": "HOLD",
        "reproduce": f'py scripts/run_mkm_merged_lit_review_gate_chain_v1.py --input "{_posix_path(md_path)}"',
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out_json": _posix_path(args.out_json), "input_md": doc["input_md"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
