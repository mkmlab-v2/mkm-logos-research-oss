#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

DEFAULT_SMOKE = ROOT / "docs" / "final" / "artifacts" / "macro_risk_warning_api_smoke_latest.json"
DEFAULT_PREREG = ROOT / "docs" / "final" / "artifacts" / "macro_risk_forward_preregister_lock_latest.json"
DEFAULT_LOG = ROOT / "reports" / "macro_risk" / "forward" / "macro_risk_forward_log_v1.jsonl"
DEFAULT_LATEST = ROOT / "docs" / "final" / "artifacts" / "macro_risk_forward_log_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _read_json(path: Path) -> dict[str, Any]:
    doc = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(doc, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return doc


def _canonical(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            rows.append(obj)
    return rows


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Append one daily forward-test log row with hash chaining.")
    p.add_argument("--smoke-json", type=Path, default=DEFAULT_SMOKE)
    p.add_argument("--preregister-json", type=Path, default=DEFAULT_PREREG)
    p.add_argument("--out-jsonl", type=Path, default=DEFAULT_LOG)
    p.add_argument("--latest-json", type=Path, default=DEFAULT_LATEST)
    p.add_argument("--source-label", default="macro_risk_warning_api_smoke_latest")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    smoke_path = args.smoke_json if args.smoke_json.is_absolute() else (ROOT / args.smoke_json)
    prereg_path = args.preregister_json if args.preregister_json.is_absolute() else (ROOT / args.preregister_json)
    out_jsonl = args.out_jsonl if args.out_jsonl.is_absolute() else (ROOT / args.out_jsonl)
    latest_json = args.latest_json if args.latest_json.is_absolute() else (ROOT / args.latest_json)

    smoke = _read_json(smoke_path)
    prereg = _read_json(prereg_path)
    prereg_hash = str(prereg.get("preregister_hash_sha256") or "")
    if not prereg_hash:
        raise ValueError("Missing preregister_hash_sha256 in prereg lock artifact.")

    rows = _load_jsonl(out_jsonl)
    prev_row_hash = str(rows[-1].get("row_hash_sha256") or "") if rows else "GENESIS"

    snapshot_ts = str(smoke.get("timestamp_utc") or smoke.get("ts_utc") or "")
    if not snapshot_ts:
        snapshot_ts = _utc_now()

    row_core = {
        "schema": "macro_risk_forward_log_row_v1",
        "logged_at_utc": _utc_now(),
        "source_label": args.source_label,
        "source_snapshot_ts_utc": snapshot_ts,
        "source_artifact_path": str(smoke_path.relative_to(ROOT)),
        "decision_state": smoke.get("decision_state"),
        "risk_warning_level": smoke.get("risk_warning_level"),
        "confidence_band": smoke.get("confidence_band"),
        "recommended_operator_posture": smoke.get("recommended_operator_posture"),
        "preregister_hash_sha256": prereg_hash,
        "previous_row_hash_sha256": prev_row_hash,
    }
    row_hash = _sha256_text(_canonical(row_core))
    row = {**row_core, "row_hash_sha256": row_hash}

    out_jsonl.parent.mkdir(parents=True, exist_ok=True)
    with out_jsonl.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")

    latest_doc = {
        "schema": "macro_risk_forward_log_latest_v1",
        "generated_at_utc": _utc_now(),
        "log_path": str(out_jsonl),
        "rows_total": len(rows) + 1,
        "latest_row": row,
    }
    latest_json.parent.mkdir(parents=True, exist_ok=True)
    latest_json.write_text(json.dumps(latest_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"forward_log_append: PASS -> {out_jsonl}")
    print(f"latest_snapshot: PASS -> {latest_json}")
    print(f"row_hash_sha256: {row_hash}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

