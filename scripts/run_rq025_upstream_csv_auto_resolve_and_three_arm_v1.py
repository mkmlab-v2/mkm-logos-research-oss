#!/usr/bin/env python3
"""[HYPO] Auto-resolve upstream λ CSV (discover → synthesize if needed) → 3-arm → train-only.

Sidecar meta (optional, next to CSV): ``<file>.csv.meta.json`` or ``<file>.meta.json``
with ``upstream_production_batch``, ``source_kind``, ``boundary_ack``.
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
MERGED_SCRIPT = ROOT / "scripts/build_rq025_sgp_history_merged_hypo_v1.py"
MERGED_CSV = ROOT / "reports/rq025_sgp_history_merged_hypo_v1.csv"
PROXY_BASE = ROOT / "reports/backups/sgp_history_master_real_pre_cert_20260611T074914Z.csv"
SYNTH_OUT = ROOT / "reports/rq025_upstream_sgp_lambda_full_v1.csv"
THREE_ARM = ROOT / "scripts/build_rq025_lambda_source_three_arm_compare_v1.py"
TRAIN_CHAIN = ROOT / "scripts/build_rq025_train_only_causal_holdout_chain_poc_v1.py"
DEFAULT_OUT = ROOT / "reports/rq025_upstream_csv_auto_resolve_v1_latest.json"
SCHEMA = "rq025_upstream_csv_auto_resolve_v1"
G_CANDIDATES = (
    Path("G:/공유 드라이브/MKM_DATA_VAULT/data/macro_alerts/sgp_history_master_real.csv"),
    Path("G:/공유 드라이브/MKM_DATA_VAULT/data/macro_alerts/sgp_history_master.csv"),
)
INTAKE_DIR = ROOT / "data/rq025/intake"
CANONICAL_INTAKE_CSV = INTAKE_DIR / "upstream_lambda_certified.csv"
FULL_HISTORY_MIN_ROWS = 500


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _sidecar_meta_candidates(csv_path: Path) -> tuple[Path, Path]:
    return (
        csv_path.with_name(csv_path.name + ".meta.json"),
        csv_path.with_suffix(".meta.json"),
    )


def _load_sidecar_meta(csv_path: Path) -> tuple[dict[str, Any], Path | None]:
    for mp in _sidecar_meta_candidates(csv_path):
        if mp.is_file():
            return _load(mp), mp
    return {}, None


def _policy_from_csv(
    csv_path: Path,
    *,
    default_kind: str,
    default_prod: bool = False,
) -> tuple[str, bool, str | None, dict[str, Any]]:
    meta, meta_path = _load_sidecar_meta(csv_path)
    kind = str(meta.get("source_kind") or default_kind)
    is_prod = bool(meta.get("upstream_production_batch")) if "upstream_production_batch" in meta else default_prod
    ack = meta.get("boundary_ack")
    if isinstance(ack, str):
        ack = ack.strip() or None
    else:
        ack = None
    detail: dict[str, Any] = {}
    if meta_path:
        detail["sidecar_meta"] = str(meta_path)
    if meta:
        detail["sidecar_meta_fields"] = sorted(meta.keys())
    return kind, is_prod, ack, detail


def _run(cmd: list[str]) -> None:
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, timeout=600)
    if proc.returncode != 0:
        raise SystemExit(f"failed: {' '.join(cmd)}\n{proc.stderr}\n{proc.stdout}")


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def _row_date(row: dict[str, str]) -> str:
    dk = str(row.get("") or row.get("date") or "").strip()[:10]
    return dk if len(dk) == 10 else ""


def _write_csv(path: Path, fields: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)


def _synthesize_full_from_tail(
    *,
    base_csv: Path,
    tail_csv: Path,
    d0: str,
    d1: str,
    out_csv: Path,
) -> dict[str, Any]:
    base_rows = _read_csv(base_csv)
    tail_by = {_row_date(r): r for r in _read_csv(tail_csv) if _row_date(r)}
    fields = list(base_rows[0].keys()) if base_rows else list(tail_by.values())[0].keys() if tail_by else []
    replaced = 0
    out_rows: list[dict[str, str]] = []
    for r in base_rows:
        dk = _row_date(r)
        if d0 <= dk <= d1 and dk in tail_by:
            out_rows.append(tail_by[dk])
            replaced += 1
        else:
            out_rows.append(r)
    _write_csv(out_csv, list(fields), out_rows)
    return {
        "base_csv": str(base_csv),
        "tail_csv": str(tail_csv),
        "out_csv": str(out_csv.relative_to(ROOT)).replace("\\", "/"),
        "date_min": d0,
        "date_max": d1,
        "n_replaced": replaced,
    }


def _discover_upstream(
    *,
    allow_synthesize: bool,
    refresh_merged: bool,
) -> tuple[Path, str, bool, dict[str, Any]]:
    """Return (path, source_kind, upstream_production_batch, detail)."""
    detail: dict[str, Any] = {}

    env_path = os.environ.get("RQ025_UPSTREAM_LAMBDA_CERTIFIED_CSV", "").strip()
    if env_path:
        p = Path(env_path)
        if p.is_file():
            kind, is_prod, _, pol = _policy_from_csv(
                p, default_kind="env_RQ025_UPSTREAM_LAMBDA_CERTIFIED_CSV"
            )
            pol["env_path"] = env_path
            return (p, kind, is_prod, pol)

    if CANONICAL_INTAKE_CSV.is_file():
        kind, is_prod, _, pol = _policy_from_csv(
            CANONICAL_INTAKE_CSV, default_kind="intake_canonical_upstream"
        )
        pol["intake_dir"] = str(INTAKE_DIR.relative_to(ROOT)).replace("\\", "/")
        return (CANONICAL_INTAKE_CSV, kind, is_prod, pol)

    if INTAKE_DIR.is_dir():
        for hit in sorted(INTAKE_DIR.glob("*.csv")):
            if hit.name.endswith(".example"):
                continue
            kind, is_prod, _, pol = _policy_from_csv(hit, default_kind="intake_drop_zone")
            if is_prod:
                pol["intake_path"] = str(hit)
                return (hit, kind, True, pol)

    for g in G_CANDIDATES:
        if not g.is_file():
            continue
        kind, is_prod, _, pol = _policy_from_csv(g, default_kind="g_vault_csv_candidate")
        pol["g_path"] = str(g)
        if is_prod:
            return (g, kind, True, pol)

    if refresh_merged and MERGED_SCRIPT.is_file():
        _run([sys.executable, str(MERGED_SCRIPT)])

    batch = _load(BATCH_LOG)
    d0 = str(batch.get("new_date_min") or "")[:10]
    d1 = str(batch.get("new_date_max") or "")[:10]

    if INBOX.is_file() and len(d0) == 10 and len(d1) == 10 and allow_synthesize and PROXY_BASE.is_file():
        inbox_rows = _read_csv(INBOX)
        if inbox_rows:
            synth = _synthesize_full_from_tail(
                base_csv=PROXY_BASE,
                tail_csv=INBOX,
                d0=d0,
                d1=d1,
                out_csv=SYNTH_OUT,
            )
            meta = _load(INBOX_META)
            detail["synthesize"] = synth
            return (
                SYNTH_OUT,
                str(meta.get("source_kind") or "inbox_tail_synthesized_full"),
                bool(meta.get("upstream_production_batch")),
                detail,
            )

    if MERGED_CSV.is_file():
        detail["merged_csv"] = str(MERGED_CSV.relative_to(ROOT)).replace("\\", "/")
        return (
            MERGED_CSV,
            "local_merged_carry_forward_full",
            False,
            detail,
        )

    raise SystemExit(
        "no upstream CSV resolved; set RQ025_UPSTREAM_LAMBDA_CERTIFIED_CSV or run merged hypo builder"
    )


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--skip-refresh-merged", action="store_true")
    ap.add_argument("--skip-synthesize", action="store_true")
    ap.add_argument("--skip-train-only", action="store_true")
    ap.add_argument("--upstream-csv", type=Path, default=None, help="Override discovery")
    ap.add_argument(
        "--upstream-production-batch",
        action="store_true",
        help="Force upstream_production_batch=true (else read CSV sidecar meta)",
    )
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args(argv)

    boundary_ack: str | None = None
    if args.upstream_csv:
        up = args.upstream_csv if args.upstream_csv.is_absolute() else ROOT / args.upstream_csv
        if not up.is_file():
            raise SystemExit(f"missing --upstream-csv: {up}")
        source_kind, is_prod, boundary_ack, detail = _policy_from_csv(
            up, default_kind="explicit_override"
        )
        detail["override"] = str(up)
        if args.upstream_production_batch:
            is_prod = True
    else:
        up, source_kind, is_prod, detail = _discover_upstream(
            allow_synthesize=not args.skip_synthesize,
            refresh_merged=not args.skip_refresh_merged,
        )
        if args.upstream_production_batch:
            is_prod = True
        if not boundary_ack:
            _, _, boundary_ack, _ = _policy_from_csv(up, default_kind=source_kind, default_prod=is_prod)

    staged = ROOT / "reports/inbox/rq025_upstream_sgp_lambda_full_staged_v1.csv"
    staged.parent.mkdir(parents=True, exist_ok=True)
    macro_for_arm = up
    synth_detail: dict[str, Any] | None = None
    n_rows = len(_read_csv(up))
    batch = _load(BATCH_LOG)
    d0 = str(batch.get("new_date_min") or "")[:10]
    d1 = str(batch.get("new_date_max") or "")[:10]
    if n_rows < FULL_HISTORY_MIN_ROWS and len(d0) == 10 and len(d1) == 10 and PROXY_BASE.is_file():
        synth_detail = _synthesize_full_from_tail(
            base_csv=PROXY_BASE,
            tail_csv=up,
            d0=d0,
            d1=d1,
            out_csv=SYNTH_OUT,
        )
        macro_for_arm = SYNTH_OUT
        detail["tail_synthesized_to_full"] = synth_detail

    if macro_for_arm.resolve() != staged.resolve():
        shutil.copy2(macro_for_arm, staged)

    three_cmd = [
        sys.executable,
        str(THREE_ARM),
        "--upstream-csv",
        str(staged),
        "--upstream-label",
        source_kind,
    ]
    if is_prod:
        three_cmd.append("--upstream-production-batch")
    _run(three_cmd)

    train_doc: dict[str, Any] = {}
    if not args.skip_train_only:
        _run([sys.executable, str(TRAIN_CHAIN), "--skip-cert-gate"])
        train_doc = _load(ROOT / "reports/rq025_train_only_causal_holdout_chain_poc_v1_latest.json")

    three_doc = _load(ROOT / "reports/rq025_lambda_source_three_arm_compare_v1_latest.json")
    upstream_arm = next((a for a in three_doc.get("arms") or [] if a.get("arm_id") == "upstream"), {})

    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "gating": "[NON_GATING]",
        "rq_id": "RQ-025",
        "resolved": {
            "upstream_csv": str(up),
            "staged_csv": str(staged.relative_to(ROOT)).replace("\\", "/"),
            "source_kind": source_kind,
            "upstream_production_batch": is_prod,
            "sidecar_meta_policy": "see <csv>.csv.meta.json or <csv>.meta.json",
            "detail": detail,
        },
        "three_arm": three_doc,
        "upstream_arm_holdout": upstream_arm.get("holdout_ensemble_test"),
        "train_only": {
            "full_test": (train_doc.get("holdout_full_sample_causal") or {}).get("ensemble_test_accuracy"),
            "train_only_test": (train_doc.get("holdout_train_only_causal") or {}).get("ensemble_test_accuracy"),
            "delta": train_doc.get("delta_train_only_minus_full_test"),
        }
        if train_doc
        else {"skipped": args.skip_train_only},
        "boundary_ack": boundary_ack
        or (
            "Real off-repo upstream sgp/lambda batch not auto-found on G: Vault; "
            "used local merged/inbox-synthesized substitute unless env override set."
            if not is_prod
            else "External upstream CSV applied per sidecar meta or CLI production flag."
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
        f"WROTE: {out_path} source={source_kind} prod={is_prod} "
        f"upstream_holdout={upstream_arm.get('holdout_ensemble_test')} "
        f"best={(three_doc.get('verdict') or {}).get('best_arm_by_holdout')}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
