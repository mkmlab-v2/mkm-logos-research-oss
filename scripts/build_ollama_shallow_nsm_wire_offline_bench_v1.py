#!/usr/bin/env python3
"""Build offline shallow router bench with NSM wire enrichment (no Ollama) [HYPO]."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.ollama_shallow_router_nsm_v1 import enrich_shallow_output, nsm_wire_ok  # noqa: E402

DEFAULT_FIXTURES = ROOT / "tests/fixtures/ollama_shallow_router_golden_v1.json"
DEFAULT_OUT = ROOT / "reports/ollama_shallow_router_bench_nsm_wire_offline_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def build_offline_bench(fixtures: list[dict[str, Any]]) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for fix in fixtures:
        shallow = enrich_shallow_output(
            {
                "schema": "ollama_shallow_router_output_v1",
                "research_only": True,
                "send_gate": "HOLD",
                "hypothesis_class": "HYPO",
                "domain_tag": fix["expected_domain_tag"],
                "coordinates": {"S": 0.25, "L": 0.25, "K": 0.25, "M": 0.25},
                "anchor_ids": [],
                "parse_status": "raw",
            },
            input_text=fix["input"],
        )
        rows.append(
            {
                "fixture_id": fix["id"],
                "expected_domain_tag": fix["expected_domain_tag"],
                "parse_ok": True,
                "schema_ok": True,
                "router_hit": True,
                "parsed_domain_tag": shallow.get("domain_tag"),
                "parsed_output": shallow,
                "nsm_prime_tags": shallow.get("nsm_prime_tags"),
                "nsm_wire_ok": nsm_wire_ok(shallow),
                "mode": "offline_nsm_wire",
            }
        )
    total = len(rows)
    nsm_ok = sum(1 for r in rows if r.get("nsm_wire_ok"))
    return {
        "schema": "ollama_shallow_router_bench_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "send_gate": "HOLD",
        "hypothesis_class": "HYPO",
        "mode": "offline_nsm_wire",
        "model": "offline_stub",
        "host": "offline",
        "fixtures_path": str(DEFAULT_FIXTURES.relative_to(ROOT)).replace("\\", "/"),
        "raw": {
            "parse_ok_rate": 1.0,
            "router_hit_rate": 1.0,
            "schema_ok_rate": 1.0,
            "nsm_wire_ok_rate": round(nsm_ok / total, 4) if total else 0.0,
            "rows": total,
        },
        "rows": rows,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--fixtures", type=Path, default=DEFAULT_FIXTURES)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    doc = json.loads(args.fixtures.read_text(encoding="utf-8"))
    fixtures = []
    for row in doc.get("fixtures") or []:
        if not isinstance(row, dict):
            continue
        inp = str(row.get("input") or "").strip()
        tag = str(row.get("expected_domain_tag") or "").strip()
        if inp and tag:
            fixtures.append({"id": str(row.get("id")), "input": inp, "expected_domain_tag": tag})
    report = build_offline_bench(fixtures)
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": report["raw"]["nsm_wire_ok_rate"] == 1.0,
                "out": str(args.out_json),
                "nsm_wire_ok_rate": report["raw"]["nsm_wire_ok_rate"],
            },
            ensure_ascii=False,
        )
    )
    return 0 if report["raw"]["nsm_wire_ok_rate"] == 1.0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
