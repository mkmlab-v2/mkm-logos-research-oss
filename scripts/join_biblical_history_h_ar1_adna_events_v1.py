#!/usr/bin/env python3
"""Join H-AR1 chronology sidecar with peer-reviewed aDNA event table CSV (B-track, no APIs)."""

from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SIDECAR = ROOT / "docs/final/artifacts/biblical_history_h_ar1_adna_migration_chronology_sidecar_v1.json"
DEFAULT_EVENTS = ROOT / "tests/fixtures/h_ar1_adna_peer_events_v1.csv"
DEFAULT_OUT = ROOT / "reports/biblical_history_h_ar1_adna_events_join_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_events_csv(path: Path) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    with path.open(encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            rows.append({k: str(v).strip() for k, v in row.items()})
    return rows


def _region_key(region: str) -> str:
    r = region.lower().replace(" ", "")
    if r in ("eurasiansteppe", "steppe"):
        return "eurasiansteppe"
    if r == "levant":
        return "levant"
    if r == "global":
        return "global"
    return r


def main() -> int:
    ap = argparse.ArgumentParser(description="Join H-AR1 sidecar nodes with aDNA peer event CSV.")
    ap.add_argument("--sidecar-json", type=Path, default=DEFAULT_SIDECAR)
    ap.add_argument("--events-csv", type=Path, default=DEFAULT_EVENTS)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--year-tolerance", type=int, default=150)
    args = ap.parse_args()

    if not args.sidecar_json.is_file():
        raise SystemExit(f"missing sidecar: {args.sidecar_json}")
    if not args.events_csv.is_file():
        raise SystemExit(f"missing events csv: {args.events_csv}")

    sidecar = _load_json(args.sidecar_json)
    events = _read_events_csv(args.events_csv)
    by_region: dict[str, list[dict[str, str]]] = {}
    for ev in events:
        by_region.setdefault(_region_key(ev.get("region", "")), []).append(ev)

    joined: list[dict[str, Any]] = []
    tier_counts: dict[str, int] = {}
    for node in sidecar.get("nodes") or []:
        if not isinstance(node, dict):
            continue
        node_id = str(node.get("node_id") or "")
        region = _region_key(str(node.get("region") or ""))
        ce_mid = node.get("date_ce_mid")
        bce_mid = node.get("date_bce_mid")
        target_year: int | None = int(ce_mid) if isinstance(ce_mid, int) else None
        era = "ce"
        if target_year is None and isinstance(bce_mid, int):
            target_year = abs(int(bce_mid))
            era = "bce"
        if target_year is None:
            continue

        candidates = by_region.get(region, []) + by_region.get("global", [])
        best = None
        best_delta = 10**9
        for c in candidates:
            year_key = "year_ce" if era == "ce" else "year_bce"
            raw = c.get(year_key, "")
            if not raw:
                continue
            try:
                y = abs(int(raw))
            except ValueError:
                continue
            delta = abs(y - target_year)
            if delta <= args.year_tolerance and delta < best_delta:
                best_delta = delta
                best = c

        row: dict[str, Any] = {
            "node_id": node_id,
            "era": era,
            "target_year": target_year,
            "matched": best is not None,
        }
        if best:
            tier = str(best.get("study_tier") or "unknown")
            tier_counts[tier] = tier_counts.get(tier, 0) + 1
            row.update(
                {
                    "matched_event_id": best.get("event_id"),
                    "matched_label": best.get("label"),
                    "study_tier": tier,
                    "year_delta": best_delta,
                    "citation_stub": best.get("citation_stub"),
                }
            )
        joined.append(row)

    matched = sum(1 for j in joined if j.get("matched"))
    payload = {
        "schema": "biblical_history_h_ar1_adna_events_join_v1",
        "hypothesis_id": "H-AR1",
        "generated_at_utc": _utc_now(),
        "research_rail": "B",
        "hypothesis_tier": "[HYPO]",
        "gating_status": "NON_GATING",
        "inputs": {
            "sidecar_json": str(args.sidecar_json),
            "events_csv": str(args.events_csv),
            "year_tolerance": args.year_tolerance,
        },
        "joined": joined,
        "summary": {
            "node_count": len(joined),
            "peer_event_matches": matched,
            "study_tier_counts": tier_counts,
        },
        "fact_lock_notice": "aDNA table join is narrative calibration only; NON_GATING; no Track A promotion.",
    }

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "output": str(args.output_json), "peer_event_matches": matched}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
