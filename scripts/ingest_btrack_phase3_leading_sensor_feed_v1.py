#!/usr/bin/env python3
"""Ingest CSV/JSONL external feeds into canonical Phase 3 leading-sensor JSONL (research_only).

CSV columns (header required):
  eval_date, signed_flow_z [, level_pctile] [, raw_*]

JSONL: rows matching btrack_phase3_leading_sensor_row_v1 (minimal validation).
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "docs/final/artifacts/btrack_phase3_leading_sensors_manifest_v1.json"
DEFAULT_OUT_DIR = ROOT / "data/btrack/phase3_leading_sensors"
DEFAULT_REPORT = ROOT / "reports/btrack_phase3_leading_sensor_ingest_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_manifest(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _sensor_map(manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for s in manifest.get("sensors") or []:
        if isinstance(s, dict) and s.get("sensor_id"):
            out[str(s["sensor_id"])] = s
    return out


def _norm_date(cell: str) -> str | None:
    s = str(cell).strip()[:10]
    if len(s) == 10 and s[4] == "-" and s[7] == "-":
        return s
    return None


def _row_from_csv(sensor_id: str, row: dict[str, str]) -> dict[str, Any] | None:
    ed = _norm_date(row.get("eval_date", ""))
    if not ed:
        return None
    try:
        z = float(row.get("signed_flow_z", ""))
    except (TypeError, ValueError):
        return None
    lp_raw = row.get("level_pctile", "")
    try:
        lp = float(lp_raw) if str(lp_raw).strip() else max(0.05, min(0.95, 0.5 + z * 0.25))
    except (TypeError, ValueError):
        lp = max(0.05, min(0.95, 0.5 + z * 0.25))
    feats: dict[str, Any] = {"signed_flow_z": round(z, 6), "level_pctile": round(lp, 6)}
    for k in ("raw_funding_rate", "raw_long_short_ratio", "raw_netflow_btc"):
        if k in row and str(row[k]).strip():
            try:
                feats[k] = float(row[k])
            except ValueError:
                pass
    return {
        "eval_date": ed,
        "sensor_id": sensor_id,
        "hypothesis_tier": "B",
        "boundary_ack": True,
        "research_only": True,
        "data_quality": "measured_csv",
        "features": feats,
        "source": "ingest_btrack_phase3_leading_sensor_feed_v1",
        "note": "Operator CSV ingest; direction promotion not implied.",
    }


def _read_csv(path: Path, sensor_id: str) -> tuple[list[dict[str, Any]], list[str]]:
    rows: list[dict[str, Any]] = []
    warns: list[str] = []
    with path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames or "eval_date" not in reader.fieldnames or "signed_flow_z" not in reader.fieldnames:
            warns.append("missing_required_columns:eval_date,signed_flow_z")
            return rows, warns
        for i, raw in enumerate(reader):
            o = _row_from_csv(sensor_id, {k: v or "" for k, v in raw.items()})
            if o is None:
                warns.append(f"skip_csv_line:{i + 2}")
                continue
            rows.append(o)
    return rows, warns


def _read_jsonl(path: Path, sensor_id: str) -> tuple[list[dict[str, Any]], list[str]]:
    rows: list[dict[str, Any]] = []
    warns: list[str] = []
    for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = line.strip()
        if not line:
            continue
        try:
            o = json.loads(line)
        except json.JSONDecodeError:
            warns.append(f"bad_json_line:{i}")
            continue
        if not isinstance(o, dict):
            continue
        o.setdefault("sensor_id", sensor_id)
        o.setdefault("hypothesis_tier", "B")
        o.setdefault("boundary_ack", True)
        o.setdefault("research_only", True)
        o.setdefault("data_quality", "measured_jsonl")
        if not _norm_date(str(o.get("eval_date", ""))):
            warns.append(f"skip_jsonl_line:{i}")
            continue
        feats = o.get("features") if isinstance(o.get("features"), dict) else {}
        if "signed_flow_z" not in feats:
            warns.append(f"skip_jsonl_no_z:{i}")
            continue
        rows.append(o)
    return rows, warns


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in sorted(rows, key=lambda r: str(r.get("eval_date"))):
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--sensor-id", required=True, help="Manifest sensor_id e.g. onchain_exchange_netflow")
    ap.add_argument("--input", type=Path, required=True, help="CSV or JSONL feed file")
    ap.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    ap.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    ap.add_argument(
        "--output-name",
        default="",
        help="Output filename under out-dir (default: {sensor_id}_measured.jsonl)",
    )
    ap.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = ap.parse_args(argv)

    if not args.input.is_file():
        print(f"MISSING input: {args.input}", file=sys.stderr)
        return 2
    manifest = _load_manifest(args.manifest)
    smap = _sensor_map(manifest)
    if args.sensor_id not in smap:
        print(f"Unknown sensor_id: {args.sensor_id}", file=sys.stderr)
        return 2

    suffix = args.input.suffix.lower()
    if suffix == ".csv":
        rows, warns = _read_csv(args.input, args.sensor_id)
    elif suffix in (".jsonl", ".ndjson"):
        rows, warns = _read_jsonl(args.input, args.sensor_id)
    else:
        print("Input must be .csv or .jsonl", file=sys.stderr)
        return 2

    if not rows:
        print("No valid rows ingested", file=sys.stderr)
        return 1

    out_name = args.output_name or f"{args.sensor_id}_measured.jsonl"
    out_path = args.out_dir / out_name
    _write_jsonl(out_path, rows)

    report = {
        "schema": "btrack_phase3_leading_sensor_ingest_v1",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "sensor_id": args.sensor_id,
        "input": str(args.input),
        "output": str(out_path),
        "n_rows": len(rows),
        "date_min": min(str(r["eval_date"]) for r in rows),
        "date_max": max(str(r["eval_date"]) for r in rows),
        "warnings": warns,
        "track_a_promotion": False,
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {out_path.resolve()} ({len(rows)} rows)")
    print(f"WROTE: {args.report.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
