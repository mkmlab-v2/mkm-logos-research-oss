#!/usr/bin/env python3
"""Ingest model outputs into Vibe prompt runs JSONL."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
RUNS_JSONL = ART / "vibe_runs_raw" / "vibe_prompt_runs_latest.jsonl"
DEFAULT_INPUT = ART / "vibe_runs_raw" / "vibe_model_outputs_latest.jsonl"
OUT_LOG = ART / "vibe_runs_raw" / "vibe_ingest_log_latest.json"


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def key_of(row: dict[str, Any]) -> tuple[str, int]:
    return str(row.get("prompt_id")), int(row.get("run_index"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-jsonl", type=str, default=str(DEFAULT_INPUT))
    args = parser.parse_args()

    in_path = Path(args.input_jsonl)
    if not RUNS_JSONL.is_file():
        raise FileNotFoundError(f"missing runs file: {RUNS_JSONL}")
    if not in_path.is_file():
        raise FileNotFoundError(f"missing input jsonl: {in_path}")

    base_rows = read_jsonl(RUNS_JSONL)
    incoming = read_jsonl(in_path)

    incoming_map = {key_of(row): row for row in incoming}
    updated = 0
    missing = 0
    allowed = {"HOLD", "REDUCE", "WATCH"}

    for row in base_rows:
        key = key_of(row)
        src = incoming_map.get(key)
        if not src:
            missing += 1
            continue

        decision = src.get("decision")
        if decision not in allowed:
            continue

        row["status"] = "model_output_ingested"
        row["decision"] = decision
        row["confidence"] = src.get("confidence")
        row["rationale_short"] = src.get("rationale_short")
        row["risk_flags"] = src.get("risk_flags") or []
        row["raw_output_path"] = src.get("raw_output_path")
        row["ingested_at_utc"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        updated += 1

    write_jsonl(RUNS_JSONL, base_rows)

    log = {
        "schema": "vibe_ingest_log_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "runs_file": str(RUNS_JSONL).replace("\\", "/"),
        "input_file": str(in_path).replace("\\", "/"),
        "input_rows": len(incoming),
        "updated_rows": updated,
        "rows_without_match": missing,
    }
    OUT_LOG.write_text(json.dumps(log, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"updated_rows: {updated}")
    print(f"written: {RUNS_JSONL}")
    print(f"written: {OUT_LOG}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

