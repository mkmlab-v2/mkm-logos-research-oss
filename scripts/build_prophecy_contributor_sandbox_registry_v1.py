#!/usr/bin/env python3
"""Build sandbox general_prophecy registry from contributor JSONL (never writes general_prophecy_latest)."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "reports/prophecy_contributor_sandbox_registry_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _to_question_row(row: dict[str, Any]) -> dict[str, Any]:
    q = {k: v for k, v in row.items() if k not in ("contributor_provided", "customer_provided", "labels", "send_gate", "ready_for_external_send", "provenance_note")}
    q["schema"] = "general_prophecy_question_v1"
    q.setdefault("research_rail", "B")
    q.setdefault("boundary_ack", True)
    return q


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--jsonl", type=Path, required=True)
    ap.add_argument("--tenant-id", default="prophecy-contributor-community-v1")
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    inp = args.jsonl.resolve()
    if not inp.is_file():
        print(f"error: missing jsonl: {inp}", file=sys.stderr)
        return 2

    questions: list[dict[str, Any]] = []
    for line in inp.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if isinstance(row, dict):
            questions.append(_to_question_row(row))

    doc: dict[str, Any] = {
        "schema": "general_prophecy_registry_v1",
        "version": "1.0.0",
        "research_rail": "B",
        "boundary_ack": True,
        "generated_at_utc": _utc(),
        "git_commit_hint": f"contributor_sandbox:{args.tenant_id}",
        "contributor_lane": {
            "tenant_id": args.tenant_id,
            "lane": "contributor_provided",
            "input_jsonl": _rel(inp),
            "input_sha256": _sha256_file(inp),
            "not_production_registry": True,
        },
        "questions": questions,
    }

    out = args.out_json.resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "questions": len(questions), "out": _rel(out)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
