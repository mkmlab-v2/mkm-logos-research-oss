#!/usr/bin/env python3
"""Phase B (FACT-lite): claim→URL abstract support judge for research LIT_REVIEW."""

from __future__ import annotations

import argparse
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
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.research_lit_review_relation_qualifier_gate_v1 import evaluate_relation_qualifier_gate
DEFAULT_OUT_DIR = ROOT / "docs" / "final" / "artifacts"
ATOM_NS = "{http://www.w3.org/2005/Atom}"
DEFAULT_MIN_PASS_RATE = 0.85
DEFAULT_MIN_TOTAL_CLAIMS = 0
DEFAULT_ARXIV_BATCH_SIZE = 8
DEFAULT_ARXIV_MAX_RETRIES = 3
DEFAULT_ARXIV_RETRY_SLEEP = 1.5
TITLE_OVERLAP_MIN = 0.25


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _posix_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def normalize_text(text: str) -> str:
    text = re.sub(r"[^\w\s]", " ", text.lower())
    return re.sub(r"\s+", " ", text).strip()


def title_supported(catalog_title: str, api_title: str) -> bool:
    a = normalize_text(catalog_title)
    b = normalize_text(api_title)
    if not a or not b:
        return False
    if b.startswith(a) or a.startswith(b):
        return True
    return a in b or b in a


def abstract_overlap(catalog_title: str, abstract: str, *, min_ratio: float = TITLE_OVERLAP_MIN) -> bool:
    tokens = [t for t in normalize_text(catalog_title).split() if len(t) > 3]
    if not tokens:
        tokens = [t for t in re.split(r"[\s\-]+", normalize_text(catalog_title)) if len(t) >= 2]
    if not tokens:
        return False
    abs_text = normalize_text(abstract)
    hits = sum(1 for token in tokens if token in abs_text)
    return (hits / len(tokens)) >= min_ratio


def catalog_label_supported_detailed(
    catalog_title: str, api_title: str, abstract: str
) -> dict[str, Any]:
    if title_supported(catalog_title, api_title):
        return {
            "supported": True,
            "judge_reason": "title_match",
            "lexical_candidate_pass": None,
            "gate": None,
        }
    title_norm = normalize_text(api_title)
    label_tokens = [t for t in re.split(r"[\s\-]+", normalize_text(catalog_title)) if len(t) >= 2]
    if label_tokens:
        hits = sum(1 for token in label_tokens if token in title_norm)
        if hits >= max(1, (len(label_tokens) + 1) // 2):
            return {
                "supported": True,
                "judge_reason": "label_token_in_title",
                "lexical_candidate_pass": None,
                "gate": None,
            }
    compact = normalize_text(catalog_title).replace(" ", "")
    if len(compact) >= 3 and compact in title_norm.replace(" ", ""):
        return {
            "supported": True,
            "judge_reason": "compact_label_in_title",
            "lexical_candidate_pass": None,
            "gate": None,
        }
    lexical_pass = abstract_overlap(catalog_title, abstract, min_ratio=0.15)
    if not lexical_pass:
        return {
            "supported": False,
            "judge_reason": "title_and_abstract_mismatch",
            "lexical_candidate_pass": False,
            "gate": None,
        }
    gate = evaluate_relation_qualifier_gate(catalog_title, abstract)
    gate["lexical_candidate_pass"] = True
    if gate["final_gate_state"] == "COMPATIBLE":
        return {
            "supported": True,
            "judge_reason": "abstract_token_overlap",
            "lexical_candidate_pass": True,
            "gate": gate,
        }
    return {
        "supported": False,
        "judge_reason": gate["final_reason_code"],
        "lexical_candidate_pass": True,
        "gate": gate,
    }


def catalog_label_supported(catalog_title: str, api_title: str, abstract: str) -> tuple[bool, str]:
    detail = catalog_label_supported_detailed(catalog_title, api_title, abstract)
    return bool(detail["supported"]), str(detail["judge_reason"])


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def extract_claims_from_jsonl(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    claims: list[dict[str, Any]] = []
    for row in rows:
        aid = row.get("arxiv_id")
        if not isinstance(aid, str) or not aid:
            continue
        title = str(row.get("title") or "").strip()
        claims.append(
            {
                "claim_id": f"arxiv:{aid}",
                "claim": title,
                "url": str(row.get("url") or f"https://arxiv.org/abs/{aid}"),
                "arxiv_id": aid,
                "lane": row.get("lane"),
            }
        )
    return claims


def extract_claims_from_markdown(text: str) -> list[dict[str, Any]]:
    claims: list[dict[str, Any]] = []
    seen: set[str] = set()

    def _append(aid: str, claim: str) -> None:
        if aid in seen:
            return
        seen.add(aid)
        claims.append(
            {
                "claim_id": f"arxiv:{aid}",
                "claim": claim or aid,
                "url": f"https://arxiv.org/abs/{aid}",
                "arxiv_id": aid,
                "lane": "catalog",
            }
        )

    for line in text.splitlines():
        if not line.startswith("|") or line.startswith("|---"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) < 2:
            continue
        if cells[0].lower() in {"id", "arxiv id"} or cells[0] == "----":
            continue
        if len(cells) == 2 and re.fullmatch(r"\d{4}\.\d{4,5}", cells[0]):
            _append(cells[0], cells[1])
            continue
        if not cells[0].isdigit():
            continue
        aid = None
        claim = None
        for i, cell in enumerate(cells):
            if re.fullmatch(r"\d{4}\.\d{4,5}", cell):
                aid = cell
                if i + 2 < len(cells) and cells[i + 1] in {
                    "concept",
                    "implementation",
                    "repo",
                }:
                    claim = cells[i + 2]
                elif i + 1 < len(cells):
                    claim = cells[i + 1]
                else:
                    claim = aid
                break
        if aid:
            _append(aid, claim or aid)

    inline_re = re.compile(r"(?:arxiv:/abs/|arxiv:)?(\d{4}\.\d{4,5})\b", re.IGNORECASE)
    for match in inline_re.finditer(text):
        _append(match.group(1), match.group(1))

    return claims


def _normalize_arxiv_id(raw_id: str) -> str:
    aid = raw_id.rstrip("/").split("/abs/")[-1] if "/abs/" in raw_id else raw_id.strip()
    return re.sub(r"v\d+$", "", aid, flags=re.IGNORECASE)


def _parse_arxiv_atom(xml_bytes: bytes) -> dict[str, dict[str, str]]:
    root = ET.fromstring(xml_bytes)
    out: dict[str, dict[str, str]] = {}
    for entry in root.findall(f"{ATOM_NS}entry"):
        raw_id = entry.findtext(f"{ATOM_NS}id") or ""
        aid = _normalize_arxiv_id(raw_id)
        if not aid:
            continue
        title = (entry.findtext(f"{ATOM_NS}title") or "").strip().replace("\n", " ")
        summary = (entry.findtext(f"{ATOM_NS}summary") or "").strip().replace("\n", " ")
        out[aid] = {"title": title, "abstract": summary}
    return out


def fetch_arxiv_records_batch(arxiv_ids: list[str], *, timeout: float = 20.0) -> dict[str, dict[str, Any]]:
    if not arxiv_ids:
        return {}
    url = (
        "http://export.arxiv.org/api/query?id_list="
        + ",".join(arxiv_ids)
        + f"&max_results={len(arxiv_ids)}"
    )
    req = urllib.request.Request(url, headers={"User-Agent": "mkm-research-fact-support/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            records = _parse_arxiv_atom(resp.read())
    except (urllib.error.URLError, TimeoutError) as exc:
        return {
            aid: {"status": "fetch_error", "title": None, "abstract": None, "error": str(exc)}
            for aid in arxiv_ids
        }
    results: dict[str, dict[str, Any]] = {}
    for aid in arxiv_ids:
        rec = records.get(aid)
        if rec:
            results[aid] = {
                "status": "fetched",
                "title": rec["title"],
                "abstract": rec["abstract"],
                "error": None,
            }
        else:
            results[aid] = {
                "status": "not_found",
                "title": None,
                "abstract": None,
                "error": "absent_in_arxiv_api",
            }
    return results


def _is_retryable_fetch_error(error: str | None) -> bool:
    text = str(error or "").lower()
    return "429" in text or "503" in text or "timeout" in text


def fetch_arxiv_records_resilient(
    arxiv_ids: list[str],
    *,
    batch_size: int = DEFAULT_ARXIV_BATCH_SIZE,
    timeout: float = 20.0,
    max_retries: int = DEFAULT_ARXIV_MAX_RETRIES,
    retry_base_sleep: float = DEFAULT_ARXIV_RETRY_SLEEP,
) -> dict[str, dict[str, Any]]:
    if not arxiv_ids:
        return {}
    results: dict[str, dict[str, Any]] = {}
    for i in range(0, len(arxiv_ids), batch_size):
        chunk = arxiv_ids[i : i + batch_size]
        pending = list(chunk)
        for attempt in range(max_retries):
            batch_result = fetch_arxiv_records_batch(pending, timeout=timeout)
            retry_ids: list[str] = []
            for aid in pending:
                meta = batch_result.get(aid) or {
                    "status": "fetch_error",
                    "title": None,
                    "abstract": None,
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
                    "abstract": None,
                    "error": "retry_exhausted",
                }
    return results


def judge_claim(
    claim: dict[str, Any],
    *,
    mode: str,
    records: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    aid = str(claim["arxiv_id"])
    catalog_title = str(claim["claim"])
    if mode == "offline":
        supported = bool(normalize_text(catalog_title)) and bool(
            re.fullmatch(r"\d{4}\.\d{4,5}", aid)
        )
        return {
            **claim,
            "support_status": "supported" if supported else "not_supported",
            "judge_mode": "offline_stub",
            "judge_reason": "offline: non-empty claim + valid arxiv id",
            "api_title": None,
        }

    rec = records.get(aid) or {"status": "not_found", "title": None, "abstract": None}
    if rec.get("status") != "fetched":
        return {
            **claim,
            "support_status": "not_supported",
            "judge_mode": "online",
            "judge_reason": rec.get("error") or rec.get("status"),
            "api_title": rec.get("title"),
        }
    api_title = str(rec.get("title") or "")
    abstract = str(rec.get("abstract") or "")
    detail = catalog_label_supported_detailed(catalog_title, api_title, abstract)
    supported = bool(detail["supported"])
    reason = str(detail["judge_reason"])
    out = {
        **claim,
        "support_status": "supported" if supported else "not_supported",
        "judge_mode": "online",
        "judge_reason": reason,
        "api_title": api_title,
    }
    if detail.get("gate"):
        out["relation_qualifier_gate"] = detail["gate"]
    return out


def build_fact_doc(
    *,
    source_path: Path | None,
    claims: list[dict[str, Any]],
    judged: list[dict[str, Any]],
    mode: str,
    min_pass_rate: float,
    min_total_claims: int,
) -> dict[str, Any]:
    supported = sum(1 for row in judged if row["support_status"] == "supported")
    total = len(judged)
    if total:
        pass_rate = supported / total
    else:
        pass_rate = 0.0 if min_total_claims > 0 else 1.0
    ids_ok = total >= min_total_claims
    rate_ok = pass_rate >= min_pass_rate if total else min_total_claims == 0
    gate_ok = ids_ok and rate_ok
    vacuous_pass = total == 0 and min_total_claims == 0
    return {
        "schema": "research_lit_review_fact_support_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc_now(),
        "source_path": _posix_path(source_path) if source_path else None,
        "mode": mode,
        "min_pass_rate": min_pass_rate,
        "min_total_claims": min_total_claims,
        "support_pass_rate": round(pass_rate, 4),
        "gate_ok": gate_ok,
        "vacuous_pass": vacuous_pass,
        "research_only": True,
        "track_b_only": True,
        "promotion_to_a_track_allowed": False,
        "policy": "Phase B FACT-lite: title/abstract support vs arXiv metadata; offline=stub",
        "entries": judged,
        "stats": {
            "total_claims": total,
            "supported": supported,
            "not_supported": total - supported,
            "vacuous_pass": vacuous_pass,
            "min_total_claims": min_total_claims,
        },
    }


def output_path_for(source_stem: str, out_dir: Path) -> Path:
    return out_dir / f"{source_stem}_fact_support_latest.json"


def check_fact_support(
    *,
    lit_md: Path | None,
    jsonl: Path | None,
    mode: str,
    min_pass_rate: float,
    min_total_claims: int,
    out_dir: Path,
    write_out: bool,
    batch_size: int = DEFAULT_ARXIV_BATCH_SIZE,
    timeout: float = 20.0,
) -> dict[str, Any]:
    claims: list[dict[str, Any]] = []
    if jsonl and jsonl.is_file():
        claims = extract_claims_from_jsonl(load_jsonl(jsonl))
    elif lit_md and lit_md.is_file():
        claims = extract_claims_from_markdown(lit_md.read_text(encoding="utf-8", errors="replace"))
    else:
        raise FileNotFoundError("need --input md and/or --jsonl")

    records: dict[str, dict[str, Any]] = {}
    if mode == "online" and claims:
        ids = sorted({str(c["arxiv_id"]) for c in claims})
        records = fetch_arxiv_records_resilient(ids, batch_size=batch_size, timeout=timeout)

    judged = [judge_claim(c, mode=mode, records=records) for c in claims]
    stem = (lit_md or jsonl).stem  # type: ignore[union-attr]
    doc = build_fact_doc(
        source_path=lit_md,
        claims=claims,
        judged=judged,
        mode=mode,
        min_pass_rate=min_pass_rate,
        min_total_claims=min_total_claims,
    )
    out_path = output_path_for(stem, out_dir)
    doc["out_path"] = _posix_path(out_path)
    if write_out:
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        jsonl_out = out_path.with_suffix(".jsonl")
        with jsonl_out.open("w", encoding="utf-8") as fh:
            for row in judged:
                fh.write(json.dumps(row, ensure_ascii=False) + "\n")
        doc["out_jsonl"] = _posix_path(jsonl_out)
    return doc


def main() -> int:
    parser = argparse.ArgumentParser(description="Research LIT_REVIEW FACT-lite support judge (Phase B)")
    parser.add_argument("--input", type=Path, default=None, help="LIT_REVIEW markdown")
    parser.add_argument("--jsonl", type=Path, default=None, help="Explore JSONL (preferred for full titles)")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--min-pass-rate", type=float, default=DEFAULT_MIN_PASS_RATE)
    parser.add_argument(
        "--min-total-claims",
        type=int,
        default=DEFAULT_MIN_TOTAL_CLAIMS,
        help="Fail gate when claim count is below this (0=allow vacuous pass)",
    )
    parser.add_argument(
        "--arxiv-batch-size",
        type=int,
        default=DEFAULT_ARXIV_BATCH_SIZE,
        help=f"Online arXiv API batch size (default {DEFAULT_ARXIV_BATCH_SIZE})",
    )
    parser.add_argument(
        "--arxiv-timeout",
        type=float,
        default=20.0,
        help="Online arXiv API per-request timeout seconds (default 20)",
    )
    parser.add_argument("--no-write", action="store_true")
    args = parser.parse_args()

    if not args.input and not args.jsonl:
        print(json.dumps({"ok": False, "error": "provide --input and/or --jsonl"}, ensure_ascii=False), file=sys.stderr)
        return 2

    mode = "offline" if args.offline else "online"
    try:
        doc = check_fact_support(
            lit_md=args.input.resolve() if args.input else None,
            jsonl=args.jsonl.resolve() if args.jsonl else None,
            mode=mode,
            min_pass_rate=args.min_pass_rate,
            min_total_claims=args.min_total_claims,
            out_dir=args.out_dir.resolve(),
            write_out=not args.no_write,
            batch_size=args.arxiv_batch_size,
            timeout=args.arxiv_timeout,
        )
    except FileNotFoundError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2

    summary = {
        "schema": "research_lit_review_fact_support_run_v1",
        "generated_at_utc": _utc_now(),
        "mode": mode,
        "min_pass_rate": args.min_pass_rate,
        "min_total_claims": args.min_total_claims,
        "ok": doc["gate_ok"],
        "support_pass_rate": doc["support_pass_rate"],
        "total_claims": doc["stats"]["total_claims"],
        "out_path": doc["out_path"],
    }
    print(json.dumps(summary, ensure_ascii=False))
    return 0 if doc["gate_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
