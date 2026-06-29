#!/usr/bin/env python3
"""Merge extract-gate case rows from example + n40 corpora."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EXAMPLE = ROOT / "data/btrack/cursor_coding_compress_bench_v1.example.jsonl"
N40 = ROOT / "data/btrack/cursor_coding_compress_bench_v1_n40.jsonl"
DEFAULT_OUT = ROOT / "data/btrack/cursor_coding_agent_extract_input_v1.jsonl"

DEFAULT_IDS = (
    "cc_005",
    "cc_n07",
    "cc_n12",
    "cc_n21",
    "cc_n23",
    "cc_n26",
    "cc_n28",
    "cc_n34",
    "cc_n35",
    "cc_n39",
    "cc_n40",
)


def _load_rows(path: Path) -> dict[str, dict]:
    out: dict[str, dict] = {}
    if not path.is_file():
        return out
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        row = json.loads(line)
        if isinstance(row, dict) and row.get("id"):
            out[str(row["id"])] = row
    return out


def build_input(*, case_ids: tuple[str, ...]) -> list[dict]:
    merged = {**_load_rows(EXAMPLE), **_load_rows(N40)}
    missing = [cid for cid in case_ids if cid not in merged]
    if missing:
        raise SystemExit(f"missing case ids for extract input: {missing}")
    return [merged[cid] for cid in case_ids]


def main() -> int:
    ap = argparse.ArgumentParser(description="Build merged extract-gate input JSONL.")
    ap.add_argument("--out-jsonl", default=str(DEFAULT_OUT))
    ap.add_argument("--case-id", action="append", dest="case_ids")
    args = ap.parse_args()
    ids = tuple(args.case_ids) if args.case_ids else DEFAULT_IDS
    rows = build_input(case_ids=ids)
    out = Path(args.out_jsonl)
    if not out.is_absolute():
        out = ROOT / out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n",
        encoding="utf-8",
    )
    print(str(out))
    print({"case_count": len(rows), "ids": list(ids)})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
