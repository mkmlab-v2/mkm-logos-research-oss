#!/usr/bin/env python3
"""CSV → weather_ground_truth_row_v1 JSONL (B-track, [HYPO], calibration only)."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "docs/final/schemas/weather_ground_truth_row_v1.schema.json"
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _fingerprint(row: dict[str, Any]) -> str:
    payload = "|".join(
        [
            str(row.get("observation_date_local")),
            str(row.get("station_or_region_id")),
            f"{float(row.get('precip_mm_day', 0)):.4f}",
        ]
    )
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]
    return f"sha256:{digest}"


def _parse_date(raw: str, date_format: str) -> str:
    raw = raw.strip()
    for fmt in (date_format, "%Y-%m-%d", "%Y/%m/%d", "%Y%m%d", "%Y.%m.%d"):
        try:
            return datetime.strptime(raw, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    raise ValueError(f"unparseable date: {raw!r}")


def _validate_row(row: dict[str, Any]) -> None:
    if not SCHEMA_PATH.is_file():
        return
    try:
        from jsonschema import Draft202012Validator
    except ImportError:
        return
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator(schema).validate(row)


def _read_csv_rows(
    path: Path,
    *,
    encoding: str,
    delimiter: str,
    date_col: str,
    precip_col: str,
    date_format: str,
    max_rows: int | None,
) -> list[dict[str, str]]:
    with path.open("r", encoding=encoding, newline="") as fh:
        reader = csv.DictReader(fh, delimiter=delimiter)
        if reader.fieldnames is None:
            raise ValueError("csv has no header row")
        out: list[dict[str, str]] = []
        for row in reader:
            if date_col not in row or precip_col not in row:
                raise ValueError(f"missing columns date={date_col!r} precip={precip_col!r}")
            out.append(row)
            if max_rows is not None and len(out) >= max_rows:
                break
        return out


def convert_csv(
    *,
    input_csv: Path,
    output_jsonl: Path,
    threshold_mm: float,
    station_id: str,
    timezone_name: str,
    date_col: str | None,
    precip_col: str | None,
    date_format: str,
    auto_columns: bool,
    strict_schema: bool,
    max_rows: int | None,
    dataset_name: str,
) -> int:
    encoding = "utf-8-sig"
    delimiter = ","
    if auto_columns or date_col is None or precip_col is None:
        from weather_csv_sniff_v1 import sniff_csv

        sniff = sniff_csv(input_csv)
        encoding = sniff["encoding"]
        delimiter = sniff["delimiter"]
        date_col = date_col or sniff["date_col"]
        precip_col = precip_col or sniff["precip_col"]
        date_format = sniff.get("date_format") or date_format
    assert date_col and precip_col

    rows_in = _read_csv_rows(
        input_csv,
        encoding=encoding,
        delimiter=delimiter,
        date_col=date_col,
        precip_col=precip_col,
        date_format=date_format,
        max_rows=max_rows,
    )
    output_jsonl.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    with output_jsonl.open("w", encoding="utf-8", newline="\n") as out:
        for src in rows_in:
            precip_raw = (src.get(precip_col) or "").strip()
            if precip_raw in ("", "-", "NA", "null", "None"):
                precip_mm = 0.0
            else:
                precip_mm = float(precip_raw)
            obs_date = _parse_date(src.get(date_col, ""), date_format)
            binary = precip_mm > threshold_mm
            doc: dict[str, Any] = {
                "schema": "weather_ground_truth_row_v1",
                "observation_date_local": obs_date,
                "timezone": timezone_name,
                "station_or_region_id": station_id,
                "precip_mm_day": round(precip_mm, 4),
                "precip_binary_gt_0_1mm": binary,
                "temp_max_c": None,
                "source": {
                    "retrieved_at_utc": _utc_now(),
                    "dataset_name": dataset_name,
                    "input_csv": str(input_csv),
                },
            }
            doc["row_fingerprint"] = _fingerprint(doc)
            if strict_schema:
                _validate_row(doc)
            out.write(json.dumps(doc, ensure_ascii=False) + "\n")
            written += 1
    print(f"WROTE: {output_jsonl} rows={written}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--threshold-mm", type=float, default=0.1)
    ap.add_argument("--station-id", default="seoul_asos_108")
    ap.add_argument("--timezone", default="Asia/Seoul")
    ap.add_argument("--date-col", default=None)
    ap.add_argument("--precip-col", default=None)
    ap.add_argument("--date-format", default="%Y-%m-%d")
    ap.add_argument("--auto-columns", action="store_true")
    ap.add_argument("--strict-schema", action="store_true")
    ap.add_argument("--max-rows", type=int, default=None)
    ap.add_argument("--dataset-name", default="csv_import_v1")
    ns = ap.parse_args()
    if not ns.input.is_file():
        print(f"missing input: {ns.input}", file=sys.stderr)
        return 2
    try:
        return convert_csv(
            input_csv=ns.input,
            output_jsonl=ns.output,
            threshold_mm=ns.threshold_mm,
            station_id=ns.station_id,
            timezone_name=ns.timezone,
            date_col=ns.date_col,
            precip_col=ns.precip_col,
            date_format=ns.date_format,
            auto_columns=ns.auto_columns,
            strict_schema=ns.strict_schema,
            max_rows=ns.max_rows,
            dataset_name=ns.dataset_name,
        )
    except (ValueError, KeyError) as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
