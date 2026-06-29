#!/usr/bin/env python3
"""[HYPO][NON_GATING] Probe Vault macro CSV freshness + optional FRED API live tail."""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib import parse, request

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MACRO = Path("G:/공유 드라이브/MKM_DATA_VAULT/data/macro_alerts/sgp_history_master_real.csv")
DEFAULT_OUT = ROOT / "reports/rq025_macro_fred_freshness_probe_v1_latest.json"
SCHEMA = "rq025_macro_fred_freshness_probe_v1"
FRED_SERIES = ("UNRATE", "DGS10", "DTWEXBGS", "NASDAQCOM")


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_dotenv() -> None:
    env_path = ROOT / ".env"
    if not env_path.is_file():
        return
    try:
        from dotenv import load_dotenv

        load_dotenv(env_path, override=True)
    except ImportError:
        pass


def _vault_tail(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {"present": False, "max_date": None, "n_rows": 0}
    dates: list[str] = []
    with path.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    for row in rows:
        dk = str(row.get("") or row.get("date") or "").strip()[:10]
        if len(dk) != 10 and row:
            dk = str(next(iter(row.values())) or "")[:10]
        if len(dk) == 10:
            dates.append(dk)
    return {
        "present": True,
        "path": str(path),
        "n_rows": len(rows),
        "min_date": min(dates) if dates else None,
        "max_date": max(dates) if dates else None,
    }


def _fred_latest(api_key: str, series_id: str) -> dict[str, Any]:
    q = parse.urlencode(
        {
            "series_id": series_id,
            "api_key": api_key,
            "file_type": "json",
            "sort_order": "desc",
            "limit": 5,
        }
    )
    url = f"https://api.stlouisfed.org/fred/series/observations?{q}"
    req = request.Request(url=url, method="GET")
    with request.urlopen(req, timeout=20) as resp:
        doc = json.loads(resp.read().decode("utf-8"))
    obs = doc.get("observations") if isinstance(doc, dict) else None
    if not isinstance(obs, list):
        return {"series_id": series_id, "ok": False, "error": "no_observations"}
    for row in obs:
        if not isinstance(row, dict):
            continue
        d = str(row.get("date") or "")[:10]
        v = str(row.get("value") or "").strip()
        if d and v and v != ".":
            try:
                return {"series_id": series_id, "ok": True, "date": d, "value": float(v)}
            except ValueError:
                continue
    return {"series_id": series_id, "ok": False, "error": "no_finite_value"}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--macro-csv", type=Path, default=DEFAULT_MACRO)
    ap.add_argument("--target-date", default="2026-06-11", help="Compare freshness vs this date")
    ap.add_argument("--skip-fred-api", action="store_true")
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args(argv)

    _load_dotenv()
    target = str(args.target_date)[:10]
    vault = _vault_tail(args.macro_csv)
    gap_days = None
    if vault.get("max_date") and target:
        try:
            d0 = datetime.strptime(str(vault["max_date"])[:10], "%Y-%m-%d").date()
            d1 = datetime.strptime(target, "%Y-%m-%d").date()
            gap_days = (d1 - d0).days
        except ValueError:
            gap_days = None

    fred_probe: dict[str, Any] = {"attempted": False, "api_key_present": False, "series": []}
    if not args.skip_fred_api:
        key = os.environ.get("FRED_API_KEY", "").strip()
        fred_probe["api_key_present"] = bool(key)
        if key:
            fred_probe["attempted"] = True
            for sid in FRED_SERIES:
                try:
                    fred_probe["series"].append(_fred_latest(key, sid))
                except Exception as exc:  # noqa: BLE001
                    fred_probe["series"].append(
                        {"series_id": sid, "ok": False, "error": str(exc)[:200]}
                    )
            ok_dates = [s["date"] for s in fred_probe["series"] if s.get("ok") and s.get("date")]
            fred_probe["fred_max_obs_date"] = max(ok_dates) if ok_dates else None

    vault_stale = gap_days is not None and gap_days > 7
    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "gating": "[NON_GATING]",
        "rq_id": "RQ-025",
        "target_date": target,
        "vault_macro": vault,
        "gap_days_vault_to_target": gap_days,
        "vault_stale_vs_target": vault_stale,
        "fred_live_probe": fred_probe,
        "verdict": {
            "vault_refresh_required": vault_stale,
            "ffill_substitute_only": vault_stale,
            "note": "Does not mutate Vault CSV; live FRED is probe-only.",
        },
        "track_wall": {
            "track_a_auto_merge": False,
            "oracle_promotion": False,
            "live_trading": False,
        },
    }
    out_path = args.output if args.output.is_absolute() else ROOT / args.output
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"WROTE: {out_path} vault_max={vault.get('max_date')} gap_days={gap_days} "
        f"fred_api={fred_probe.get('fred_max_obs_date')}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
