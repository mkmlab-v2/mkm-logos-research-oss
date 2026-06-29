#!/usr/bin/env python3
"""Build router smoke report: 75 MKM12 slots → 12 A-code packs (B-track)."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "reports/lora_tranche2_mkm12_75_to_12_router_smoke_latest.json"
GOLDEN = ROOT / "docs/final/artifacts/mkm_control_integrity_golden_v1.jsonl"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="MKM12 75→12 router smoke report builder.")
    p.add_argument("--out-json", default=str(DEFAULT_OUT))
    p.add_argument("--golden-jsonl", default=str(GOLDEN))
    p.add_argument("--skip-golden", action="store_true")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    out_path = Path(args.out_json)
    if not out_path.is_absolute():
        out_path = ROOT / out_path

    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts/route_mkm12_formula_to_acode_pack_v1.py"), "--out-json", str(out_path)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        print(proc.stderr or proc.stdout, file=sys.stderr)
        return proc.returncode

    payload = json.loads(out_path.read_text(encoding="utf-8-sig"))
    payload["generated_at_utc"] = _utc_now()
    payload["smoke_ok"] = bool(payload.get("routing_wired_ok"))

    golden_rows: list[dict] = []
    if not args.skip_golden and Path(args.golden_jsonl).is_file():
        from scripts.mkm12_acode_pack_router_v1 import load_json, route_golden_row_to_pack

        registry = load_json(ROOT / "docs/final/artifacts/acode_12_pack_registry_v1.json")
        formulas_doc = load_json(ROOT / "docs/final/artifacts/mkm12_75_formulas_ssot_v1_latest.json")
        with Path(args.golden_jsonl).open(encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                row = json.loads(line)
                golden_rows.append(route_golden_row_to_pack(row, registry=registry, formulas_doc=formulas_doc))
                if len(golden_rows) >= 24:
                    break
        payload["golden_row_routes"] = golden_rows
        payload["golden_row_count"] = len(golden_rows)
        payload["golden_row_distinct_packs"] = len({r["pack_id"] for r in golden_rows})

    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"out": str(out_path), "smoke_ok": payload["smoke_ok"]}))
    return 0 if payload["smoke_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
