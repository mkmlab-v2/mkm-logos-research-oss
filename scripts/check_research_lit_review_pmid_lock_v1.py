#!/usr/bin/env python3
"""Phase A-PoC: verify PMIDs cited in research LIT_REVIEW via PubMed E-utilities (B-track only)."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT_DIR = ROOT / "docs" / "final" / "artifacts"
PMID_PATTERNS = (
    re.compile(r"PMID:\s*(\d{7,8})\b", re.IGNORECASE),
    re.compile(r"pubmed\.ncbi\.nlm\.nih\.gov/(\d{7,8})\b", re.IGNORECASE),
)
DEFAULT_MIN_PASS_RATE = 0.85
DEFAULT_MIN_TOTAL_PMIDS = 0
DEFAULT_PUBMED_MAX_RETRIES = 3
DEFAULT_PUBMED_RETRY_SLEEP = 1.5
DEFAULT_TOOL = "mkm-research-pmid-lock"
DEFAULT_EMAIL = "support@mkmlife.com"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _posix_source_path(source_path: Path) -> str:
    try:
        return source_path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return source_path.resolve().as_posix()


def quote_hash_pmid(pmid: str) -> str:
    digest = hashlib.sha256(f"pmid:{pmid}".encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


def normalize_pmid(raw: str) -> str:
    return raw.strip()


def is_valid_pmid_form(pmid: str) -> bool:
    return bool(re.fullmatch(r"\d{7,8}", pmid))


def extract_pmids(text: str) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []

    def _append(pmid: str) -> None:
        if pmid in seen:
            return
        seen.add(pmid)
        ordered.append(pmid)

    pmid_table = False
    for line in text.splitlines():
        if line.startswith("|"):
            cells = [c.strip() for c in line.strip("|").split("|")]
            if len(cells) >= 2:
                if cells[0].lower() in {"pmid", "pmid id"}:
                    pmid_table = True
                    continue
                if pmid_table and re.fullmatch(r"\d{7,8}", cells[0]):
                    _append(cells[0])
                    continue
        for pattern in PMID_PATTERNS:
            for match in pattern.finditer(line):
                _append(match.group(1))
    return ordered


def _pubmed_tool_email() -> tuple[str, str]:
    tool = os.environ.get("MKM_PUBMED_TOOL", DEFAULT_TOOL)
    email = os.environ.get("MKM_PUBMED_EMAIL", DEFAULT_EMAIL)
    return tool, email


def fetch_pubmed_esummary_batch(
    pmids: list[str],
    *,
    timeout: float = 20.0,
) -> dict[str, dict[str, Any]]:
    if not pmids:
        return {}
    tool, email = _pubmed_tool_email()
    query = urllib.parse.urlencode(
        {
            "db": "pubmed",
            "id": ",".join(pmids),
            "retmode": "json",
            "tool": tool,
            "email": email,
        }
    )
    url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?{query}"
    req = urllib.request.Request(url, headers={"User-Agent": f"{tool}/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        if exc.code == 429:
            return {
                pmid: {"status": "fetch_error", "title": None, "error": "http_429"}
                for pmid in pmids
            }
        return {
            pmid: {"status": "fetch_error", "title": None, "error": f"http_{exc.code}"}
            for pmid in pmids
        }
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        return {
            pmid: {"status": "fetch_error", "title": None, "error": str(exc)} for pmid in pmids
        }

    result = payload.get("result") if isinstance(payload, dict) else None
    if not isinstance(result, dict):
        return {
            pmid: {"status": "fetch_error", "title": None, "error": "invalid_pubmed_payload"}
            for pmid in pmids
        }

    out: dict[str, dict[str, Any]] = {}
    for pmid in pmids:
        row = result.get(pmid)
        if not isinstance(row, dict):
            out[pmid] = {"status": "not_found", "title": None, "error": "absent_in_pubmed_result"}
            continue
        title = str(row.get("title") or "").strip() or None
        if row.get("error"):
            out[pmid] = {"status": "not_found", "title": title, "error": str(row.get("error"))}
        else:
            out[pmid] = {"status": "verified", "title": title, "error": None}
    return out


def fetch_pubmed_resilient(
    pmids: list[str],
    *,
    max_retries: int = DEFAULT_PUBMED_MAX_RETRIES,
    retry_sleep: float = DEFAULT_PUBMED_RETRY_SLEEP,
) -> dict[str, dict[str, Any]]:
    results: dict[str, dict[str, Any]] = {}
    batch_size = 20
    for i in range(0, len(pmids), batch_size):
        chunk = pmids[i : i + batch_size]
        last: dict[str, dict[str, Any]] = {}
        for attempt in range(max_retries):
            last = fetch_pubmed_esummary_batch(chunk)
            if all(row.get("status") == "verified" for row in last.values()):
                break
            if not any(row.get("error") == "http_429" for row in last.values()):
                break
            if attempt + 1 < max_retries:
                time.sleep(retry_sleep * (attempt + 1))
        results.update(last)
    return results


def build_lock_doc(
    *,
    source_path: Path,
    pmids: list[str],
    mode: str,
    min_pass_rate: float,
    min_total_pmids: int,
    verify_results: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    entries: list[dict[str, Any]] = []
    verified = format_only = not_found = invalid_format = fetch_error = 0

    for pmid in pmids:
        qh = quote_hash_pmid(pmid)
        if not is_valid_pmid_form(pmid):
            invalid_format += 1
            entries.append(
                {
                    "pmid": pmid,
                    "quote_hash": qh,
                    "status": "invalid_format",
                    "title": None,
                    "error": "invalid_pmid_form",
                }
            )
            continue

        if mode == "offline":
            format_only += 1
            entries.append(
                {
                    "pmid": pmid,
                    "quote_hash": qh,
                    "status": "format_only",
                    "title": None,
                    "error": None,
                }
            )
            continue

        meta = verify_results.get(pmid) or {"status": "fetch_error", "title": None, "error": "missing"}
        status = str(meta.get("status") or "fetch_error")
        if status == "verified":
            verified += 1
        elif status == "not_found":
            not_found += 1
        else:
            fetch_error += 1
            status = "fetch_error"
        entries.append(
            {
                "pmid": pmid,
                "quote_hash": qh,
                "status": status,
                "title": meta.get("title"),
                "error": meta.get("error"),
            }
        )

    total = len(pmids)
    if mode == "offline":
        ok_count = format_only
        pass_rate = (ok_count / total) if total else (0.0 if min_total_pmids > 0 else 1.0)
    else:
        ok_count = verified
        pass_rate = (ok_count / total) if total else (0.0 if min_total_pmids > 0 else 1.0)

    ids_ok = total >= min_total_pmids
    rate_ok = pass_rate >= min_pass_rate if total else min_total_pmids == 0
    gate_ok = ids_ok and rate_ok
    vacuous_pass = total == 0 and min_total_pmids == 0

    return {
        "schema": "research_lit_review_pmid_lock_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc_now(),
        "source_path": _posix_source_path(source_path),
        "mode": mode,
        "min_pass_rate": min_pass_rate,
        "min_total_pmids": min_total_pmids,
        "pmid_pass_rate": round(pass_rate, 4),
        "gate_ok": gate_ok,
        "vacuous_pass": vacuous_pass,
        "research_only": True,
        "track_b_only": True,
        "promotion_to_a_track_allowed": False,
        "policy": "PoC: PubMed esummary existence check; offline=format-only; not clinical citation proof",
        "entries": entries,
        "stats": {
            "total_pmids": total,
            "verified": verified,
            "format_only": format_only,
            "not_found": not_found,
            "invalid_format": invalid_format,
            "fetch_error": fetch_error,
            "vacuous_pass": vacuous_pass,
            "min_total_pmids": min_total_pmids,
        },
    }


def check_file(
    source_path: Path,
    *,
    mode: str,
    min_pass_rate: float,
    min_total_pmids: int,
    out_dir: Path,
    write_out: bool,
) -> dict[str, Any]:
    text = source_path.read_text(encoding="utf-8", errors="replace")
    pmids = extract_pmids(text)
    verify_results: dict[str, dict[str, Any]] = {}
    if mode == "online" and pmids:
        verify_results = fetch_pubmed_resilient(pmids)

    doc = build_lock_doc(
        source_path=source_path,
        pmids=pmids,
        mode=mode,
        min_pass_rate=min_pass_rate,
        min_total_pmids=min_total_pmids,
        verify_results=verify_results,
    )
    out_path = out_dir / f"{source_path.stem}_pmid_lock_latest.json"
    doc["out_path"] = _posix_source_path(out_path)
    if write_out:
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return doc


def main() -> int:
    parser = argparse.ArgumentParser(description="Research LIT_REVIEW PMID lock (PubMed PoC)")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--min-pass-rate", type=float, default=DEFAULT_MIN_PASS_RATE)
    parser.add_argument(
        "--min-total-pmids",
        type=int,
        default=DEFAULT_MIN_TOTAL_PMIDS,
        help="Fail gate when extracted PMID count is below this (0=allow vacuous pass)",
    )
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--no-write", action="store_true")
    args = parser.parse_args()

    source_path = args.input.resolve()
    if not source_path.is_file():
        print(json.dumps({"ok": False, "error": f"missing input: {source_path}"}, ensure_ascii=False))
        return 2

    mode = "offline" if args.offline else "online"
    doc = check_file(
        source_path,
        mode=mode,
        min_pass_rate=args.min_pass_rate,
        min_total_pmids=args.min_total_pmids,
        out_dir=args.out_dir.resolve(),
        write_out=not args.no_write,
    )
    summary = {
        "schema": "research_lit_review_pmid_lock_run_v1",
        "generated_at_utc": _utc_now(),
        "mode": mode,
        "min_pass_rate": args.min_pass_rate,
        "min_total_pmids": args.min_total_pmids,
        "ok": doc["gate_ok"],
        "pmid_pass_rate": doc["pmid_pass_rate"],
        "total_pmids": doc["stats"]["total_pmids"],
        "vacuous_pass": doc.get("vacuous_pass", False),
        "out_path": doc.get("out_path"),
        "source_path": doc["source_path"],
    }
    print(json.dumps(summary, ensure_ascii=False))
    return 0 if doc["gate_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
