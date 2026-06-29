#!/usr/bin/env python3
"""Verify MKM repo does not import AGPL bigset source (isolation wall smoke)."""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/final/artifacts/bigset_agpl_isolation_wall_v1_latest.json"

SCAN_ROOTS = [ROOT / "scripts", ROOT / "tests", ROOT / "projects/no1kmedi/src"]
FORBIDDEN_PATTERNS = [
    re.compile(r"from\s+bigset\b"),
    re.compile(r"import\s+bigset\b"),
    re.compile(r"tinyfish-io/bigset", re.I),
    re.compile(r"node_modules/@adamexu/bigset"),
]

ALLOWLIST_FILES = {
    "scripts/check_bigset_agpl_isolation_wall_v1.py",
    "scripts/bigset_agent_bridge_v1.py",
    "scripts/run_bigset_ingest_spike_chain_v1.py",
}


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def scan() -> tuple[bool, list[str]]:
    hits: list[str] = []
    for base in SCAN_ROOTS:
        if not base.is_dir():
            continue
        for path in base.rglob("*"):
            if not path.is_file():
                continue
            if path.suffix not in {".py", ".ts", ".tsx", ".mjs", ".js"}:
                continue
            rel = path.relative_to(ROOT).as_posix()
            if rel in ALLOWLIST_FILES:
                continue
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            for pat in FORBIDDEN_PATTERNS:
                if pat.search(text):
                    hits.append(f"{rel}: matched {pat.pattern}")
    return len(hits) == 0, hits


def main() -> int:
    ok, hits = scan()
    doc = {
        "schema": "bigset_agpl_isolation_wall_v1",
        "generated_at_utc": _now(),
        "ok": ok,
        "research_only": True,
        "send_gate": "HOLD",
        "forbidden": "import bigset source / vendor AGPL tree into MKM core",
        "allowed": "subprocess CLI + CSV/MD artifact ingest only",
        "violations": hits,
        "reproduce": "py scripts/check_bigset_agpl_isolation_wall_v1.py",
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": ok, "violations": len(hits)}, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
