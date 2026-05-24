#!/usr/bin/env python3
"""Join Phase 3 leading-sensor JSONL stubs to btrack_prophecy_score rows (research_only).

Output: wide joined JSONL + meta JSON. Does not mutate prod score or enable Track A.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "docs/final/artifacts/btrack_phase3_leading_sensors_manifest_v1.json"
DEFAULT_SENSOR_DIR = ROOT / "data/btrack/phase3_leading_sensors"
DEFAULT_SCORE = ROOT / "docs/final/artifacts/btrack_prophecy_score_latest.json"
DEFAULT_OUT_JSONL = ROOT / "reports/btrack_phase3_leading_sensors_joined_v1_latest.jsonl"
DEFAULT_OUT_META = ROOT / "reports/btrack_phase3_leading_sensors_joined_v1_latest.meta.json"
SCHEMA = "btrack_phase3_leading_sensors_joined_v1"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rel(p: Path) -> str:
    try:
        return str(p.resolve().relative_to(ROOT.resolve())).replace("\\", "/")
    except ValueError:
        return str(p).replace("\\", "/")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        o = json.loads(line)
        if isinstance(o, dict):
            rows.append(o)
    return rows


def _resolve_sensor_path(sensor_dir: Path, s: dict[str, Any]) -> tuple[Path | None, str]:
    """Prefer measured feed over stub when both exist."""
    sid = str(s.get("sensor_id") or "")
    candidates: list[tuple[str, str]] = []
    if s.get("measured_jsonl_relpath"):
        candidates.append(("measured", str(s["measured_jsonl_relpath"])))
    candidates.append(("stub", str(s.get("stub_jsonl_relpath") or f"{sid}_stub.jsonl")))
    for kind, rel in candidates:
        path = sensor_dir / rel
        if path.is_file():
            return path, kind
    return None, "missing"


def _load_sensors(manifest: dict[str, Any], sensor_dir: Path) -> tuple[list[str], dict[str, dict[str, dict[str, Any]]], dict[str, str]]:
    """by_date[eval_date][sensor_id] = row; source_kind[sensor_id] = measured|stub."""
    sensor_ids: list[str] = []
    by_date: dict[str, dict[str, dict[str, Any]]] = {}
    source_kind: dict[str, str] = {}
    for s in manifest.get("sensors") or []:
        if not isinstance(s, dict):
            continue
        sid = str(s.get("sensor_id") or "")
        if not sid:
            continue
        sensor_ids.append(sid)
        path, kind = _resolve_sensor_path(sensor_dir, s)
        if path is None:
            source_kind[sid] = "missing"
            continue
        source_kind[sid] = kind
        for row in _read_jsonl(path):
            ed = str(row.get("eval_date") or "")[:10]
            if len(ed) != 10:
                continue
            by_date.setdefault(ed, {})[sid] = row
    return sensor_ids, by_date, source_kind


def _composite_signed_flow(by_date: dict[str, dict[str, Any]], eval_date: str, sensor_ids: list[str]) -> float | None:
    bucket = by_date.get(eval_date) or {}
    zs: list[float] = []
    for sid in sensor_ids:
        row = bucket.get(sid)
        if not isinstance(row, dict):
            continue
        feats = row.get("features") if isinstance(row.get("features"), dict) else {}
        z = feats.get("signed_flow_z")
        if isinstance(z, (int, float)):
            zs.append(float(z))
    if not zs:
        return None
    return round(sum(zs) / len(zs), 6)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    ap.add_argument("--sensor-dir", type=Path, default=DEFAULT_SENSOR_DIR)
    ap.add_argument("--score-json", type=Path, default=DEFAULT_SCORE)
    ap.add_argument("--instrument", default="btc", choices=("btc", "kospi", "pooled", "all"))
    ap.add_argument("--out-jsonl", type=Path, default=DEFAULT_OUT_JSONL)
    ap.add_argument("--out-meta", type=Path, default=DEFAULT_OUT_META)
    args = ap.parse_args(argv)

    if not args.manifest.is_file():
        print(f"MISSING manifest: {args.manifest}", file=__import__("sys").stderr)
        return 2
    if not args.score_json.is_file():
        print(f"MISSING score: {args.score_json}", file=__import__("sys").stderr)
        return 2

    manifest = _load_json(args.manifest)
    sensor_ids, by_date, source_kind = _load_sensors(manifest, args.sensor_dir)
    score = _load_json(args.score_json)
    raw_rows = [r for r in (score.get("rows") or []) if isinstance(r, dict)]

    joined: list[dict[str, Any]] = []
    n_sensor_missing = 0
    for r in raw_rows:
        inst = str(r.get("instrument") or "").strip().lower()
        if args.instrument != "all" and args.instrument != "pooled" and inst != args.instrument:
            continue
        if args.instrument == "pooled" and inst not in ("btc", "kospi"):
            continue
        ed = str(r.get("eval_date") or "")[:10]
        comp = _composite_signed_flow(by_date, ed, sensor_ids)
        if comp is None:
            n_sensor_missing += 1
        sensors_flat: dict[str, Any] = {}
        for sid in sensor_ids:
            srow = (by_date.get(ed) or {}).get(sid)
            if isinstance(srow, dict):
                sensors_flat[f"{sid}_signed_flow_z"] = (srow.get("features") or {}).get("signed_flow_z")
                sensors_flat[f"{sid}_data_quality"] = srow.get("data_quality")
        joined.append(
            {
                "eval_date": ed,
                "instrument": inst,
                "predicted_direction": r.get("predicted_direction"),
                "actual_direction": r.get("actual_direction"),
                "daily_return": r.get("daily_return"),
                "leading_composite_signed_flow_z": comp,
                "sensors": sensors_flat,
                "research_only": True,
                "hypothesis_tag": "[HYPO]",
            }
        )

    args.out_jsonl.parent.mkdir(parents=True, exist_ok=True)
    with args.out_jsonl.open("w", encoding="utf-8") as f:
        for row in joined:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    meta = {
        "schema": SCHEMA,
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "inputs": {
            "manifest": _rel(args.manifest),
            "sensor_dir": _rel(args.sensor_dir),
            "score_json": _rel(args.score_json),
        },
        "instrument_filter": args.instrument,
        "n_score_rows_joined": len(joined),
        "n_eval_dates_with_sensors": len({r["eval_date"] for r in joined if r.get("leading_composite_signed_flow_z") is not None}),
        "n_rows_missing_sensor": n_sensor_missing,
        "sensor_ids": sensor_ids,
        "sensor_source_kind": source_kind,
        "direction_promotion_allowed": False,
        "note_ko": "선행 센서는 join·ablation 연구용. 방향 승격·prod score 변경 없음.",
    }
    args.out_meta.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.out_jsonl.resolve()} ({len(joined)} rows)")
    print(f"WROTE: {args.out_meta.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
