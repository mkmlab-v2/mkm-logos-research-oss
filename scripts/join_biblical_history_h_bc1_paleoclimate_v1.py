#!/usr/bin/env python3
"""Join H-BC1 chronology sidecar with paleoclimate proxy CSV (B-track, no APIs)."""

from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SIDECAR = ROOT / "docs/final/artifacts/biblical_history_h_bc1_bronze_collapse_chronology_sidecar_v1.json"
DEFAULT_PROXY = ROOT / "tests/fixtures/h_bc1_paleoclimate_proxy_v1.csv"
DEFAULT_OUT = ROOT / "reports/biblical_history_h_bc1_paleoclimate_join_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_proxy_csv(path: Path) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    with path.open(encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            rows.append({k: str(v) for k, v in row.items()})
    return rows


def _region_map(node: dict[str, Any]) -> str:
    region = str(node.get("region") or "").lower()
    if region == "levant":
        return "levant"
    if region == "anatolia":
        return "anatolia"
    if region == "aegean":
        return "aegean"
    if region == "egypt":
        return "egypt_nile"
    return "eastern_mediterranean"


def main() -> int:
    ap = argparse.ArgumentParser(description="Join H-BC1 sidecar nodes with paleoclimate proxy CSV.")
    ap.add_argument("--sidecar-json", type=Path, default=DEFAULT_SIDECAR)
    ap.add_argument("--proxy-csv", type=Path, default=DEFAULT_PROXY)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--year-tolerance-bce", type=int, default=30)
    args = ap.parse_args()

    if not args.sidecar_json.is_file():
        raise SystemExit(f"missing sidecar: {args.sidecar_json}")
    if not args.proxy_csv.is_file():
        raise SystemExit(f"missing proxy csv: {args.proxy_csv}")

    sidecar = _load_json(args.sidecar_json)
    proxies = _read_proxy_csv(args.proxy_csv)
    proxy_by_region: dict[str, list[dict[str, str]]] = {}
    for p in proxies:
        proxy_by_region.setdefault(p.get("region", ""), []).append(p)

    joined: list[dict[str, Any]] = []
    drought_vals: list[float] = []
    for node in sidecar.get("nodes") or []:
        if not isinstance(node, dict):
            continue
        mid = int(node.get("date_bce_mid", 0))
        region_key = _region_map(node)
        candidates = proxy_by_region.get(region_key, []) + proxy_by_region.get("eastern_mediterranean", [])
        best = None
        best_delta = 10**9
        for c in candidates:
            try:
                y = int(c.get("year_bce", "0"))
            except ValueError:
                continue
            delta = abs(y - mid)
            if delta <= args.year_tolerance_bce and delta < best_delta:
                best_delta = delta
                best = c
        drought = None
        if best is not None:
            try:
                drought = float(best.get("drought_index_0_1", ""))
                drought_vals.append(drought)
            except ValueError:
                drought = None
        joined.append(
            {
                "node_id": node.get("node_id"),
                "date_bce_mid": mid,
                "region": node.get("region"),
                "proxy_match": best,
                "drought_index_0_1": drought,
            }
        )

    mean_drought = round(sum(drought_vals) / len(drought_vals), 4) if drought_vals else None
    out = {
        "schema": "biblical_history_h_bc1_paleoclimate_join_v1",
        "generated_at_utc": _utc_now(),
        "research_rail": "B",
        "hypothesis_tier": "[HYPO]",
        "gating_status": "NON_GATING",
        "inputs": {
            "sidecar_json": str(args.sidecar_json),
            "proxy_csv": str(args.proxy_csv),
            "year_tolerance_bce": args.year_tolerance_bce,
        },
        "summary": {
            "nodes_joined": len(joined),
            "proxy_matches": sum(1 for j in joined if j.get("proxy_match")),
            "mean_drought_index_0_1": mean_drought,
        },
        "joined_nodes": joined,
        "fact_lock_notice": "Proxy stub for research lane; not paleoclimate proof or gating input.",
    }

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "output": str(args.output_json), "matches": out["summary"]["proxy_matches"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
