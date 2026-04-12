#!/usr/bin/env python3
"""Probe NotebookLM sources (nlm) for LOG_METABOLISM-shaped JSONL; print one JSON result.

Stdout: single JSON object (machine-readable). Stderr: human progress.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
MANIFEST = ROOT / "docs/final/artifacts/derived/notebooklm_pull_manifest_v1.json"

from ingest_notebooklm_metabolism_jsonl import (  # noqa: E402
    _fetch_via_nlm,
    parse_and_validate_metabolism_jsonl,
)


def _nlm_json_load(stdout: str) -> Any:
    return json.loads(stdout.lstrip("\ufeff"))


def _list_sources(notebook_id: str, nlm_bin: str) -> list[dict[str, Any]]:
    cp = subprocess.run(
        [nlm_bin, "source", "list", notebook_id, "--json"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if cp.returncode != 0:
        msg = (cp.stderr or cp.stdout or "").strip()
        raise RuntimeError(f"nlm source list {notebook_id}: {msg}")
    data = _nlm_json_load(cp.stdout or "[]")
    if not isinstance(data, list):
        return []
    return [x for x in data if isinstance(x, dict)]


def _default_notebook_ids(extra: list[str]) -> list[str]:
    seen: list[str] = []
    if MANIFEST.is_file():
        doc = json.loads(MANIFEST.read_text(encoding="utf-8-sig"))
        for it in doc.get("items", []):
            nb = str(it.get("notebook_id") or "").strip()
            if nb and nb not in seen:
                seen.append(nb)
    for x in extra:
        x = str(x).strip()
        if x and x not in seen:
            seen.append(x)
    return seen


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--notebook-id",
        action="append",
        default=[],
        metavar="UUID",
        help="Extra notebook to scan (repeatable). Default: notebooklm_pull_manifest_v1.json",
    )
    ap.add_argument("--max-per-notebook", type=int, default=40, help="Max sources to fetch per notebook.")
    ap.add_argument("--min-rows", type=int, default=1, help="Minimum valid rows to accept a source.")
    ap.add_argument("--nlm-bin", default="nlm")
    ap.add_argument(
        "--quiet",
        action="store_true",
        help="No stderr progress (stdout is only the JSON line for shells).",
    )
    args = ap.parse_args()

    nlm = (args.nlm_bin or "nlm").strip()
    notebook_ids = _default_notebook_ids(list(args.notebook_id))
    if not notebook_ids:
        out = {
            "schema": "discover_nl_metabolism_source_v1",
            "match": None,
            "reason": "no_notebook_ids",
            "probed_sources": 0,
        }
        print(json.dumps(out, ensure_ascii=False))
        return 0

    probed = 0
    for nb in notebook_ids:
        if not args.quiet:
            print(f"[discover] notebook={nb}", file=sys.stderr)
        try:
            sources = _list_sources(nb, nlm)
        except RuntimeError as e:
            if not args.quiet:
                print(f"[discover] skip: {e}", file=sys.stderr)
            continue
        for src in sources[: max(1, args.max_per_notebook)]:
            sid = str(src.get("id") or "").strip()
            title = str(src.get("title") or "")
            if not sid:
                continue
            probed += 1
            try:
                raw = _fetch_via_nlm(sid, nlm)
            except RuntimeError as e:
                if not args.quiet:
                    print(f"[discover] fetch_fail {sid}: {e}", file=sys.stderr)
                continue
            rows, errs = parse_and_validate_metabolism_jsonl(raw)
            if errs or len(rows) < max(0, args.min_rows):
                continue
            out = {
                "schema": "discover_nl_metabolism_source_v1",
                "match": {
                    "notebook_id": nb,
                    "source_id": sid,
                    "title": title,
                    "valid_rows": len(rows),
                },
                "probed_sources": probed,
            }
            print(json.dumps(out, ensure_ascii=False))
            return 0

    out = {
        "schema": "discover_nl_metabolism_source_v1",
        "match": None,
        "reason": "no_valid_metabolism_jsonl_source",
        "probed_sources": probed,
        "notebooks_scanned": notebook_ids,
    }
    print(json.dumps(out, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
