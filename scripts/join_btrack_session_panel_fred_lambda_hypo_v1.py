#!/usr/bin/env python3
"""[HYPO][NON_GATING] Join session panel dates with Vault FRED macro lambda(t) + gradient."""
from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PANEL = ROOT / "reports/btrack_session_panel_wide_prophecy_weather_20260612_obs.csv"
DEFAULT_MACRO = Path("G:/공유 드라이브/MKM_DATA_VAULT/data/macro_alerts/sgp_history_master_real.csv")
DEFAULT_OUT = ROOT / "reports/btrack_session_panel_fred_lambda_join_hypo_v1_latest.json"
SCHEMA = "btrack_session_panel_fred_lambda_join_hypo_v1"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_macro(path: Path) -> dict[str, dict[str, Any]]:
    if not path.is_file():
        return {}
    out: dict[str, dict[str, Any]] = {}
    with path.open(encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            dk = str(row.get("") or row.get("date") or "").strip()[:10]
            if len(dk) != 10 and row:
                dk = str(next(iter(row.values())) or "")[:10]
            if len(dk) != 10:
                continue
            entry: dict[str, Any] = {"date": dk}
            for col in ("S", "L", "K", "M", "lambda_t", "gradient", "alert_level", "z_score"):
                raw = row.get(col)
                if raw is None or str(raw).strip() == "":
                    continue
                try:
                    entry[col] = float(raw)
                except (TypeError, ValueError):
                    entry[col] = str(raw).strip()
            out[dk] = entry
    return out


def _read_panel_dates(path: Path, date_col: str) -> list[str]:
    text = path.read_text(encoding="utf-8-sig")
    r = csv.DictReader(text.splitlines())
    if not r.fieldnames:
        return []
    resolved = date_col
    for h in r.fieldnames:
        if h.strip().lower() == date_col.strip().lower():
            resolved = h
            break
    dates: list[str] = []
    for row in r:
        dk = str(row.get(resolved) or "")[:10]
        if len(dk) == 10:
            dates.append(dk)
    return sorted(set(dates))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--panel-csv", type=Path, default=DEFAULT_PANEL)
    ap.add_argument("--panel-date-col", default="session_local_date")
    ap.add_argument("--macro-csv", type=Path, default=DEFAULT_MACRO)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    panel_path = args.panel_csv if args.panel_csv.is_absolute() else ROOT / args.panel_csv
    macro_path = args.macro_csv
    out_path = args.output if args.output.is_absolute() else ROOT / args.output

    if not panel_path.is_file():
        raise SystemExit(f"missing panel: {panel_path}")
    if not macro_path.is_file():
        raise SystemExit(f"missing macro csv: {macro_path}")

    dates = _read_panel_dates(panel_path, args.panel_date_col)
    macro = _load_macro(macro_path)

    rows: list[dict[str, Any]] = []
    n_hit = 0
    for dk in dates:
        m = macro.get(dk)
        if m:
            n_hit += 1
        rows.append({"session_local_date": dk, "macro": m, "macro_present": m is not None})

    out = {
        "schema": SCHEMA,
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "gating": "[NON_GATING]",
        "hypothesis_tag": "[HYPO]",
        "inputs": {
            "panel_csv": str(panel_path.relative_to(ROOT)).replace("\\", "/"),
            "macro_csv": str(macro_path),
            "n_panel_dates": len(dates),
            "n_macro_joined": n_hit,
            "join_rate": round(n_hit / len(dates), 6) if dates else None,
        },
        "rows": rows,
        "boundary_ack": "FRED lambda join is observation-only; not live regime trigger or Track A gate.",
        "track_wall": {"auto_bridge_to_a_track": False, "live_trading_trigger": False},
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {out_path} join_rate={out['inputs']['join_rate']} n={len(dates)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
