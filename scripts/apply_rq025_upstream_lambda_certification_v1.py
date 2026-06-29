#!/usr/bin/env python3
"""[HYPO] Upstream λ certification gate — diff proxy tail vs human certified CSV; optional Vault replace."""
from __future__ import annotations

import argparse
import csv
import json
import math
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_VAULT = Path("G:/공유 드라이브/MKM_DATA_VAULT/data/macro_alerts/sgp_history_master_real.csv")
DEFAULT_BATCH_LOG = ROOT / "reports/rq025_sgp_lambda_vault_batch_v1_latest.json"
DEFAULT_PREVIEW = ROOT / "reports/rq025_sgp_lambda_vault_batch_preview_v1.csv"
DEFAULT_INBOX = ROOT / "reports/inbox/rq025_upstream_sgp_lambda_certified_v1.csv"
DEFAULT_OUT = ROOT / "reports/rq025_upstream_lambda_certification_v1_latest.json"
SCHEMA = "rq025_upstream_lambda_certification_v1"
NUMERIC_KEYS = ("S", "L", "K", "M", "lambda_t", "lambda_ma", "lambda_std", "z_score", "gradient")


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(path)


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
    for k in NUMERIC_KEYS:
        try:
            float(row[k])
        except (TypeError, ValueError, KeyError):
            return False
    return bool(_row_date(row))


def _rows_by_date(rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    out: dict[str, dict[str, str]] = {}
    for r in rows:
        dk = _row_date(r)
        if dk:
            out[dk] = r
    return out


def _diff_rows(
    left: dict[str, dict[str, str]],
    right: dict[str, dict[str, str]],
    *,
    dates: list[str],
) -> dict[str, Any]:
    per_key_max: dict[str, float] = {k: 0.0 for k in NUMERIC_KEYS}
    compared = 0
    missing_left = 0
    missing_right = 0
    for dk in dates:
        a = left.get(dk)
        b = right.get(dk)
        if not a:
            missing_left += 1
            continue
        if not b:
            missing_right += 1
            continue
        compared += 1
        for k in NUMERIC_KEYS:
            try:
                per_key_max[k] = max(per_key_max[k], abs(float(a[k]) - float(b[k])))
            except (TypeError, ValueError):
                per_key_max[k] = math.inf
    return {
        "n_dates": len(dates),
        "n_compared": compared,
        "missing_left": missing_left,
        "missing_right": missing_right,
        "max_abs_delta_by_field": {k: (None if v == math.inf else round(v, 8)) for k, v in per_key_max.items()},
        "max_abs_delta_any": round(max(v for v in per_key_max.values() if v != math.inf), 8)
        if any(v != math.inf for v in per_key_max.values())
        else None,
    }


def _replace_tail(
    vault_rows: list[dict[str, str]],
    certified_by_date: dict[str, dict[str, str]],
    *,
    date_min: str,
    date_max: str,
) -> tuple[list[dict[str, str]], int]:
    replaced = 0
    out: list[dict[str, str]] = []
    for r in vault_rows:
        dk = _row_date(r)
        if date_min <= dk <= date_max and dk in certified_by_date:
            out.append(certified_by_date[dk])
            replaced += 1
        else:
            out.append(r)
    return out, replaced


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--vault-csv", type=Path, default=DEFAULT_VAULT)
    ap.add_argument("--batch-log-json", type=Path, default=DEFAULT_BATCH_LOG)
    ap.add_argument("--proxy-preview-csv", type=Path, default=DEFAULT_PREVIEW)
    ap.add_argument("--certified-csv", type=Path, default=DEFAULT_INBOX)
    ap.add_argument("--apply-vault", action="store_true", help="Replace proxy tail with certified rows (backup first)")
    ap.add_argument("--max-abs-delta-ok", type=float, default=1e-6, help="Gate: certified vs proxy max abs delta")
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args(argv)

    batch_log = _load_json(args.batch_log_json if args.batch_log_json.is_absolute() else ROOT / args.batch_log_json)
    d0 = str(batch_log.get("new_date_min") or "")[:10]
    d1 = str(batch_log.get("new_date_max") or "")[:10]
    if len(d0) != 10 or len(d1) != 10:
        raise SystemExit("batch log missing new_date_min/max")

    certified_path = args.certified_csv if args.certified_csv.is_absolute() else ROOT / args.certified_csv
    preview_path = args.proxy_preview_csv if args.proxy_preview_csv.is_absolute() else ROOT / args.proxy_preview_csv
    vault_path = args.vault_csv

    proxy_dates = [d for d in sorted(_rows_by_date(_read_vault(preview_path)[1]).keys()) if d0 <= d <= d1] if preview_path.is_file() else []

    status = "awaiting_certified_csv"
    certified_present = certified_path.is_file()
    vault_proxy_diff: dict[str, Any] | None = None
    certified_proxy_diff: dict[str, Any] | None = None
    certification_pass = False
    applied = False
    backup_path: str | None = None
    n_replaced = 0

    if vault_path.is_file() and preview_path.is_file():
        vault_by = _rows_by_date(_read_vault(vault_path)[1])
        preview_by = _rows_by_date(_read_vault(preview_path)[1])
        vault_proxy_diff = _diff_rows(vault_by, preview_by, dates=proxy_dates)

    if certified_present:
        _, cert_rows = _read_vault(certified_path)
        cert_by = {dk: r for dk, r in _rows_by_date(cert_rows).items() if _finite_row(r)}
        cert_dates = sorted(dk for dk in cert_by if d0 <= dk <= d1)
        if preview_path.is_file():
            preview_by = _rows_by_date(_read_vault(preview_path)[1])
            certified_proxy_diff = _diff_rows(cert_by, preview_by, dates=cert_dates or proxy_dates)
        max_delta = float(certified_proxy_diff.get("max_abs_delta_any") or 0) if certified_proxy_diff else 0.0
        coverage_ok = (
            len(cert_dates) >= len(proxy_dates)
            and certified_proxy_diff is not None
            and int(certified_proxy_diff.get("missing_right") or 0) == 0
        )
        certification_pass = bool(coverage_ok)
        if certification_pass and max_delta <= float(args.max_abs_delta_ok):
            status = "certified_present_matches_proxy_within_tol"
        elif certification_pass:
            status = "certified_present_differs_from_proxy"
        else:
            status = "certified_present_incomplete_coverage"

        if args.apply_vault and certification_pass and vault_path.is_file():
            if not certified_present:
                raise SystemExit("apply requires certified csv")
            fields, vault_rows = _read_vault(vault_path)
            new_rows, n_replaced = _replace_tail(vault_rows, cert_by, date_min=d0, date_max=d1)
            backup_dir = ROOT / "reports" / "backups"
            backup_dir.mkdir(parents=True, exist_ok=True)
            stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            backup = backup_dir / f"sgp_history_master_real_pre_cert_{stamp}.csv"
            shutil.copy2(vault_path, backup)
            backup_path = str(backup.relative_to(ROOT)).replace("\\", "/")
            write_fields = fields if fields else list(cert_rows[0].keys()) if cert_rows else []
            with vault_path.open("w", encoding="utf-8", newline="") as f:
                w = csv.DictWriter(f, fieldnames=write_fields, extrasaction="ignore")
                w.writeheader()
                for r in new_rows:
                    w.writerow(r)
            applied = True
            status = "certified_applied_to_vault"
    else:
        certified_proxy_diff = None

    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "gating": "[NON_GATING]",
        "rq_id": "RQ-025",
        "proxy_tail": {
            "date_min": d0,
            "date_max": d1,
            "n_proxy_dates": len(proxy_dates),
            "implementation": batch_log.get("implementation"),
            "batch_log_json": _rel(args.batch_log_json if args.batch_log_json.is_absolute() else ROOT / args.batch_log_json),
        },
        "certified_csv": {
            "expected_inbox": _rel(certified_path),
            "present": certified_present,
        },
        "vault_proxy_integrity": vault_proxy_diff,
        "certified_vs_proxy": certified_proxy_diff,
        "status": status,
        "certification_pass": certification_pass,
        "apply": {
            "requested": bool(args.apply_vault),
            "applied": applied,
            "n_rows_replaced": n_replaced,
            "backup_csv": backup_path,
        },
        "human_action": (
            f"Drop upstream batch CSV at {certified_path} then re-run with --apply-vault"
            if not certified_present
            else "Certified file present; review certified_vs_proxy before apply"
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
    print(f"WROTE: {out_path} status={status} certified_present={certified_present} pass={certification_pass}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
