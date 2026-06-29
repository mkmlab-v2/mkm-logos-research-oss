#!/usr/bin/env python3
"""[HYPO] Read-only scan for off-repo / local upstream sgp_history CSV candidates."""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "reports/rq025_upstream_csv_discovery_v1_latest.json"
SCHEMA = "rq025_upstream_csv_discovery_v1"
POINTER = ROOT / "docs/final/LOCAL_MACHINE_POINTER_V1.md"
GLOB_NAME = "sgp_history*.csv"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_sidecar_flags(path: Path) -> dict[str, Any]:
    for mp in (path.with_name(path.name + ".meta.json"), path.with_suffix(".meta.json")):
        if mp.is_file():
            try:
                return json.loads(mp.read_text(encoding="utf-8-sig"))
            except json.JSONDecodeError:
                return {"sidecar_parse_error": str(mp)}
    return {}


def _csv_date_range(path: Path) -> tuple[str | None, str | None, int]:
    dates: list[str] = []
    try:
        with path.open(encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                dk = str(row.get("") or row.get("date") or "").strip()[:10]
                if len(dk) == 10:
                    dates.append(dk)
    except OSError:
        return None, None, 0
    if not dates:
        return None, None, 0
    dates.sort()
    return dates[0], dates[-1], len(dates)


def _scan_roots_from_pointer() -> list[Path]:
    roots: list[Path] = [
        ROOT / "data/rq025/intake",
        Path("G:/공유 드라이브/MKM_DATA_VAULT/data/macro_alerts"),
        ROOT / "reports/backups",
        ROOT / "reports/inbox",
        ROOT / "reports",
    ]
    if POINTER.is_file():
        text = POINTER.read_text(encoding="utf-8")
        for m in re.finditer(r"`([A-Za-z]:\\[^`]+)`", text):
            p = Path(m.group(1))
            if p.is_dir():
                roots.append(p)
        vault = re.search(r"mkm_data_vault`\s*\|\s*`([^`]+)`", text)
        if vault:
            roots.append(Path(vault.group(1)) / "data/macro_alerts")
    seen: set[str] = set()
    out: list[Path] = []
    for r in roots:
        key = str(r).lower()
        if key not in seen:
            seen.add(key)
            out.append(r)
    return out


def _validate_csv_schema(path: Path) -> dict[str, Any]:
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from scripts.validate_rq025_upstream_lambda_csv_v1 import validate_csv

    return validate_csv(path)


def _candidate_record(path: Path, *, source: str, validate_schema: bool = False) -> dict[str, Any]:
    d0, d1, n = _csv_date_range(path)
    meta = _load_sidecar_flags(path)
    rec: dict[str, Any] = {
        "path": str(path),
        "source": source,
        "exists": path.is_file(),
        "size_bytes": path.stat().st_size if path.is_file() else None,
        "row_count_estimate": n,
        "date_min": d0,
        "date_max": d1,
        "sidecar_meta_present": bool(meta),
        "upstream_production_batch": meta.get("upstream_production_batch"),
        "source_kind": meta.get("source_kind"),
    }
    if validate_schema and path.is_file():
        vr = _validate_csv_schema(path)
        rec["schema_ok"] = bool(vr.get("ok"))
        rec["schema_row_count"] = vr.get("row_count")
        errs = vr.get("errors") or []
        rec["schema_errors"] = errs[:5] if errs else []
    return rec


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--max-depth", type=int, default=4)
    ap.add_argument(
        "--validate-candidates",
        action="store_true",
        help="Run rq025 upstream CSV schema validation on each candidate",
    )
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args(argv)

    candidates: list[dict[str, Any]] = []
    env_path = os.environ.get("RQ025_UPSTREAM_LAMBDA_CERTIFIED_CSV", "").strip()
    if env_path:
        p = Path(env_path)
        candidates.append(
            _candidate_record(
                p,
                source="env_RQ025_UPSTREAM_LAMBDA_CERTIFIED_CSV",
                validate_schema=args.validate_candidates,
            )
        )

    for root in _scan_roots_from_pointer():
        if not root.is_dir():
            continue
        try:
            for hit in root.glob(GLOB_NAME):
                if hit.is_file():
                    candidates.append(
                        _candidate_record(hit, source=f"scan:{root}", validate_schema=args.validate_candidates)
                    )
            if args.max_depth > 0:
                for hit in root.rglob(GLOB_NAME):
                    if hit.is_file() and hit not in {Path(c["path"]) for c in candidates}:
                        rel = hit.relative_to(root)
                        if len(rel.parts) <= args.max_depth:
                            candidates.append(
                                _candidate_record(
                                    hit,
                                    source=f"scan_rglob:{root}",
                                    validate_schema=args.validate_candidates,
                                )
                            )
        except OSError:
            continue

    # de-dup by path
    by_path: dict[str, dict[str, Any]] = {}
    for c in candidates:
        by_path[c["path"]] = c
    unique = list(by_path.values())
    prod = [c for c in unique if c.get("upstream_production_batch") is True]
    schema_ok = [c for c in unique if c.get("schema_ok") is True]
    schema_fail = [c for c in unique if c.get("schema_ok") is False]

    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "rq_id": "RQ-025",
        "scan_roots": [str(r) for r in _scan_roots_from_pointer()],
        "candidates": sorted(unique, key=lambda x: str(x.get("path"))),
        "verdict": {
            "n_candidates": len(unique),
            "n_production_meta": len(prod),
            "n_schema_ok": len(schema_ok) if args.validate_candidates else None,
            "n_schema_fail": len(schema_fail) if args.validate_candidates else None,
            "schema_validated": bool(args.validate_candidates),
            "recommended_next": (
                "Set RQ025_UPSTREAM_LAMBDA_CERTIFIED_CSV to candidate with sidecar "
                "upstream_production_batch=true, then run run_rq025_upstream_csv_auto_resolve_and_three_arm_v1.py"
                if prod
                else (
                    "Schema-ok candidates exist but no production sidecar meta; "
                    "drop CSV+meta to data/rq025/intake/ or attach sidecar to chosen path"
                    if args.validate_candidates and schema_ok
                    else "No production-meta CSV found; Human Gate — export off-repo batch + sidecar meta"
                )
            ),
        },
        "track_wall": {
            "track_a_auto_merge": False,
            "oracle_promotion": False,
            "live_trading": False,
        },
    }
    out = args.output if args.output.is_absolute() else ROOT / args.output
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    extra = ""
    if args.validate_candidates:
        extra = f" schema_ok={len(schema_ok)} schema_fail={len(schema_fail)}"
    print(f"WROTE: {out} candidates={len(unique)} production_meta={len(prod)}{extra}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
