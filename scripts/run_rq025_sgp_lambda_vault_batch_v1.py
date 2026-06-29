#!/usr/bin/env python3
"""[HYPO] Extend Vault sgp_history via KOSPI-calibrated S/L/K/M + lambda recompute (append-only).

Not the off-repo production sgp batch. Uses fitted proxy from vault history + KOSPI OHLCV.
Default: dry-run preview under reports/. Use --apply-vault for G: append (backup first).
"""
from __future__ import annotations

import argparse
import csv
import json
import shutil
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_VAULT = Path("G:/공유 드라이브/MKM_DATA_VAULT/data/macro_alerts/sgp_history_master_real.csv")
DEFAULT_KOSPI = ROOT / "research/market_data/kospi_daily_external_yf.csv"
DEFAULT_OUT = ROOT / "reports/rq025_sgp_lambda_vault_batch_v1_latest.json"
DEFAULT_PREVIEW = ROOT / "reports/rq025_sgp_lambda_vault_batch_preview_v1.csv"
SCHEMA = "rq025_sgp_lambda_vault_batch_v1"
FIELDS = ("", "S", "L", "K", "M", "lambda_t", "lambda_ma", "lambda_std", "z_score", "gradient", "alert_level")


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_vault(path: Path) -> tuple[list[str], list[dict[str, str]]]:
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


def _finite_row(row: dict[str, str]) -> bool:
    keys = ("S", "L", "K", "M", "lambda_t", "lambda_ma", "lambda_std", "z_score", "gradient")
    for k in keys:
        try:
            float(row[k])
        except (TypeError, ValueError, KeyError):
            return False
    return bool(_row_date(row))


def _load_kospi_close(path: Path) -> dict[str, float]:
    if not path.is_file():
        return {}
    out: dict[str, float] = {}
    with path.open(encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            dk = str(row.get("date") or row.get("Date") or row.get("eval_date") or "")[:10]
            close = row.get("close") or row.get("Close") or row.get("adj_close")
            try:
                if len(dk) == 10:
                    out[dk] = float(close)
            except (TypeError, ValueError):
                continue
    return out


def _krx_days(d0: date, d1: date) -> list[str]:
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from scripts.kospi_krx_calendar_v1 import krx_trading_days

    return krx_trading_days(d0, d1)


def _fit_models(rows: list[dict[str, str]], kospi: dict[str, float]) -> dict[str, Any]:
    clean = [r for r in rows if _finite_row(r)]
    S = np.array([float(r["S"]) for r in clean])
    L = np.array([float(r["L"]) for r in clean])
    K = np.array([float(r["K"]) for r in clean])
    M = np.array([float(r["M"]) for r in clean])
    lt = np.array([float(r["lambda_t"]) for r in clean])
    X = np.column_stack([S, L, K, M, np.ones(len(clean))])
    coef, _, _, _ = np.linalg.lstsq(X, lt, rcond=None)

    aligned: list[tuple[float, float, float, float, float]] = []
    for i in range(1, len(clean)):
        d0 = _row_date(clean[i - 1])
        d1 = _row_date(clean[i])
        c0, c1 = kospi.get(d0), kospi.get(d1)
        if c0 and c1 and c0 > 0:
            ret = (c1 / c0) - 1.0
            aligned.append(
                (
                    ret,
                    float(clean[i]["S"]) - float(clean[i - 1]["S"]),
                    float(clean[i]["L"]) - float(clean[i - 1]["L"]),
                    float(clean[i]["K"]) - float(clean[i - 1]["K"]),
                    float(clean[i]["M"]) - float(clean[i - 1]["M"]),
                )
            )
    if len(aligned) < 30:
        slkm_delta = {"ds_ret": 2.0, "dl_ret": -0.5, "dk": -1e-5, "dm": -1e-5}
    else:
        arr = np.array(aligned)
        ret = arr[:, 0]
        slkm_delta = {
            "ds_ret": float(np.linalg.lstsq(np.column_stack([ret, np.ones(len(ret))]), arr[:, 1], rcond=None)[0][0]),
            "dl_ret": float(np.linalg.lstsq(np.column_stack([ret, np.ones(len(ret))]), arr[:, 2], rcond=None)[0][0]),
            "dk": float(np.median(arr[:, 3])),
            "dm": float(np.median(arr[:, 4])),
        }

    return {"lambda_coef_slkm_b": [float(x) for x in coef], "slkm_delta": slkm_delta, "n_fit_rows": len(clean)}


def _alert_from_z(z: float) -> str:
    az = abs(z)
    if z >= 3.0:
        return "L3"
    if az >= 2.0:
        return "L2"
    if az >= 1.0:
        return "L1"
    return "L0"


def _build_extension_rows(
    *,
    base_rows: list[dict[str, str]],
    new_dates: list[str],
    kospi: dict[str, float],
    models: dict[str, Any],
) -> list[dict[str, str]]:
    if not new_dates:
        return []
    coef = np.array(models["lambda_coef_slkm_b"], dtype=float)
    delta = models["slkm_delta"]
    hist_lt = [float(r["lambda_t"]) for r in base_rows if _finite_row(r)]
    prev = dict(base_rows[-1])
    out: list[dict[str, str]] = []
    for dk in new_dates:
        prev_d = _row_date(prev)
        c0, c1 = kospi.get(prev_d), kospi.get(dk)
        ret = ((c1 / c0) - 1.0) if c0 and c1 and c0 > 0 else 0.0
        s = float(prev["S"]) + float(delta["ds_ret"]) * ret
        l = float(prev["L"]) + float(delta["dl_ret"]) * ret
        k = float(prev["K"]) + float(delta["dk"])
        m = float(prev["M"]) + float(delta["dm"])
        lam = float(coef[0] * s + coef[1] * l + coef[2] * k + coef[3] * m + coef[4])
        hist_lt.append(lam)
        ma_win = hist_lt[-30:]
        ma = sum(ma_win) / len(ma_win)
        std_win = hist_lt[-60:] if len(hist_lt) >= 60 else hist_lt
        std = float(np.std(np.array(std_win, dtype=float)))
        if std < 1e-9:
            std = 1e-9
        z = (lam - float(np.mean(std_win))) / std
        grad = lam - float(prev["lambda_t"])
        row = {
            "": dk,
            "S": f"{s:.8f}",
            "L": f"{l:.8f}",
            "K": f"{k:.8f}",
            "M": f"{m:.8f}",
            "lambda_t": f"{lam:.7f}",
            "lambda_ma": f"{ma}",
            "lambda_std": f"{std}",
            "z_score": f"{z}",
            "gradient": f"{grad}",
            "alert_level": _alert_from_z(z),
        }
        out.append(row)
        prev = row
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--vault-csv", type=Path, default=DEFAULT_VAULT)
    ap.add_argument("--kospi-csv", type=Path, default=DEFAULT_KOSPI)
    ap.add_argument("--extend-to", default=None, help="YYYY-MM-DD; default today UTC")
    ap.add_argument("--apply-vault", action="store_true", help="Append new rows to Vault (backup first)")
    ap.add_argument("--preview-csv", type=Path, default=DEFAULT_PREVIEW)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args(argv)

    if not args.vault_csv.is_file():
        raise SystemExit(f"vault csv missing: {args.vault_csv}")

    extend_to = (args.extend_to or datetime.now(timezone.utc).strftime("%Y-%m-%d"))[:10]
    fields, rows = _read_vault(args.vault_csv)
    dated = sorted((_row_date(r), r) for r in rows if _row_date(r))
    if not dated:
        raise SystemExit("no dated rows in vault csv")
    max_vault = dated[-1][0]
    base_rows = [r for _, r in dated]

    kospi = _load_kospi_close(args.kospi_csv if args.kospi_csv.is_absolute() else ROOT / args.kospi_csv)
    models = _fit_models(base_rows, kospi)

    d_start = datetime.strptime(max_vault, "%Y-%m-%d").date() + timedelta(days=1)
    d_end = date.fromisoformat(extend_to)
    new_dates = [d for d in _krx_days(d_start, d_end) if d > max_vault]
    extension = _build_extension_rows(
        base_rows=base_rows, new_dates=new_dates, kospi=kospi, models=models
    )

    preview_path = args.preview_csv if args.preview_csv.is_absolute() else ROOT / args.preview_csv
    preview_path.parent.mkdir(parents=True, exist_ok=True)
    with preview_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(FIELDS))
        w.writeheader()
        for r in extension:
            w.writerow(r)

    applied = False
    backup_path: str | None = None
    if args.apply_vault and extension:
        backup_dir = ROOT / "reports" / "backups"
        backup_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        backup = backup_dir / f"sgp_history_master_real_{stamp}.csv"
        shutil.copy2(args.vault_csv, backup)
        backup_path = str(backup.relative_to(ROOT)).replace("\\", "/")
        write_fields = fields if fields else list(FIELDS)
        with args.vault_csv.open("a", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=write_fields, extrasaction="ignore")
            for r in extension:
                w.writerow(r)
        applied = True

    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "gating": "[NON_GATING]",
        "rq_id": "RQ-025",
        "implementation": "rq025_kospi_calibrated_proxy_v1",
        "vault_csv": str(args.vault_csv),
        "vault_max_before": max_vault,
        "extend_to": extend_to,
        "n_new_rows": len(extension),
        "new_date_min": extension[0][""] if extension else None,
        "new_date_max": extension[-1][""] if extension else None,
        "preview_csv": str(preview_path.relative_to(ROOT)).replace("\\", "/"),
        "models": models,
        "apply": {
            "requested": bool(args.apply_vault),
            "applied": applied,
            "mode": "append_only",
            "backup_csv": backup_path,
        },
        "boundary_ack": (
            "Proxy recompute from KOSPI + vault-fitted coefficients; "
            "not certified upstream sgp lambda batch."
        ),
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
        f"WROTE: {out_path} new_rows={len(extension)} applied={applied} "
        f"max_before={max_vault} max_after={extension[-1][''] if extension else max_vault}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
