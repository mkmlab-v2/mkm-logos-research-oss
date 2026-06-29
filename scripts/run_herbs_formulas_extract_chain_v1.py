#!/usr/bin/env python3
"""Herbs/formulas extract chain: structured markdown → schema-valid JSON → optional DOI/PMID locks."""

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

DEFAULT_OUT = ROOT / "reports" / "herbs_formulas_extract_chain_v1_latest.json"
BUILD = ROOT / "scripts" / "build_herbs_formulas_extract_v1.py"
DOSAGE_VALIDATE = ROOT / "scripts" / "validate_dosage_v1.py"
DOI_LOCK = ROOT / "scripts" / "check_research_lit_review_doi_lock_v1.py"
PMID_LOCK = ROOT / "scripts" / "check_research_lit_review_pmid_lock_v1.py"


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
    parser = argparse.ArgumentParser(description="Herbs/formulas extract + optional citation locks")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--extract-out", type=Path, default=None)
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--skip-doi-lock", action="store_true")
    parser.add_argument("--skip-pmid-lock", action="store_true")
    parser.add_argument("--no-write-locks", action="store_true", help="Pass --no-write to DOI/PMID lock subprocesses")
    args = parser.parse_args()

    md_path = args.input.resolve()
    if not md_path.is_file():
        print(json.dumps({"ok": False, "error": f"missing input: {md_path}"}, ensure_ascii=False))
        return 2

    extract_out = (
        args.extract_out.resolve()
        if args.extract_out
        else ROOT / "docs/final/artifacts" / f"{md_path.stem}_herbs_formulas_extract_latest.json"
    )
    steps: dict[str, Any] = {}

    _log("herbs extract chain: step 1/4 build + schema validate")
    build_cmd = [
        sys.executable,
        str(BUILD),
        "--input",
        str(md_path),
        "--out",
        str(extract_out),
        "--strict",
    ]
    build_proc = _run(build_cmd)
    steps["extract"] = {"exit_code": build_proc.returncode, "stdout": build_proc.stdout.strip()}
    if build_proc.returncode != 0:
        steps["extract"]["stderr"] = build_proc.stderr.strip()
        print(json.dumps({"ok": False, "step": "extract", "steps": steps}, ensure_ascii=False))
        return build_proc.returncode

    extract_doc = json.loads(extract_out.read_text(encoding="utf-8"))

    _log("herbs extract chain: step 2/4 dosage boundary validate")
    dosage_cmd = [
        sys.executable,
        str(DOSAGE_VALIDATE),
        "--input",
        str(extract_out),
    ]
    dosage_proc = _run(dosage_cmd)
    steps["dosage_validate"] = {
        "exit_code": dosage_proc.returncode,
        "stdout": dosage_proc.stdout.strip(),
    }
    if dosage_proc.returncode != 0:
        steps["dosage_validate"]["stderr"] = dosage_proc.stderr.strip()
        print(json.dumps({"ok": False, "step": "dosage_validate", "steps": steps}, ensure_ascii=False))
        return dosage_proc.returncode

    text = md_path.read_text(encoding="utf-8", errors="replace")

    doi_doc: dict[str, Any] | None = None
    if not args.skip_doi_lock:
        from scripts.check_research_lit_review_doi_lock_v1 import extract_dois

        if not extract_dois(text):
            doi_doc = {"skipped": True, "reason": "no_dois_in_source"}
            steps["doi_lock"] = {"exit_code": 0, "skipped": True}
        else:
            _log("herbs extract chain: step 3/4 doi_lock")
            doi_cmd = [
                sys.executable,
                str(DOI_LOCK),
                "--input",
                str(md_path),
                "--min-total-dois",
                "1",
            ]
            if args.offline:
                doi_cmd.append("--offline")
            if args.no_write_locks:
                doi_cmd.append("--no-write")
            doi_proc = _run(doi_cmd)
            steps["doi_lock"] = {"exit_code": doi_proc.returncode, "stdout": doi_proc.stdout.strip()}
            if doi_proc.returncode != 0:
                print(json.dumps({"ok": False, "step": "doi_lock", "steps": steps}, ensure_ascii=False))
                return doi_proc.returncode
            doi_doc = json.loads(doi_proc.stdout.strip())

    pmid_doc: dict[str, Any] | None = None
    if not args.skip_pmid_lock:
        from scripts.check_research_lit_review_pmid_lock_v1 import extract_pmids

        if not extract_pmids(text):
            pmid_doc = {"skipped": True, "reason": "no_pmids_in_source"}
            steps["pmid_lock"] = {"exit_code": 0, "skipped": True}
        else:
            _log("herbs extract chain: step 4/4 pmid_lock")
            pmid_cmd = [
                sys.executable,
                str(PMID_LOCK),
                "--input",
                str(md_path),
                "--min-total-pmids",
                "1",
            ]
            if args.offline:
                pmid_cmd.append("--offline")
            if args.no_write_locks:
                pmid_cmd.append("--no-write")
            pmid_proc = _run(pmid_cmd)
            steps["pmid_lock"] = {"exit_code": pmid_proc.returncode, "stdout": pmid_proc.stdout.strip()}
            if pmid_proc.returncode != 0:
                print(json.dumps({"ok": False, "step": "pmid_lock", "steps": steps}, ensure_ascii=False))
                return pmid_proc.returncode
            pmid_doc = json.loads(pmid_proc.stdout.strip())

    chain_doc = {
        "schema": "herbs_formulas_extract_chain_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc_now(),
        "ok": True,
        "offline": bool(args.offline),
        "input": _posix_path(md_path),
        "extract_path": _posix_path(extract_out),
        "research_only": True,
        "send_gate": "HOLD",
        "expert_review_required": True,
        "doi_lock_enabled": not args.skip_doi_lock,
        "pmid_lock_enabled": not args.skip_pmid_lock,
        "extract": extract_doc,
        "doi_lock": doi_doc,
        "pmid_lock": pmid_doc,
        "steps": steps,
        "reproduce": (
            f'py scripts/run_herbs_formulas_extract_chain_v1.py --input "{_posix_path(md_path)}"'
            + (" --offline" if args.offline else "")
        ),
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(chain_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out_path": _posix_path(args.out_json)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
