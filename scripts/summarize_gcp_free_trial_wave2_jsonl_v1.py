"""Summarize GCP Free Trial Wave2 JSONL asset file (local or remote path)."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--jsonl", type=Path, required=True)
    ap.add_argument("--expected-lines", type=int, default=150)
    ap.add_argument("--out-json", type=Path, default=Path("reports/gcp_free_trial_vertex_credit_burn_v1_latest.json"))
    args = ap.parse_args()

    if not args.jsonl.is_file():
        print(json.dumps({"ok": False, "error": f"missing {args.jsonl}"}))
        return 2

    ok = err = dry = 0
    indices: set[int] = set()
    for line in args.jsonl.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        indices.add(int(row.get("index", 0)))
        st = row.get("status")
        if st == "ok":
            ok += 1
        elif st == "dry_run":
            dry += 1
        else:
            err += 1

    lines = ok + err + dry
    payload = {
        "schema": "gcp_free_trial_vertex_credit_burn_v1",
        "wave_id": "wave2",
        "jsonl_path": str(args.jsonl),
        "lines": lines,
        "calls_ok": ok,
        "calls_failed": err,
        "dry_run_rows": dry,
        "unique_indices": len(indices),
        "expected_lines": args.expected_lines,
        "complete": lines >= args.expected_lines and err == 0 and dry == 0 and ok >= args.expected_lines,
        "governance": {
            "hypothesis_tier": "B",
            "track_wall": "btrack_research_only",
            "final_action": "WATCH",
        },
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": payload["complete"], "lines": lines, "calls_ok": ok, "calls_failed": err}))
    return 0 if payload["complete"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
