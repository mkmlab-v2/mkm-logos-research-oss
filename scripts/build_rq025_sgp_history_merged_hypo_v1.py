#!/usr/bin/env python3
"""[HYPO] Merge Vault sgp_history with local trading-day extension (carry-forward tail).

Does NOT write to G: Vault. Extension rows are tagged macro_extension=carry_forward_vault_tail.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_VAULT = Path("G:/공유 드라이브/MKM_DATA_VAULT/data/macro_alerts/sgp_history_master_real.csv")
DEFAULT_OUT_CSV = ROOT / "reports/rq025_sgp_history_merged_hypo_v1.csv"
DEFAULT_OUT_META = ROOT / "reports/rq025_sgp_history_merged_hypo_v1_latest.json"
SCHEMA = "rq025_sgp_history_merged_hypo_v1"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_vault(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    if not path.is_file():
        return [], []
    with path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        fields = list(reader.fieldnames or [])
        rows = [dict(r) for r in reader]
    return fields, rows


def _row_date(row: dict[str, str]) -> str:
    dk = str(row.get("") or row.get("date") or "").strip()[:10]
    if len(dk) != 10 and row:
        dk = str(next(iter(row.values())) or "")[:10]
    return dk if len(dk) == 10 else ""


def _krx_weekdays(d0: date, d1: date) -> list[str]:
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from scripts.kospi_krx_calendar_v1 import krx_trading_days

    return krx_trading_days(d0, d1)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--vault-csv", type=Path, default=DEFAULT_VAULT)
    ap.add_argument("--extend-to", default="2026-06-11", help="YYYY-MM-DD inclusive")
    ap.add_argument("--output-csv", type=Path, default=DEFAULT_OUT_CSV)
    ap.add_argument("--output-meta", type=Path, default=DEFAULT_OUT_META)
    args = ap.parse_args(argv)

    fields, rows = _read_vault(args.vault_csv)
    if not rows:
        raise SystemExit(f"missing or empty vault csv: {args.vault_csv}")

    dated = [( _row_date(r), r) for r in rows]
    dated = [(d, r) for d, r in dated if d]
    if not dated:
        raise SystemExit("no parseable dates in vault csv")
    dated.sort(key=lambda x: x[0])
    max_vault = dated[-1][0]
    tail_row = dict(dated[-1][1])

    d_end = date.fromisoformat(str(args.extend_to)[:10])
    d_start = datetime.strptime(max_vault, "%Y-%m-%d").date() + timedelta(days=1)
    extension_dates: list[str] = []
    if d_start <= d_end:
        extension_dates = [d for d in _krx_weekdays(d_start, d_end) if d > max_vault]

    out_rows = [r for _, r in dated]
    for dk in extension_dates:
        ext = dict(tail_row)
        if "" in fields or fields[0] == "":
            ext[""] = dk
        if "date" in fields:
            ext["date"] = dk
        elif fields:
            ext[fields[0]] = dk
        ext["macro_extension"] = "carry_forward_vault_tail"
        ext["macro_extension_from"] = max_vault
        out_rows.append(ext)

    out_csv = args.output_csv if args.output_csv.is_absolute() else ROOT / args.output_csv
    out_meta = args.output_meta if args.output_meta.is_absolute() else ROOT / args.output_meta
    out_csv.parent.mkdir(parents=True, exist_ok=True)

    write_fields = list(fields)
    for extra in ("macro_extension", "macro_extension_from"):
        if extra not in write_fields:
            write_fields.append(extra)

    with out_csv.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=write_fields, extrasaction="ignore")
        w.writeheader()
        for r in out_rows:
            w.writerow(r)

    meta: dict[str, Any] = {
        "schema": SCHEMA,
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "gating": "[NON_GATING]",
        "vault_csv": str(args.vault_csv),
        "vault_max_date": max_vault,
        "extend_to": str(args.extend_to)[:10],
        "n_vault_rows": len(dated),
        "n_extension_rows": len(extension_dates),
        "n_total_rows": len(out_rows),
        "merged_csv": str(out_csv.relative_to(ROOT)).replace("\\", "/"),
        "boundary_ack": "Extension is carry-forward only; not Vault overwrite or lambda recompute.",
        "track_wall": {
            "track_a_auto_merge": False,
            "oracle_promotion": False,
            "live_trading": False,
        },
    }
    out_meta.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {out_csv} vault_max={max_vault} ext={len(extension_dates)} total={len(out_rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
