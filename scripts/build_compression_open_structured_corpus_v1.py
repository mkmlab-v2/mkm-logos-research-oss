#!/usr/bin/env python3
"""Verify (or refresh manifest for) open structured compression PoC corpora.

Does not fetch external data — uses repo-fixed JSONL under data/compression/.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CORPORA = (
    ROOT / "data/compression/stateless_poc_open_structured_v1.jsonl",
    ROOT / "data/compression/stateless_poc_open_structured_long_v1.jsonl",
    ROOT / "data/compression/stateless_poc_golden40_public_safe_v1.jsonl",
)
OUT_DEFAULT = ROOT / "docs/final/artifacts/compression_open_structured_corpus_manifest_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _line_count(path: Path) -> int:
    n = 0
    with path.open("r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            if line.strip():
                n += 1
    return n


def build(*, corpora: tuple[Path, ...] = DEFAULT_CORPORA) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for path in corpora:
        rel = path.relative_to(ROOT).as_posix()
        if not path.is_file():
            rows.append({"path": rel, "ok": False, "error": "missing"})
            continue
        rows.append(
            {
                "path": rel,
                "ok": True,
                "sha256": _sha256(path),
                "line_count": _line_count(path),
            }
        )
    ok = all(r.get("ok") for r in rows)
    return {
        "schema": "compression_open_structured_corpus_manifest_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "corpora": rows,
        "ok": ok,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-json", type=Path, default=OUT_DEFAULT)
    ap.add_argument(
        "--strict",
        action="store_true",
        help="Exit 1 if any default corpus file is missing.",
    )
    args = ap.parse_args()
    doc = build()
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc["ok"], "output": str(args.out_json)}, ensure_ascii=False))
    if args.strict and not doc["ok"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
