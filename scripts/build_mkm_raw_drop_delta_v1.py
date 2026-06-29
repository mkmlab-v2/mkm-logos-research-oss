#!/usr/bin/env python3
"""Extract structured delta from Tier-0 raw markdown drops (regex + optional Ollama hint).

Track B · research_only · send_gate HOLD · not a live DR agent replacement.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.build_mkm_deep_research_router_index_v1 import classify_research_plane  # noqa: E402
from scripts.check_research_lit_review_citation_lock_v1 import extract_arxiv_ids  # noqa: E402

DEFAULT_RAW_DIR = ROOT / "docs" / "research" / "raw"
DEFAULT_OUT_DIR = ROOT / "docs" / "final" / "artifacts"
DEFAULT_OLLAMA_HOST = "http://127.0.0.1:11434"
DEFAULT_OLLAMA_MODEL = "gemma4:e2b"

OVERCLAIM_RULES: tuple[tuple[re.Pattern[str], str, str], ...] = (
    (re.compile(r"242\s*[×x]", re.I), "DROP", "242x multiplier KPI"),
    (re.compile(r"\bDMF\b", re.I), "DROP", "DMF product claim"),
    (re.compile(r"oracle\s+gap\s*[=:]?\s*0(?:\.0)?\b", re.I), "NARROW", "oracle gap zero"),
    (re.compile(r"NSGA[- ]?II.*shipp", re.I), "HYPO", "NSGA-II shipped"),
    (re.compile(r"routing\s+solved", re.I), "NARROW", "routing solved"),
    (re.compile(r"LongMemEval\s*95", re.I), "DROP", "unmeasured LongMemEval score"),
    (re.compile(r"patent\s+moat|global\s+standard", re.I), "DROP", "marketing moat"),
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _posix_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def detect_overclaim_candidates(text: str) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    seen: set[str] = set()
    for pattern, filter_tag, label in OVERCLAIM_RULES:
        for match in pattern.finditer(text):
            key = f"{filter_tag}:{label}"
            if key in seen:
                continue
            seen.add(key)
            start = max(0, match.start() - 40)
            end = min(len(text), match.end() + 40)
            out.append(
                {
                    "filter": filter_tag,
                    "label": label,
                    "snippet": text[start:end].replace("\n", " ").strip(),
                }
            )
    return out


def _ollama_plane_hint(*, text: str, query: str, host: str, model: str, timeout: float) -> str | None:
    prompt = (
        "Classify this research raw drop into exactly one plane label:\n"
        "research_memory, research_edge, research_benchmarks, research_meta\n"
        f"Query: {query}\n"
        f"Excerpt:\n{text[:2000]}\n"
        "Reply with the label only."
    )
    payload = json.dumps(
        {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0},
        }
    ).encode("utf-8")
    url = f"{host.rstrip('/')}/api/generate"
    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            doc = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        return None
    response = str(doc.get("response") or "").strip().lower()
    for plane in ("research_memory", "research_edge", "research_benchmarks", "research_meta"):
        if plane in response:
            return plane
    return None


def build_raw_drop_delta(
    *,
    source_path: Path,
    query: str,
    baseline_arxiv_ids: set[str] | None = None,
    use_ollama: bool = False,
    ollama_host: str = DEFAULT_OLLAMA_HOST,
    ollama_model: str = DEFAULT_OLLAMA_MODEL,
    ollama_timeout: float = 30.0,
) -> dict[str, Any]:
    text = source_path.read_text(encoding="utf-8", errors="replace")
    arxiv_ids = extract_arxiv_ids(text)
    baseline = baseline_arxiv_ids or set()
    new_arxiv_ids = [aid for aid in arxiv_ids if aid not in baseline]
    rows = [{"arxiv_id": aid, "title": aid, "lane": "raw_drop"} for aid in arxiv_ids]
    plane_hint = classify_research_plane(query=query, rows=rows)
    extract_mode = "regex"
    if use_ollama:
        hinted = _ollama_plane_hint(
            text=text,
            query=query,
            host=ollama_host,
            model=ollama_model,
            timeout=ollama_timeout,
        )
        if hinted:
            plane_hint = hinted
            extract_mode = "hybrid"
    stat = source_path.stat()
    return {
        "schema": "mkm_raw_drop_delta_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc_now(),
        "source_path": _posix_path(source_path),
        "source_sha256": file_sha256(source_path),
        "source_mtime_utc": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        ),
        "query": query,
        "extract_mode": extract_mode,
        "arxiv_ids": arxiv_ids,
        "new_arxiv_ids": new_arxiv_ids,
        "arxiv_id_count": len(arxiv_ids),
        "new_arxiv_id_count": len(new_arxiv_ids),
        "plane_hint": plane_hint,
        "overclaim_candidates": detect_overclaim_candidates(text),
        "research_only": True,
        "send_gate": "HOLD",
        "hypothesis_class": "HYPO",
    }


def default_out_path(source: Path, out_dir: Path = DEFAULT_OUT_DIR) -> Path:
    stem = source.stem
    return out_dir / f"{stem}_raw_drop_delta_latest.json"


def main() -> int:
    parser = argparse.ArgumentParser(description="Build structured delta from Tier-0 raw markdown drop")
    parser.add_argument("--input", type=Path, required=True, help="Raw markdown under docs/research/raw/")
    parser.add_argument("--query", default="research raw drop")
    parser.add_argument("--baseline-md", type=Path, default=None, help="Existing MERGED/LIT_REVIEW for new-id diff")
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--use-ollama", action="store_true")
    parser.add_argument("--no-ollama", action="store_true", help="Force regex-only (default for CI)")
    parser.add_argument("--ollama-host", default=os.getenv("OLLAMA_HOST", DEFAULT_OLLAMA_HOST))
    parser.add_argument(
        "--ollama-model",
        default=os.getenv("OLLAMA_MODEL", DEFAULT_OLLAMA_MODEL),
    )
    args = parser.parse_args()

    source = args.input.resolve()
    if not source.is_file():
        print(json.dumps({"ok": False, "error": f"missing input: {source}"}, ensure_ascii=False), file=sys.stderr)
        return 2

    baseline_ids: set[str] = set()
    if args.baseline_md and args.baseline_md.is_file():
        baseline_ids = set(extract_arxiv_ids(args.baseline_md.read_text(encoding="utf-8", errors="replace")))

    use_ollama = bool(args.use_ollama and not args.no_ollama)
    doc = build_raw_drop_delta(
        source_path=source,
        query=args.query,
        baseline_arxiv_ids=baseline_ids,
        use_ollama=use_ollama,
        ollama_host=str(args.ollama_host),
        ollama_model=str(args.ollama_model),
    )
    out_path = args.out.resolve() if args.out else default_out_path(source)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    doc["out_path"] = _posix_path(out_path)
    print(
        json.dumps(
            {
                "ok": True,
                "out_path": doc["out_path"],
                "arxiv_id_count": doc["arxiv_id_count"],
                "new_arxiv_id_count": doc["new_arxiv_id_count"],
                "plane_hint": doc["plane_hint"],
                "extract_mode": doc["extract_mode"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
