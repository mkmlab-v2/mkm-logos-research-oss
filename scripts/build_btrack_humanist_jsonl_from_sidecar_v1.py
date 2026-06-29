#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Export per-date myeongni/sasang JSONL from prophecy insight sidecar [HYPO][research_only]."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_SIDECAR = ROOT / "docs/final/artifacts/btrack_prophecy_score_insight_sidecar_v1_latest.json"
DEFAULT_MYEONGNI_OUT = ROOT / "reports/btrack_humanist_myeongni_from_sidecar_v1.jsonl"
DEFAULT_SASANG_OUT = ROOT / "reports/btrack_humanist_sasang_from_sidecar_v1.jsonl"
DEFAULT_MANIFEST = ROOT / "reports/btrack_humanist_from_sidecar_manifest_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _write_jsonl(rows: list[dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")


def export_humanist_jsonl_from_sidecar(
    *,
    sidecar_path: Path,
    instrument: str | None = None,
) -> dict[str, Any]:
    doc = json.loads(sidecar_path.read_text(encoding="utf-8-sig"))
    features = doc.get("per_date_features") or []
    my_rows: list[dict[str, Any]] = []
    sa_rows: list[dict[str, Any]] = []
    dates: list[str] = []

    for row in features:
        if not isinstance(row, dict):
            continue
        if instrument:
            inst = str(row.get("instrument") or "").strip().lower()
            if inst and inst != instrument.strip().lower():
                continue
        eval_date = str(row.get("eval_date") or "")[:10]
        if len(eval_date) != 10:
            continue
        dated = row.get("dated_source_snapshots_asof_eval_date") or {}
        my_block = dated.get("myeongni_16_state_jsonl") if isinstance(dated.get("myeongni_16_state_jsonl"), dict) else {}
        sa_block = dated.get("sasang_dynamics_jsonl") if isinstance(dated.get("sasang_dynamics_jsonl"), dict) else {}
        my_snap = my_block.get("snapshot") if isinstance(my_block.get("snapshot"), dict) else {}
        sa_snap = sa_block.get("snapshot") if isinstance(sa_block.get("snapshot"), dict) else {}
        if not my_snap and not sa_snap:
            continue

        dates.append(eval_date)
        if my_snap:
            my_rows.append(
                {
                    "ts_utc": f"{eval_date}T13:00:00Z",
                    "hypothesis_tier": "B",
                    "boundary_ack": True,
                    "stub": False,
                    "source_provenance": "sidecar_dated_snapshot_v1",
                    "underlying_may_be_calendar_stub": True,
                    "eval_date": eval_date,
                    "instrument": row.get("instrument"),
                    "state_id": my_snap.get("state_id"),
                    "mapping_target": my_snap.get("mapping_target"),
                    "consistency_rate": my_snap.get("consistency_rate"),
                    "self_contradiction_rate": my_snap.get("self_contradiction_rate", 0.05),
                    "run_id": my_snap.get("run_id") or "sidecar_dated_snapshot_v1",
                }
            )
        if sa_snap:
            sa_rows.append(
                {
                    "ts_utc": f"{eval_date}T12:00:00+00:00",
                    "hypothesis_tier": "B",
                    "boundary_ack": True,
                    "stub": False,
                    "source_provenance": "sidecar_dated_snapshot_v1",
                    "underlying_may_be_calendar_stub": True,
                    "eval_date": eval_date,
                    "instrument": row.get("instrument"),
                    "mapping_target": sa_snap.get("mapping_target"),
                    "regime_hypothesis": sa_snap.get("regime_hypothesis"),
                    "machine_readables": sa_snap.get("machine_readables") or {},
                    "a_track_autobind_forbidden": True,
                }
            )

    my_rows.sort(key=lambda r: str(r.get("eval_date")))
    sa_rows.sort(key=lambda r: str(r.get("eval_date")))

    return {
        "schema": "btrack_humanist_from_sidecar_export_v1",
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "research_only": True,
        "sidecar_path": str(sidecar_path.relative_to(ROOT)).replace("\\", "/")
        if sidecar_path.is_relative_to(ROOT)
        else str(sidecar_path),
        "instrument_filter": instrument,
        "n_eval_dates": len(set(dates)),
        "date_min": min(dates) if dates else None,
        "date_max": max(dates) if dates else None,
        "myeongni_rows": my_rows,
        "sasang_rows": sa_rows,
        "note_ko": "Sidecar dated snapshot export; underlying calendar rows may still be stub-origin.",
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--sidecar-json", type=Path, default=DEFAULT_SIDECAR)
    ap.add_argument("--instrument", type=str, default="kospi", help="Filter per_date_features instrument (empty=all)")
    ap.add_argument("--myeongni-out", type=Path, default=DEFAULT_MYEONGNI_OUT)
    ap.add_argument("--sasang-out", type=Path, default=DEFAULT_SASANG_OUT)
    ap.add_argument("--manifest-out", type=Path, default=DEFAULT_MANIFEST)
    args = ap.parse_args(argv)

    if not args.sidecar_json.is_file():
        print(f"Missing sidecar: {args.sidecar_json}", file=sys.stderr)
        return 1

    inst = args.instrument.strip().lower() if args.instrument else None
    if inst == "":
        inst = None

    doc = export_humanist_jsonl_from_sidecar(sidecar_path=args.sidecar_json, instrument=inst)
    _write_jsonl(doc["myeongni_rows"], args.myeongni_out)
    _write_jsonl(doc["sasang_rows"], args.sasang_out)

    manifest = {k: v for k, v in doc.items() if k not in ("myeongni_rows", "sasang_rows")}
    manifest["paths"] = {
        "myeongni_jsonl": str(args.myeongni_out.relative_to(ROOT)).replace("\\", "/"),
        "sasang_jsonl": str(args.sasang_out.relative_to(ROOT)).replace("\\", "/"),
    }
    args.manifest_out.parent.mkdir(parents=True, exist_ok=True)
    args.manifest_out.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(
        f"WROTE: {args.myeongni_out.resolve()} my={len(doc['myeongni_rows'])} "
        f"sa={len(doc['sasang_rows'])} dates={doc.get('n_eval_dates')}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
