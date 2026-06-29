#!/usr/bin/env python3
"""Phase A: verify arXiv IDs cited in research LIT_REVIEW / MERGED markdown files."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT_DIR = ROOT / "docs" / "final" / "artifacts"
ATOM_NS = "{http://www.w3.org/2005/Atom}"
ARXIV_ID_RE = re.compile(
    r"(?:arxiv:/abs/|arxiv:)?(\d{4}\.\d{4,5})\b",
    re.IGNORECASE,
)
DEFAULT_MIN_PASS_RATE = 0.85
DEFAULT_MIN_TOTAL_IDS = 0
DEFAULT_ARXIV_BATCH_SIZE = 8
DEFAULT_ARXIV_MAX_RETRIES = 3
DEFAULT_ARXIV_RETRY_SLEEP = 1.5
DEFAULT_GLOBS = ("*_LIT_REVIEW_*.md", "*_MERGED_*.md")


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _posix_source_path(source_path: Path) -> str:
    try:
        return source_path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return source_path.resolve().as_posix()


def quote_hash_arxiv(arxiv_id: str) -> str:
    digest = hashlib.sha256(f"arxiv:{arxiv_id}".encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


def is_valid_arxiv_id_form(arxiv_id: str) -> bool:
    m = re.fullmatch(r"(\d{2})(\d{2})\.(\d{4,5})", arxiv_id)
    if not m:
        return False
    yy, mm, _ = int(m.group(1)), int(m.group(2)), m.group(3)
    if mm < 1 or mm > 12:
        return False
    if yy < 7 or yy > 99:
        return False
    return True


def extract_arxiv_ids(text: str) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for match in ARXIV_ID_RE.finditer(text):
        aid = match.group(1)
        if aid in seen:
            continue
        seen.add(aid)
        ordered.append(aid)
    return ordered


def _normalize_arxiv_id(raw_id: str) -> str:
    aid = raw_id.rstrip("/").split("/abs/")[-1] if "/abs/" in raw_id else raw_id.strip()
    aid = re.sub(r"v\d+$", "", aid, flags=re.IGNORECASE)
    return aid


def _parse_arxiv_atom(xml_bytes: bytes) -> dict[str, str]:
    root = ET.fromstring(xml_bytes)
    out: dict[str, str] = {}
    for entry in root.findall(f"{ATOM_NS}entry"):
        raw_id = entry.findtext(f"{ATOM_NS}id") or ""
        aid = _normalize_arxiv_id(raw_id)
        if not aid:
            continue
        title = (entry.findtext(f"{ATOM_NS}title") or "").strip().replace("\n", " ")
        out[aid] = title
    return out


def fetch_arxiv_metadata_batch(
    arxiv_ids: list[str],
    *,
    timeout: float = 20.0,
) -> dict[str, dict[str, Any]]:
    if not arxiv_ids:
        return {}
    url = (
        "http://export.arxiv.org/api/query?id_list="
        + ",".join(arxiv_ids)
        + f"&max_results={len(arxiv_ids)}"
    )
    req = urllib.request.Request(url, headers={"User-Agent": "mkm-research-citation-lock/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            xml_bytes = resp.read()
    except (urllib.error.URLError, TimeoutError) as exc:
        return {
            aid: {"status": "fetch_error", "error": str(exc), "title": None}
            for aid in arxiv_ids
        }
    titles = _parse_arxiv_atom(xml_bytes)
    results: dict[str, dict[str, Any]] = {}
    for aid in arxiv_ids:
        if aid in titles:
            results[aid] = {"status": "verified", "title": titles[aid], "error": None}
        else:
            results[aid] = {"status": "not_found", "title": None, "error": "absent_in_arxiv_api"}
    return results


def _is_retryable_fetch_error(error: str | None) -> bool:
    text = str(error or "").lower()
    return "429" in text or "503" in text or "timeout" in text


def fetch_arxiv_metadata_resilient(
    arxiv_ids: list[str],
    *,
    batch_size: int = DEFAULT_ARXIV_BATCH_SIZE,
    timeout: float = 20.0,
    max_retries: int = DEFAULT_ARXIV_MAX_RETRIES,
    retry_base_sleep: float = DEFAULT_ARXIV_RETRY_SLEEP,
) -> dict[str, dict[str, Any]]:
    """Fetch arXiv metadata in small batches with retry/backoff on rate limits."""
    if not arxiv_ids:
        return {}
    results: dict[str, dict[str, Any]] = {}
    for i in range(0, len(arxiv_ids), batch_size):
        chunk = arxiv_ids[i : i + batch_size]
        pending = list(chunk)
        for attempt in range(max_retries):
            batch_result = fetch_arxiv_metadata_batch(pending, timeout=timeout)
            retry_ids: list[str] = []
            for aid in pending:
                meta = batch_result.get(aid) or {
                    "status": "fetch_error",
                    "title": None,
                    "error": "missing_batch_result",
                }
                if meta.get("status") == "fetch_error" and _is_retryable_fetch_error(
                    str(meta.get("error") or "")
                ):
                    retry_ids.append(aid)
                else:
                    results[aid] = meta
            if not retry_ids:
                break
            pending = retry_ids
            if attempt + 1 < max_retries:
                time.sleep(retry_base_sleep * (2**attempt))
        for aid in pending:
            if aid not in results:
                results[aid] = {
                    "status": "fetch_error",
                    "title": None,
                    "error": "retry_exhausted",
                }
    return results


def resolve_input_paths(input_arg: Path, globs: tuple[str, ...]) -> list[Path]:
    if input_arg.is_file():
        return [input_arg.resolve()]
    if input_arg.is_dir():
        found: list[Path] = []
        seen: set[Path] = set()
        for pattern in globs:
            for candidate in sorted(input_arg.glob(pattern)):
                resolved = candidate.resolve()
                if resolved.is_file() and resolved not in seen:
                    seen.add(resolved)
                    found.append(resolved)
        return found
    raise FileNotFoundError(f"input not found: {input_arg}")


def build_lock_doc(
    *,
    source_path: Path,
    arxiv_ids: list[str],
    mode: str,
    min_pass_rate: float,
    min_total_ids: int,
    verify_results: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    entries: list[dict[str, Any]] = []
    verified = 0
    not_found = 0
    invalid_format = 0
    format_only = 0
    fetch_error = 0

    for aid in arxiv_ids:
        qh = quote_hash_arxiv(aid)
        if mode == "offline":
            if is_valid_arxiv_id_form(aid):
                status = "format_only"
                format_only += 1
            else:
                status = "invalid_format"
                invalid_format += 1
            entries.append(
                {
                    "arxiv_id": aid,
                    "quote_hash": qh,
                    "status": status,
                    "title": None,
                }
            )
            continue

        meta = verify_results.get(aid) or {"status": "not_found", "title": None, "error": "missing"}
        status = str(meta.get("status") or "not_found")
        if status == "verified":
            verified += 1
        elif status == "not_found":
            not_found += 1
        elif status == "fetch_error":
            fetch_error += 1
        elif status == "invalid_format":
            invalid_format += 1
        entries.append(
            {
                "arxiv_id": aid,
                "quote_hash": qh,
                "status": status,
                "title": meta.get("title"),
                "error": meta.get("error"),
            }
        )

    total = len(arxiv_ids)
    if mode == "offline":
        ok_count = format_only
        pass_rate = (ok_count / total) if total else (0.0 if min_total_ids > 0 else 1.0)
    else:
        ok_count = verified
        pass_rate = (ok_count / total) if total else (0.0 if min_total_ids > 0 else 1.0)

    ids_ok = total >= min_total_ids
    rate_ok = pass_rate >= min_pass_rate if total else min_total_ids == 0
    gate_ok = ids_ok and rate_ok
    vacuous_pass = total == 0 and min_total_ids == 0

    return {
        "schema": "research_lit_review_citation_lock_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc_now(),
        "source_path": _posix_source_path(source_path),
        "mode": mode,
        "min_pass_rate": min_pass_rate,
        "min_total_ids": min_total_ids,
        "citation_pass_rate": round(pass_rate, 4),
        "gate_ok": gate_ok,
        "vacuous_pass": vacuous_pass,
        "research_only": True,
        "track_b_only": True,
        "promotion_to_a_track_allowed": False,
        "policy": "Phase A: arXiv ID existence via export.arxiv.org; offline=format-only",
        "entries": entries,
        "stats": {
            "total_ids": total,
            "verified": verified,
            "format_only": format_only,
            "not_found": not_found,
            "invalid_format": invalid_format,
            "fetch_error": fetch_error,
            "vacuous_pass": vacuous_pass,
            "min_total_ids": min_total_ids,
        },
    }


def output_path_for(source_path: Path, out_dir: Path) -> Path:
    stem = source_path.stem
    return out_dir / f"{stem}_citation_lock_latest.json"


def check_file(
    source_path: Path,
    *,
    mode: str,
    min_pass_rate: float,
    min_total_ids: int,
    out_dir: Path,
    write_out: bool,
    batch_size: int = DEFAULT_ARXIV_BATCH_SIZE,
) -> dict[str, Any]:
    text = source_path.read_text(encoding="utf-8", errors="replace")
    arxiv_ids = extract_arxiv_ids(text)
    verify_results: dict[str, dict[str, Any]] = {}
    if mode == "online" and arxiv_ids:
        verify_results = fetch_arxiv_metadata_resilient(arxiv_ids, batch_size=batch_size)

    doc = build_lock_doc(
        source_path=source_path,
        arxiv_ids=arxiv_ids,
        mode=mode,
        min_pass_rate=min_pass_rate,
        min_total_ids=min_total_ids,
        verify_results=verify_results,
    )
    out_path = output_path_for(source_path, out_dir)
    doc["out_path"] = str(out_path.relative_to(ROOT)).replace("\\", "/")
    if write_out:
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return doc


def main() -> int:
    parser = argparse.ArgumentParser(description="Research LIT_REVIEW arXiv citation lock v1 (Phase A)")
    parser.add_argument(
        "--input",
        type=Path,
        default=ROOT / "tests" / "fixtures" / "research_lit_review_citation_lock_minimal_v1.md",
        help="Markdown file or directory (default: minimal fixture)",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=DEFAULT_OUT_DIR,
        help="Directory for *_citation_lock_latest.json artifacts",
    )
    parser.add_argument(
        "--glob",
        action="append",
        dest="globs",
        help=f"Glob when --input is dir (default: {DEFAULT_GLOBS})",
    )
    parser.add_argument("--offline", action="store_true", help="Format-only; no arXiv API calls")
    parser.add_argument(
        "--min-pass-rate",
        type=float,
        default=DEFAULT_MIN_PASS_RATE,
        help=f"Gate threshold (default {DEFAULT_MIN_PASS_RATE})",
    )
    parser.add_argument(
        "--min-total-ids",
        type=int,
        default=DEFAULT_MIN_TOTAL_IDS,
        help="Fail gate when extracted arXiv ID count is below this (0=allow vacuous pass)",
    )
    parser.add_argument(
        "--arxiv-batch-size",
        type=int,
        default=DEFAULT_ARXIV_BATCH_SIZE,
        help=f"Online arXiv API batch size (default {DEFAULT_ARXIV_BATCH_SIZE})",
    )
    parser.add_argument("--no-write", action="store_true", help="Skip writing artifact JSON")
    parser.add_argument("--stdout-only", action="store_true", help="Print summary JSON only")
    args = parser.parse_args()

    globs = tuple(args.globs) if args.globs else DEFAULT_GLOBS
    mode = "offline" if args.offline else "online"

    try:
        paths = resolve_input_paths(args.input.resolve(), globs)
    except FileNotFoundError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2

    if not paths:
        print(json.dumps({"ok": False, "error": "no matching markdown files"}, ensure_ascii=False), file=sys.stderr)
        return 2

    results: list[dict[str, Any]] = []
    all_ok = True
    for path in paths:
        doc = check_file(
            path,
            mode=mode,
            min_pass_rate=args.min_pass_rate,
            min_total_ids=args.min_total_ids,
            out_dir=args.out_dir.resolve(),
            write_out=not args.no_write,
            batch_size=args.arxiv_batch_size,
        )
        results.append(
            {
                "source_path": doc["source_path"],
                "out_path": doc["out_path"],
                "citation_pass_rate": doc["citation_pass_rate"],
                "gate_ok": doc["gate_ok"],
                "total_ids": doc["stats"]["total_ids"],
                "vacuous_pass": doc.get("vacuous_pass", False),
            }
        )
        if not doc["gate_ok"]:
            all_ok = False

    summary = {
        "schema": "research_lit_review_citation_lock_run_v1",
        "generated_at_utc": _utc_now(),
        "mode": mode,
        "min_pass_rate": args.min_pass_rate,
        "min_total_ids": args.min_total_ids,
        "ok": all_ok,
        "files": results,
    }
    print(json.dumps(summary, ensure_ascii=False))
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
