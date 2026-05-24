#!/usr/bin/env python3
"""DF-P1-02: Selective verse load from logos_verse_4d corpus by verse_id list."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "logos_verse_selective_load_v1"


def _load_manifest(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _corpus_path(manifest: dict[str, Any]) -> Path:
    outputs = manifest.get("outputs") or {}
    raw = outputs.get("verse_4d_jsonl") or (manifest.get("inputs") or {}).get("primary_jsonl")
    if not raw:
        raise ValueError("manifest missing verse_4d_jsonl path")
    p = Path(str(raw))
    if not p.is_absolute():
        p = ROOT / p
    return p


def _bare_verse_id(verse_id: str) -> str:
    return verse_id.split("::", 1)[-1] if "::" in verse_id else verse_id


def _load_ids(args: argparse.Namespace) -> list[str]:
    if args.ids:
        return [x.strip() for x in args.ids.split(",") if x.strip()]
    if args.ids_file:
        path = ROOT / args.ids_file if not Path(args.ids_file).is_absolute() else Path(args.ids_file)
        doc = json.loads(path.read_text(encoding="utf-8-sig"))
        if isinstance(doc, list):
            return [str(x) for x in doc]
        rag = doc.get("graph_rag") or {}
        for container in (doc, rag):
            for key in ("verse_node_ids", "verse_atom_ids", "verse_ids"):
                if key in container:
                    return [str(x) for x in container[key]]
        raise ValueError(f"ids file missing verse id list: {path}")
    raise ValueError("provide --ids or --ids-file")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--manifest-json",
        default="docs/final/artifacts/logos_verse_4d_corpus_v1_latest.json",
    )
    parser.add_argument(
        "--ids-file",
        default="docs/final/artifacts/logos_graph_seed_chain_v1_latest.json",
        help="Seed chain JSON or plain id list file",
    )
    parser.add_argument("--ids", default="", help="Comma-separated verse_ids override")
    parser.add_argument(
        "--out-jsonl",
        default="docs/final/artifacts/logos_verse_selective_load_v1_latest.jsonl",
    )
    parser.add_argument(
        "--out-report-json",
        default="docs/final/artifacts/logos_verse_selective_load_v1_latest.json",
    )
    args = parser.parse_args()

    manifest_path = ROOT / args.manifest_json
    if not manifest_path.is_file():
        print(f"missing manifest: {manifest_path}", file=sys.stderr)
        return 1

    requested = _load_ids(args)
    if not requested:
        print("empty id set", file=sys.stderr)
        return 1

    wanted_bare = {_bare_verse_id(v) for v in requested}

    corpus_path = _corpus_path(_load_manifest(manifest_path))
    if not corpus_path.is_file():
        print(f"missing corpus: {corpus_path}", file=sys.stderr)
        return 1

    found: list[dict[str, Any]] = []
    for line in corpus_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        row = json.loads(line)
        vid = str(row.get("verse_id") or "")
        if _bare_verse_id(vid) in wanted_bare:
            found.append(row)
            wanted_bare.discard(_bare_verse_id(vid))
        if not wanted_bare:
            break

    missing = sorted(wanted_bare)
    out_jsonl = Path(args.out_jsonl)
    if not out_jsonl.is_absolute():
        out_jsonl = ROOT / out_jsonl
    out_jsonl.parent.mkdir(parents=True, exist_ok=True)
    with out_jsonl.open("w", encoding="utf-8") as fh:
        for row in found:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")

    report = {
        "schema": SCHEMA,
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "hypothesis_tier": "[HYPO]",
        "research_only": True,
        "corpus_path": str(corpus_path.relative_to(ROOT)).replace("\\", "/"),
        "requested_count": len(requested),
        "found_count": len(found),
        "missing_count": len(missing),
        "missing_verse_ids_sample": missing[:20],
        "output_jsonl": (
            str(out_jsonl.relative_to(ROOT)).replace("\\", "/")
            if out_jsonl.is_relative_to(ROOT)
            else str(out_jsonl)
        ),
    }
    out_report = Path(args.out_report_json)
    if not out_report.is_absolute():
        out_report = ROOT / out_report
    out_report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(
        json.dumps(
            {
                "ok": len(missing) == 0 or len(found) > 0,
                "found": len(found),
                "missing": len(missing),
                "out": str(out_report),
            },
            ensure_ascii=False,
        )
    )
    return 0 if found else 1


if __name__ == "__main__":
    raise SystemExit(main())
