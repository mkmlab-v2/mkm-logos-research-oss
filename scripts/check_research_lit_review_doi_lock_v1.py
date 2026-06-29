#!/usr/bin/env python3
"""Phase A-PoC: verify DOIs cited in research LIT_REVIEW via Crossref (B-track only)."""

from __future__ import annotations

import argparse
import hashlib
import json
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
DOI_CORE_RE = re.compile(
    r"(?:doi:\s*|https?://(?:dx\.)?doi\.org/)?(10\.\d{4,9}/[^\s\])>\"',]+)",
    re.IGNORECASE,
)
DEFAULT_MIN_PASS_RATE = 0.85
DEFAULT_MIN_TOTAL_DOIS = 0
DEFAULT_CROSSREF_MAX_RETRIES = 3
DEFAULT_CROSSREF_RETRY_SLEEP = 1.5
DEFAULT_USER_AGENT = "mkm-research-doi-lock/1.0 (https://mkm12.local/btrack; mailto:support@mkmlife.com)"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _posix_source_path(source_path: Path) -> str:
    try:
        return source_path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return source_path.resolve().as_posix()


def quote_hash_doi(doi: str) -> str:
    digest = hashlib.sha256(f"doi:{doi.lower()}".encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


def normalize_doi(raw: str) -> str:
    doi = raw.strip().rstrip(".,;)")
    doi = re.sub(r"^https?://(?:dx\.)?doi\.org/", "", doi, flags=re.IGNORECASE)
    doi = re.sub(r"^doi:\s*", "", doi, flags=re.IGNORECASE)
    return doi.lower()


def is_valid_doi_form(doi: str) -> bool:
    return bool(re.fullmatch(r"10\.\d{4,9}/[^\s]+", doi, flags=re.IGNORECASE))


def extract_dois(text: str) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for match in DOI_CORE_RE.finditer(text):
        doi = normalize_doi(match.group(1))
        if doi in seen:
            continue
        seen.add(doi)
        ordered.append(doi)
    return ordered


def fetch_crossref_work(
    doi: str,
    *,
    timeout: float = 20.0,
    user_agent: str = DEFAULT_USER_AGENT,
) -> dict[str, Any]:
    encoded = urllib.parse.quote(doi, safe="/")
    url = f"https://api.crossref.org/works/{encoded}"
    req = urllib.request.Request(url, headers={"User-Agent": user_agent})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return {"status": "not_found", "title": None, "error": "http_404"}
        if exc.code == 429:
            return {"status": "fetch_error", "title": None, "error": "http_429"}
        return {"status": "fetch_error", "title": None, "error": f"http_{exc.code}"}
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        return {"status": "fetch_error", "title": None, "error": str(exc)}

    message = payload.get("message") if isinstance(payload, dict) else None
    if not isinstance(message, dict):
        return {"status": "fetch_error", "title": None, "error": "invalid_crossref_payload"}

    title_parts = message.get("title") or []
    title = title_parts[0] if title_parts else None
    status = str(message.get("status") or "ok")
    if status.lower() in {"ok", "valid"}:
        return {"status": "verified", "title": title, "error": None}
    return {"status": "not_found", "title": title, "error": f"crossref_status_{status}"}


def fetch_crossref_resilient(
    dois: list[str],
    *,
    max_retries: int = DEFAULT_CROSSREF_MAX_RETRIES,
    retry_sleep: float = DEFAULT_CROSSREF_RETRY_SLEEP,
) -> dict[str, dict[str, Any]]:
    results: dict[str, dict[str, Any]] = {}
    for doi in dois:
        last: dict[str, Any] = {"status": "fetch_error", "title": None, "error": "not_attempted"}
        for attempt in range(max_retries):
            last = fetch_crossref_work(doi)
            if last.get("status") == "verified":
                break
            if last.get("error") != "http_429":
                break
            if attempt + 1 < max_retries:
                time.sleep(retry_sleep * (attempt + 1))
        results[doi] = last
    return results


def build_lock_doc(
    *,
    source_path: Path,
    dois: list[str],
    mode: str,
    min_pass_rate: float,
    min_total_dois: int,
    verify_results: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    entries: list[dict[str, Any]] = []
    verified = format_only = not_found = invalid_format = fetch_error = 0

    for doi in dois:
        qh = quote_hash_doi(doi)
        if not is_valid_doi_form(doi):
            invalid_format += 1
            entries.append(
                {
                    "doi": doi,
                    "quote_hash": qh,
                    "status": "invalid_format",
                    "title": None,
                    "error": "invalid_doi_form",
                }
            )
            continue

        if mode == "offline":
            format_only += 1
            entries.append(
                {
                    "doi": doi,
                    "quote_hash": qh,
                    "status": "format_only",
                    "title": None,
                    "error": None,
                }
            )
            continue

        meta = verify_results.get(doi) or {"status": "fetch_error", "title": None, "error": "missing"}
        status = str(meta.get("status") or "fetch_error")
        if status == "verified":
            verified += 1
        elif status == "not_found":
            not_found += 1
        elif status == "fetch_error":
            fetch_error += 1
        else:
            fetch_error += 1
            status = "fetch_error"
        entries.append(
            {
                "doi": doi,
                "quote_hash": qh,
                "status": status,
                "title": meta.get("title"),
                "error": meta.get("error"),
            }
        )

    total = len(dois)
    if mode == "offline":
        ok_count = format_only
        pass_rate = (ok_count / total) if total else (0.0 if min_total_dois > 0 else 1.0)
    else:
        ok_count = verified
        pass_rate = (ok_count / total) if total else (0.0 if min_total_dois > 0 else 1.0)

    ids_ok = total >= min_total_dois
    rate_ok = pass_rate >= min_pass_rate if total else min_total_dois == 0
    gate_ok = ids_ok and rate_ok
    vacuous_pass = total == 0 and min_total_dois == 0

    return {
        "schema": "research_lit_review_doi_lock_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc_now(),
        "source_path": _posix_source_path(source_path),
        "mode": mode,
        "min_pass_rate": min_pass_rate,
        "min_total_dois": min_total_dois,
        "doi_pass_rate": round(pass_rate, 4),
        "gate_ok": gate_ok,
        "vacuous_pass": vacuous_pass,
        "research_only": True,
        "track_b_only": True,
        "promotion_to_a_track_allowed": False,
        "policy": "PoC: Crossref /works existence check; offline=format-only; not clinical citation proof",
        "entries": entries,
        "stats": {
            "total_dois": total,
            "verified": verified,
            "format_only": format_only,
            "not_found": not_found,
            "invalid_format": invalid_format,
            "fetch_error": fetch_error,
            "vacuous_pass": vacuous_pass,
            "min_total_dois": min_total_dois,
        },
    }


def check_file(
    source_path: Path,
    *,
    mode: str,
    min_pass_rate: float,
    min_total_dois: int,
    out_dir: Path,
    write_out: bool,
) -> dict[str, Any]:
    text = source_path.read_text(encoding="utf-8", errors="replace")
    dois = extract_dois(text)
    verify_results: dict[str, dict[str, Any]] = {}
    if mode == "online" and dois:
        verify_results = fetch_crossref_resilient(dois)

    doc = build_lock_doc(
        source_path=source_path,
        dois=dois,
        mode=mode,
        min_pass_rate=min_pass_rate,
        min_total_dois=min_total_dois,
        verify_results=verify_results,
    )
    out_path = out_dir / f"{source_path.stem}_doi_lock_latest.json"
    doc["out_path"] = _posix_source_path(out_path)
    if write_out:
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return doc


def main() -> int:
    parser = argparse.ArgumentParser(description="Research LIT_REVIEW DOI lock (Crossref PoC)")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--min-pass-rate", type=float, default=DEFAULT_MIN_PASS_RATE)
    parser.add_argument(
        "--min-total-dois",
        type=int,
        default=DEFAULT_MIN_TOTAL_DOIS,
        help="Fail gate when extracted DOI count is below this (0=allow vacuous pass)",
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
        min_total_dois=args.min_total_dois,
        out_dir=args.out_dir.resolve(),
        write_out=not args.no_write,
    )
    summary = {
        "schema": "research_lit_review_doi_lock_run_v1",
        "generated_at_utc": _utc_now(),
        "mode": mode,
        "min_pass_rate": args.min_pass_rate,
        "min_total_dois": args.min_total_dois,
        "ok": doc["gate_ok"],
        "doi_pass_rate": doc["doi_pass_rate"],
        "total_dois": doc["stats"]["total_dois"],
        "vacuous_pass": doc.get("vacuous_pass", False),
        "out_path": doc.get("out_path"),
        "source_path": doc["source_path"],
    }
    print(json.dumps(summary, ensure_ascii=False))
    return 0 if doc["gate_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
