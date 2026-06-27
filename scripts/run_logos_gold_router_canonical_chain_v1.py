#!/usr/bin/env python3
"""Chain: canonicalize gold router artifacts → gold eval refresh [HYPO][research_only]."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
OUT = ROOT / "reports/logos_gold_router_canonical_chain_v1_latest.json"


def _run(script: str, extra: list[str] | None = None) -> dict:
    cmd = [PY, str(ROOT / "scripts" / script)] + (extra or [])
    cp = subprocess.run(
        cmd,
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=300,
    )
    return {
        "step": script,
        "exit_code": cp.returncode,
        "stdout": (cp.stdout or "").strip()[-1500:],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--promote-gold-prefix-first",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Reorder router verse_ids: gold ids/prefixes first (default on)",
    )
    ap.add_argument("--out-json", type=Path, default=OUT)
    args = ap.parse_args()

    mat_extra = ["--query-id", "q02", "--query-id", "q05"]
    if args.promote_gold_prefix_first:
        mat_extra.append("--promote-gold-prefix-first")

    steps = [
        _run("materialize_logos_gold_router_live_v1.py", mat_extra),
        _run("build_logos_gold_query_eval_report_v1.py"),
    ]
    ok = all(s["exit_code"] == 0 for s in steps)

    gold = json.loads((ROOT / "reports/logos_gold_query_eval_v1_latest.json").read_text(encoding="utf-8-sig"))
    rows = {r["id"]: r.get("hit_at_k", {}).get("1", {}) for r in gold.get("rows") or []}

    doc = {
        "schema": "logos_gold_router_canonical_chain_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "ok": ok,
        "research_only": True,
        "promote_gold_prefix_first": args.promote_gold_prefix_first,
        "steps": steps,
        "router_hit_at_1": {"q02": rows.get("q02"), "q05": rows.get("q05")},
        "gold_required_all_pass": gold.get("summary", {}).get("gold_required_all_pass"),
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": ok, "router_hit_at_1": doc["router_hit_at_1"], "out": str(args.out_json)}))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
