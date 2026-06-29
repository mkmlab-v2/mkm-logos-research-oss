#!/usr/bin/env python3
"""[HYPO] Auto-discover certified λ CSV → inbox → apply-vault → post-cert repin.

Default substitute (no external upstream file): tail rows from
`reports/rq025_sgp_history_merged_hypo_v1.csv` (carry-forward, NOT production batch).
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BATCH_LOG = ROOT / "reports/rq025_sgp_lambda_vault_batch_v1_latest.json"
INBOX = ROOT / "reports/inbox/rq025_upstream_sgp_lambda_certified_v1.csv"
INBOX_META = ROOT / "reports/inbox/rq025_upstream_sgp_lambda_certified_v1.meta.json"
MERGED = ROOT / "reports/rq025_sgp_history_merged_hypo_v1.csv"
POST_CERT = ROOT / "scripts/build_rq025_post_cert_vault_direct_repin_chain_v1.py"
DEFAULT_OUT = ROOT / "reports/rq025_auto_upstream_lambda_certification_v1_latest.json"
SCHEMA = "rq025_auto_upstream_lambda_certification_v1"
VAULT_FIELDS = ("", "S", "L", "K", "M", "lambda_t", "lambda_ma", "lambda_std", "z_score", "gradient", "alert_level")


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _row_date(row: dict[str, str]) -> str:
    dk = str(row.get("") or row.get("date") or "").strip()[:10]
    return dk if len(dk) == 10 else ""


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def _write_inbox(rows: list[dict[str, str]], out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(VAULT_FIELDS), extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in VAULT_FIELDS})


def _extract_tail(path: Path, d0: str, d1: str) -> list[dict[str, str]]:
    tail = [r for r in _read_csv(path) if d0 <= _row_date(r) <= d1]
    tail.sort(key=_row_date)
    return tail


def _run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, timeout=600)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--source-csv", type=Path, default=None, help="Explicit certified/substitute CSV")
    ap.add_argument(
        "--substitute",
        choices=("none", "merged_carry_forward"),
        default="merged_carry_forward",
        help="When no source/inbox: build inbox from local substitute (default)",
    )
    ap.add_argument("--skip-apply", action="store_true")
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args(argv)

    batch = _load(BATCH_LOG)
    d0 = str(batch.get("new_date_min") or "")[:10]
    d1 = str(batch.get("new_date_max") or "")[:10]
    if len(d0) != 10:
        raise SystemExit("batch log missing proxy tail dates")

    source_path: Path | None = None
    source_kind = "inbox_existing"
    boundary_ack = ""

    if args.source_csv:
        source_path = args.source_csv if args.source_csv.is_absolute() else ROOT / args.source_csv
        source_kind = "explicit_path"
    elif os.environ.get("RQ025_UPSTREAM_LAMBDA_CERTIFIED_CSV"):
        source_path = Path(os.environ["RQ025_UPSTREAM_LAMBDA_CERTIFIED_CSV"])
        source_kind = "env_RQ025_UPSTREAM_LAMBDA_CERTIFIED_CSV"
    elif INBOX.is_file():
        source_path = INBOX
        source_kind = "inbox_existing"
    elif args.substitute == "merged_carry_forward" and MERGED.is_file():
        tail = _extract_tail(MERGED, d0, d1)
        if len(tail) < 1:
            raise SystemExit(f"merged substitute has no rows in {d0}..{d1}")
        _write_inbox(tail, INBOX)
        meta = {
            "generated_at_utc": _utc_now(),
            "source_csv": str(MERGED.relative_to(ROOT)).replace("\\", "/"),
            "source_kind": "local_merged_carry_forward_substitute",
            "upstream_production_batch": False,
            "boundary_ack": (
                "Carry-forward tail from build_rq025_sgp_history_merged_hypo_v1.py; "
                "NOT off-repo upstream sgp/lambda batch. Research substitute only."
            ),
            "n_rows": len(tail),
            "date_min": d0,
            "date_max": d1,
        }
        INBOX_META.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        source_path = INBOX
        source_kind = "local_merged_carry_forward_substitute"
        boundary_ack = meta["boundary_ack"]
    else:
        raise SystemExit("no certified/substitute source; set --source-csv or enable merged substitute")

    if source_path != INBOX and source_path.is_file():
        INBOX.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, INBOX)
        INBOX_META.write_text(
            json.dumps(
                {
                    "generated_at_utc": _utc_now(),
                    "source_csv": str(source_path),
                    "source_kind": source_kind,
                    "upstream_production_batch": source_kind not in (
                        "local_merged_carry_forward_substitute",
                    ),
                    "copied_to_inbox": True,
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

    post_cmd = [sys.executable, str(POST_CERT), "--certified-csv", str(INBOX)]
    if not args.skip_apply:
        post_cmd.append("--apply-vault")
    proc = _run(post_cmd)
    if proc.returncode != 0:
        raise SystemExit(f"post_cert failed\n{proc.stderr}\n{proc.stdout}")

    post = _load(ROOT / "reports/rq025_post_cert_vault_direct_repin_chain_v1_latest.json")
    cert = post.get("certification") or {}

    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "gating": "[NON_GATING]",
        "rq_id": "RQ-025",
        "source_kind": source_kind,
        "upstream_production_batch": False,
        "boundary_ack": boundary_ack or "See inbox meta.json; do not claim upstream batch without external proof",
        "inbox_csv": str(INBOX.relative_to(ROOT)).replace("\\", "/"),
        "inbox_meta": str(INBOX_META.relative_to(ROOT)).replace("\\", "/") if INBOX_META.is_file() else None,
        "certification_status": cert.get("status"),
        "certification_applied": bool((cert.get("apply") or {}).get("applied")),
        "repin": post.get("repin"),
        "human_remainder": (
            "Provide real upstream batch CSV via --source-csv or env RQ025_UPSTREAM_LAMBDA_CERTIFIED_CSV"
            if source_kind == "local_merged_carry_forward_substitute"
            else None
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
        f"WROTE: {out_path} source={source_kind} cert={cert.get('status')} "
        f"applied={(cert.get('apply') or {}).get('applied')} "
        f"holdout={(post.get('repin') or {}).get('holdout_ensemble_test')}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
