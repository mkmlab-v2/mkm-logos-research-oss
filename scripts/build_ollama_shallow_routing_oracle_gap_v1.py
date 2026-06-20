#!/usr/bin/env python3
"""Shadow eval: routing_oracle_gap + cloud_skip_ratio for Ollama shallow router v1 [HYPO].

Joins bench rows with golden fixture metadata. Oracle = expected_domain_tag in fixtures.
Does not open SEND or Track A gates.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BENCH = ROOT / "reports/ollama_shallow_router_bench_v1_latest.json"
DEFAULT_FIXTURES = ROOT / "tests/fixtures/ollama_shallow_router_golden_v1.json"
DEFAULT_OUT = ROOT / "reports/ollama_shallow_routing_oracle_gap_v1_latest.json"
DEEP_DOMAINS = frozenset({"logos", "oracle"})
SCHEMA_ID = "ollama_shallow_routing_oracle_gap_v1"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _load_fixture_meta(fixtures_path: Path) -> dict[str, dict[str, Any]]:
    doc = _read_json(fixtures_path)
    meta: dict[str, dict[str, Any]] = {}
    for row in doc.get("fixtures", []):
        if not isinstance(row, dict):
            continue
        fid = str(row.get("id") or "")
        tag = str(row.get("expected_domain_tag") or "")
        if not fid or not tag:
            continue
        deep_required = row.get("deep_chain_required")
        if deep_required is None:
            deep_required = tag in DEEP_DOMAINS
        meta[fid] = {
            "expected_domain_tag": tag,
            "deep_chain_required": bool(deep_required),
        }
    return meta


def build_oracle_gap_report(
    bench: dict[str, Any],
    fixture_meta: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    rows = bench.get("rows") if isinstance(bench.get("rows"), list) else []
    evaluated: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        fid = str(row.get("fixture_id") or "")
        meta = fixture_meta.get(fid)
        if meta is None:
            continue
        expected = meta["expected_domain_tag"]
        actual = str(row.get("parsed_domain_tag") or row.get("domain_tag") or "")
        router_hit = bool(row.get("router_hit"))
        if not router_hit and actual:
            router_hit = actual == expected
        deep_required = bool(meta["deep_chain_required"])
        shallow_only_ok = (not deep_required) and router_hit
        evaluated.append(
            {
                "fixture_id": fid,
                "expected_domain_tag": expected,
                "parsed_domain_tag": actual or None,
                "router_hit": router_hit,
                "deep_chain_required": deep_required,
                "shallow_only_eligible": not deep_required,
                "shallow_only_ok": shallow_only_ok,
                "deep_routing_ok": deep_required and router_hit,
            }
        )

    total = len(evaluated)
    router_hits = sum(1 for r in evaluated if r["router_hit"])
    router_hit_rate = round(router_hits / total, 4) if total else 0.0
    routing_oracle_gap = round(1.0 - router_hit_rate, 4) if total else 1.0

    shallow_eligible = [r for r in evaluated if r["shallow_only_eligible"]]
    shallow_ok = [r for r in shallow_eligible if r["shallow_only_ok"]]
    cloud_skip_ratio = round(len(shallow_ok) / len(shallow_eligible), 4) if shallow_eligible else 0.0

    deep_required_rows = [r for r in evaluated if r["deep_chain_required"]]
    deep_ok = [r for r in deep_required_rows if r["deep_routing_ok"]]
    deep_routing_recall = (
        round(len(deep_ok) / len(deep_required_rows), 4) if deep_required_rows else 0.0
    )

    bench_raw = bench.get("raw") if isinstance(bench.get("raw"), dict) else {}
    return {
        "schema": SCHEMA_ID,
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "send_gate": "HOLD",
        "hypothesis_class": "HYPO",
        "bench_schema": bench.get("schema"),
        "bench_mode": bench.get("mode"),
        "fixtures_evaluated": total,
        "raw": {
            "router_hit_rate": router_hit_rate,
            "routing_oracle_gap": routing_oracle_gap,
            "cloud_skip_ratio": cloud_skip_ratio,
            "deep_routing_recall": deep_routing_recall,
            "rows": total,
        },
        "repair_v2": {
            "note": "No repair layer; metrics equal raw.",
            "router_hit_rate": router_hit_rate,
            "routing_oracle_gap": routing_oracle_gap,
            "cloud_skip_ratio": cloud_skip_ratio,
            "deep_routing_recall": deep_routing_recall,
            "rows": total,
        },
        "delta": {
            "routing_oracle_gap_delta_repair_v2_minus_raw": 0.0,
        },
        "rows": evaluated,
        "bench_raw_pointer": bench_raw,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Shallow router routing_oracle_gap shadow eval v1")
    ap.add_argument("--bench-json", type=Path, default=DEFAULT_BENCH)
    ap.add_argument("--fixtures", type=Path, default=DEFAULT_FIXTURES)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument(
        "--max-oracle-gap",
        type=float,
        default=None,
        help="Fail exit 1 if routing_oracle_gap exceeds this threshold",
    )
    ap.add_argument(
        "--min-cloud-skip-ratio",
        type=float,
        default=None,
        help="Fail exit 1 if cloud_skip_ratio below this threshold",
    )
    args = ap.parse_args()

    bench_path = args.bench_json if args.bench_json.is_absolute() else ROOT / args.bench_json
    fixtures_path = args.fixtures if args.fixtures.is_absolute() else ROOT / args.fixtures
    if not bench_path.is_file():
        raise SystemExit(f"bench json missing: {bench_path}")
    if not fixtures_path.is_file():
        raise SystemExit(f"fixtures missing: {fixtures_path}")

    bench = _read_json(bench_path)
    if bench.get("mode") in {"skipped", "unreachable"}:
        raise SystemExit(f"bench mode {bench.get('mode')!r} has no live rows for oracle gap")

    meta = _load_fixture_meta(fixtures_path)
    report = build_oracle_gap_report(bench, meta)
    out_path = args.out_json if args.out_json.is_absolute() else ROOT / args.out_json
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    gap = float(report["raw"]["routing_oracle_gap"])
    skip = float(report["raw"]["cloud_skip_ratio"])
    ok = True
    if args.max_oracle_gap is not None and gap > args.max_oracle_gap:
        ok = False
    if args.min_cloud_skip_ratio is not None and skip < args.min_cloud_skip_ratio:
        ok = False

    print(
        json.dumps(
            {
                "ok": ok,
                "out": str(out_path),
                "raw": report["raw"],
                "delta": report["delta"],
            },
            ensure_ascii=False,
        )
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
