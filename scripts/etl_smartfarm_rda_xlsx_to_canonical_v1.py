#!/usr/bin/env python3
"""ETL for RDA smartfarm public soil/weather XLSX package.

Input layout (default):
  data/smartfarm_rda_extract_v1/데이터제공/
    기상/농업기상 시간자료(2023년~2026년).xlsx
    토양/토양검정화학성상세정보(2023).xlsx
    토양/토양검정화학성상세정보(2024).xlsx
    토양/토양검정화학성상세정보(2025).xlsx
    토양/토양검정화학성상세정보(2026).xlsx

Outputs:
  - agmet_hourly_canonical.(csv|parquet)
  - soil_test_canonical.(csv|parquet)
  - etl_summary.json
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import pandas as pd


KST_TZ = "Asia/Seoul"

WEATHER_RENAME_MAP = {
    "지점명": "agmet_station_name",
    "일시": "agmet_local_hour_id",
    "온도": "air_temp_c",
    "습도": "relative_humidity_pct",
    "일사량": "solar_radiation",
    "강수량": "precip_mm_hourly",
}

SOIL_RENAME_MAP = {
    "시료채취년도": "sample_year",
    "토양검정일": "soil_test_date",
    "경지구분코드": "land_use_code",
    "대상지 지번주소": "parcel_address",
    "지번코드": "pnu_code",
    "유기물": "organic_matter",
    "유효인산": "available_phosphate",
    "유효규산": "available_silicate",
    "마그네슘": "exchangeable_mg",
    "칼륨": "exchangeable_k",
    "칼슘": "exchangeable_ca",
    "산도": "soil_ph",
    "산도 ": "soil_ph",  # 2024 workbook has trailing whitespace variant
    "전기전도도": "soil_ec_raw",
}


@dataclass
class EtlSummary:
    weather_sheets: list[str]
    weather_rows: int
    soil_files: list[str]
    soil_rows: int
    output_format: str


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert RDA smartfarm XLSX files into canonical weather/soil tables."
    )
    parser.add_argument(
        "--input-root",
        default="data/smartfarm_rda_extract_v1/데이터제공",
        help="Directory containing 기상/ and 토양/ folders.",
    )
    parser.add_argument(
        "--output-dir",
        default="data/smartfarm_rda_extract_v1/out",
        help="Directory for canonical output tables.",
    )
    parser.add_argument(
        "--output-format",
        default="csv",
        choices=("csv", "parquet"),
        help="Write output as csv or parquet (csv default for portability).",
    )
    parser.add_argument(
        "--max-rows-per-sheet",
        type=int,
        default=None,
        help="Optional dev/smoke cap for weather rows per sheet.",
    )
    parser.add_argument(
        "--sample-soil-rows",
        type=int,
        default=None,
        help="Optional dev/smoke cap for each soil workbook.",
    )
    return parser.parse_args()


def _expect_exists(path: Path) -> Path:
    if not path.exists():
        raise FileNotFoundError(f"Required path not found: {path}")
    return path


def _normalize_weather_time_col(df: pd.DataFrame) -> pd.DataFrame:
    # Observed source format: 'YYYYMMDD  HH' (double-space before hour)
    normalized = (
        df["agmet_local_hour_id"]
        .astype(str)
        .str.strip()
        .str.replace(r"\s+", " ", regex=True)
    )
    df["agmet_local_hour_id"] = normalized
    dt = pd.to_datetime(normalized, format="%Y%m%d %H", errors="coerce")
    df["agmet_ts_local"] = dt.dt.tz_localize(KST_TZ, ambiguous="NaT", nonexistent="NaT")
    df["agmet_ts_utc"] = df["agmet_ts_local"].dt.tz_convert("UTC")
    return df


def _coerce_numeric(df: pd.DataFrame, columns: Iterable[str]) -> pd.DataFrame:
    for col in columns:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def _load_weather(weather_xlsx: Path, max_rows_per_sheet: int | None) -> tuple[pd.DataFrame, list[str]]:
    xls = pd.ExcelFile(weather_xlsx)
    frames: list[pd.DataFrame] = []
    for sheet in xls.sheet_names:
        df = pd.read_excel(
            weather_xlsx,
            sheet_name=sheet,
            nrows=max_rows_per_sheet,
        )
        df = df.rename(columns=WEATHER_RENAME_MAP)
        missing = sorted(set(WEATHER_RENAME_MAP.values()) - set(df.columns))
        if missing:
            raise ValueError(f"Weather sheet '{sheet}' missing expected columns: {missing}")
        df = _normalize_weather_time_col(df)
        df = _coerce_numeric(
            df,
            columns=(
                "air_temp_c",
                "relative_humidity_pct",
                "solar_radiation",
                "precip_mm_hourly",
            ),
        )
        df["source_sheet"] = sheet
        frames.append(df)
    out = pd.concat(frames, ignore_index=True)
    return out, list(xls.sheet_names)


def _load_soil_file(path: Path, sample_rows: int | None) -> pd.DataFrame:
    if "2025" in path.name:
        # 2025 workbook has duplicated Korean header row under English column names.
        df = pd.read_excel(path, skiprows=1, nrows=sample_rows)
    else:
        df = pd.read_excel(path, nrows=sample_rows)
    df = df.rename(columns=SOIL_RENAME_MAP)
    required = {
        "sample_year",
        "soil_test_date",
        "land_use_code",
        "parcel_address",
        "pnu_code",
        "soil_ph",
        "soil_ec_raw",
    }
    missing = sorted(required - set(df.columns))
    if missing:
        raise ValueError(f"Soil workbook '{path.name}' missing expected columns: {missing}")
    df["source_file"] = path.name
    return df


def _normalize_soil(df: pd.DataFrame) -> pd.DataFrame:
    if "soil_test_date" in df.columns:
        dt = pd.to_datetime(df["soil_test_date"].astype(str), format="%Y%m%d", errors="coerce")
        df["soil_test_date"] = dt.dt.date.astype("string")
    df = _coerce_numeric(
        df,
        columns=(
            "sample_year",
            "land_use_code",
            "pnu_code",
            "organic_matter",
            "available_phosphate",
            "available_silicate",
            "exchangeable_mg",
            "exchangeable_k",
            "exchangeable_ca",
            "soil_ph",
            "soil_ec_raw",
        ),
    )
    return df


def _write_table(df: pd.DataFrame, base_path_no_ext: Path, output_format: str) -> Path:
    if output_format == "parquet":
        out_path = base_path_no_ext.with_suffix(".parquet")
        df.to_parquet(out_path, index=False)
    else:
        out_path = base_path_no_ext.with_suffix(".csv")
        df.to_csv(out_path, index=False, encoding="utf-8-sig")
    return out_path


def main() -> int:
    args = _parse_args()
    input_root = _expect_exists(Path(args.input_root))
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    weather_xlsx = _expect_exists(input_root / "기상" / "농업기상 시간자료(2023년~2026년).xlsx")
    soil_dir = _expect_exists(input_root / "토양")
    soil_files = sorted(soil_dir.glob("토양검정화학성상세정보(*).xlsx"))
    if not soil_files:
        raise FileNotFoundError(f"No soil xlsx files found in: {soil_dir}")

    weather_df, sheets = _load_weather(weather_xlsx, args.max_rows_per_sheet)
    soil_frames = [_load_soil_file(path, args.sample_soil_rows) for path in soil_files]
    soil_df = _normalize_soil(pd.concat(soil_frames, ignore_index=True))

    weather_out = _write_table(weather_df, output_dir / "agmet_hourly_canonical", args.output_format)
    soil_out = _write_table(soil_df, output_dir / "soil_test_canonical", args.output_format)

    summary = EtlSummary(
        weather_sheets=sheets,
        weather_rows=len(weather_df),
        soil_files=[p.name for p in soil_files],
        soil_rows=len(soil_df),
        output_format=args.output_format,
    )
    summary_path = output_dir / "etl_summary.json"
    summary_path.write_text(
        json.dumps(
            {
                "schema": "smartfarm_rda_etl_summary_v1",
                "input_root": str(input_root),
                "weather_output": str(weather_out),
                "soil_output": str(soil_out),
                "summary": summary.__dict__,
                "notes": [
                    "2025 soil workbook loaded with skiprows=1 due to duplicated header row.",
                    "Column alias normalization applied: '산도 ' -> 'soil_ph'.",
                    "This ETL does not fabricate missing telemetry fields (soil_moisture_pct, soil_temp_c, comm_ok).",
                ],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print(f"[ok] weather rows: {len(weather_df):,} -> {weather_out}")
    print(f"[ok] soil rows: {len(soil_df):,} -> {soil_out}")
    print(f"[ok] summary: {summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

