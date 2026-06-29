#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build per-date sasang JSONL via market_psych v2 -> market_sasang lens [HYPO][research_only]."""
from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.market_psych_sasang_axis_v2 import (  # noqa: E402
    load_manifest,
    map_row_to_sasang,
    validate_psych_csv_fields,
)
from scripts.market_psych_v2_lens_bridge_v1 import sasang_upstream_stub_from_v2_mapping  # noqa: E402
from scripts.market_sasang_lens_engine_v1 import build_market_sasang_lens_payload, load_policy  # noqa: E402

DEFAULT_CSV = ROOT / "data/market_sasang/market_psychology_kospi_from_yfinance_v2_latest.csv"
DEFAULT_MANIFEST = ROOT / "docs/final/artifacts/market_psych_to_sasang_axis_manifest_v2.json"
DEFAULT_POLICY = ROOT / "data/market_sasang/market_sasang_lens_policy_v1.json"
DEFAULT_OUT = ROOT / "reports/btrack_market_sasang_per_date_v1.jsonl"
DEFAULT_MANIFEST_OUT = ROOT / "reports/btrack_market_sasang_per_date_manifest_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _write_jsonl(rows: list[dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")


def build_market_sasang_per_date_rows(
    *,
    csv_path: Path,
    manifest_path: Path,
    policy_path: Path,
    date_from: str | None,
    date_to: str | None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    manifest = load_manifest(manifest_path)
    policy = load_policy(policy_path)
    rows_csv: list[dict[str, str]] = []
    with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        validate_psych_csv_fields(reader.fieldnames, manifest)
        rows_csv = list(reader)
    if not rows_csv:
        raise ValueError(f"empty market psych csv: {csv_path}")

    df = date_from[:10] if date_from else None
    dt = date_to[:10] if date_to else None
    out: list[dict[str, Any]] = []
    prev_stress: float | None = None
    for row in rows_csv:
        ed = str(row.get("timestamp_utc") or "")[:10]
        if len(ed) != 10:
            continue
        if df and ed < df:
            continue
        if dt and ed > dt:
            continue
        mapping = map_row_to_sasang(row, manifest=manifest, prev_stress=prev_stress)
        prev_stress = float((mapping.get("byungjeung") or {}).get("stress_index") or 0.0)
        upstream = sasang_upstream_stub_from_v2_mapping(mapping, eval_date=ed)
        lens = build_market_sasang_lens_payload(
            sasang_lens_doc=upstream,
            policy=policy,
            policy_path=str(policy_path.resolve()),
            source_input_path=str(csv_path.resolve()),
        )
        fusion = lens.get("fusion_bridge") if isinstance(lens.get("fusion_bridge"), dict) else {}
        mapping_target = str(mapping.get("mapping_target") or fusion.get("direction_hint") or "neutral")
        bj = mapping.get("byungjeung") if isinstance(mapping.get("byungjeung"), dict) else {}
        out.append(
            {
                "ts_utc": f"{ed}T12:00:00+00:00",
                "eval_date": ed,
                "hypothesis_tier": "B",
                "boundary_ack": True,
                "stub": False,
                "source_provenance": "market_psych_v2_per_date_v1",
                "underlying_may_be_calendar_stub": False,
                "a_track_autobind_forbidden": True,
                "mapping_target": mapping_target,
                "regime_hypothesis": str(bj.get("byungjeung_state") or "watch"),
                "machine_readables": dict(mapping.get("machine_readables") or {}),
                "market_sasang_lens_snapshot": {
                    "state_vector_sasang_softmax": lens.get("state_vector_sasang_softmax"),
                    "fusion_bridge": fusion,
                    "veto": lens.get("veto"),
                    "uncertainty": lens.get("uncertainty"),
                },
            }
        )

    meta = {
        "schema": "btrack_market_sasang_per_date_manifest_v1",
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "research_only": True,
        "csv_path": str(csv_path.relative_to(ROOT)).replace("\\", "/")
        if csv_path.is_relative_to(ROOT)
        else str(csv_path),
        "date_from": df,
        "date_to": dt,
        "n_rows": len(out),
        "date_min": out[0]["eval_date"] if out else None,
        "date_max": out[-1]["eval_date"] if out else None,
        "output_jsonl": str(DEFAULT_OUT.relative_to(ROOT)).replace("\\", "/"),
        "note_ko": "market_psych v2 + market_sasang lens per trading day; calendar stub 대체 humanist sasang 입력.",
    }
    return out, meta


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--csv", type=Path, default=DEFAULT_CSV)
    ap.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    ap.add_argument("--policy", type=Path, default=DEFAULT_POLICY)
    ap.add_argument("--date-from", type=str, default="2026-01-01")
    ap.add_argument("--date-to", type=str, default="2026-06-08")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--manifest-out", type=Path, default=DEFAULT_MANIFEST_OUT)
    ap.add_argument(
        "--refresh-market-psych-csv",
        action="store_true",
        help="Run build_market_psychology_kospi_from_yfinance_v2.py before mapping.",
    )
    args = ap.parse_args(argv)

    if args.refresh_market_psych_csv:
        import subprocess

        rc = subprocess.call(
            [sys.executable, str(ROOT / "scripts/build_market_psychology_kospi_from_yfinance_v2.py"), "--days", "400"],
            cwd=str(ROOT),
        )
        if rc != 0:
            print("market psych csv refresh failed", file=sys.stderr)
            return rc

    if not args.csv.is_file():
        print(f"Missing csv: {args.csv} (try --refresh-market-psych-csv)", file=sys.stderr)
        return 1

    rows, meta = build_market_sasang_per_date_rows(
        csv_path=args.csv,
        manifest_path=args.manifest,
        policy_path=args.policy,
        date_from=args.date_from,
        date_to=args.date_to,
    )
    meta["output_jsonl"] = str(args.out.relative_to(ROOT)).replace("\\", "/") if args.out.is_relative_to(ROOT) else str(args.out)
    _write_jsonl(rows, args.out)
    args.manifest_out.parent.mkdir(parents=True, exist_ok=True)
    args.manifest_out.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"WROTE: {args.out.resolve()} rows={len(rows)} range={meta.get('date_min')}..{meta.get('date_max')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
