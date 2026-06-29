#!/usr/bin/env python3
"""Append ops dynamical timeseries row after solo_ops / reddit snapshot change [HYPO · P1 wire]."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.ops_dynamical_bench_v1_lib import (  # noqa: E402
    DEFAULT_JSONL,
    DEFAULT_OUT,
    append_jsonl_row,
    build_report,
    load_json_rel,
    read_jsonl,
    timeseries_row_from_bench,
)
from scripts.ops_dynamical_bench_v1_lib import INPUT_PATHS, submit_tab_count  # noqa: E402

FP_PATH = ROOT / "reports/ops_dynamical_timeseries_fingerprint_v1.json"


def _fingerprint() -> str:
    reddit = load_json_rel(INPUT_PATHS[0])
    solo = load_json_rel(INPUT_PATHS[1])
    upgrade = load_json_rel(INPUT_PATHS[2])
    payload = {
        "submit_tabs": submit_tab_count(reddit),
        "solo_ok": solo.get("last_ok") if solo else None,
        "upgrade_ok": upgrade.get("ok") if upgrade else None,
        "reddit_ok": reddit.get("ok") if reddit else None,
    }
    raw = json.dumps(payload, sort_keys=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--jsonl", type=Path, default=DEFAULT_JSONL)
    ap.add_argument("--force", action="store_true", help="append even if fingerprint unchanged")
    args = ap.parse_args()

    fp = _fingerprint()
    prior = None
    if FP_PATH.is_file():
        prior = json.loads(FP_PATH.read_text(encoding="utf-8-sig")).get("fingerprint")

    if not args.force and prior == fp:
        print(json.dumps({"ok": True, "appended": False, "reason": "fingerprint_unchanged", "fingerprint": fp}))
        return 0

    bench = build_report()
    DEFAULT_OUT.write_text(json.dumps(bench, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    row = timeseries_row_from_bench(bench)
    row["source"] = "run_ops_dynamical_ops_snapshot_chain_v1"
    row["input_fingerprint"] = fp
    append_jsonl_row(args.jsonl, row)

    FP_PATH.parent.mkdir(parents=True, exist_ok=True)
    FP_PATH.write_text(
        json.dumps({"fingerprint": fp, "rows": len(read_jsonl(args.jsonl))}, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "ok": True,
                "appended": True,
                "fingerprint": fp,
                "jsonl": str(args.jsonl),
                "stage": bench["state_machine"]["stage"],
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
