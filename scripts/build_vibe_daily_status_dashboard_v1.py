#!/usr/bin/env python3
"""Build daily dashboard artifact for Vibe research loop."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"

ALERT_JSON = ART / "vibe_gate_alert_latest.json"
COVERAGE_JSON = ART / "vibe_runs_raw" / "vibe_raw_coverage_latest.json"
CONSISTENCY_JSON = ART / "vibe_prompt_consistency_report_latest.json"
EVOLUTION_JSON = ART / "vibe_evolution_suggestions_latest.json"
INGEST_LOG_JSON = ART / "vibe_runs_raw" / "vibe_ingest_log_latest.json"
EXTERNAL_INPUT_JSONL = ART / "vibe_external_inputs_latest.jsonl"

OUT_JSON = ART / "vibe_daily_status_dashboard_latest.json"
OUT_MD = ART / "vibe_daily_status_dashboard_latest.md"


def load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def summarize_external_inputs(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {
            "rows": 0,
            "parse_errors": 0,
            "bucket_counts": {},
            "latest_as_of_utc": None,
        }
    rows = 0
    parse_errors = 0
    bucket_counts: dict[str, int] = {}
    latest_as_of_utc = None
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        rows += 1
        try:
            obj = json.loads(line)
        except Exception:
            parse_errors += 1
            continue
        bucket = str(obj.get("bucket", "unknown"))
        bucket_counts[bucket] = bucket_counts.get(bucket, 0) + 1
        as_of = obj.get("as_of_utc")
        if isinstance(as_of, str):
            if latest_as_of_utc is None or as_of > latest_as_of_utc:
                latest_as_of_utc = as_of
    return {
        "rows": rows,
        "parse_errors": parse_errors,
        "bucket_counts": bucket_counts,
        "latest_as_of_utc": latest_as_of_utc,
    }


def main() -> int:
    alert = load(ALERT_JSON)
    coverage = load(COVERAGE_JSON)
    consistency = load(CONSISTENCY_JSON)
    evolution = load(EVOLUTION_JSON)
    ingest = load(INGEST_LOG_JSON)
    external_inputs = summarize_external_inputs(EXTERNAL_INPUT_JSONL)

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    gate_status = alert.get("status", "unknown")
    filled_cov = coverage.get("filled_coverage_ratio")
    consistency_ratio = (
        consistency.get("overall", {}).get("overall_weighted_consistency_ratio")
        if isinstance(consistency.get("overall"), dict)
        else None
    )
    updated_rows = ingest.get("updated_rows")
    evo_count = len(evolution.get("suggestions", [])) if isinstance(evolution.get("suggestions"), list) else 0

    health = "green"
    if gate_status == "fail":
        health = "red"
    elif gate_status == "ok" and isinstance(consistency_ratio, (int, float)) and consistency_ratio < 0.7:
        health = "yellow"

    dashboard = {
        "schema": "vibe_daily_status_dashboard_v1",
        "generated_at_utc": now,
        "scope": "research_only",
        "overall_health": health,
        "summary": {
            "gate_status": gate_status,
            "gate_stage": alert.get("stage"),
            "gate_message": alert.get("message"),
            "filled_coverage_ratio": filled_cov,
            "consistency_ratio": consistency_ratio,
            "ingested_rows": updated_rows,
            "evolution_suggestion_count": evo_count,
            "external_input_rows": external_inputs["rows"],
            "external_input_parse_errors": external_inputs["parse_errors"],
            "external_input_latest_as_of_utc": external_inputs["latest_as_of_utc"],
        },
        "external_input_bucket_counts": external_inputs["bucket_counts"],
        "paths": {
            "alert": str(ALERT_JSON).replace("\\", "/"),
            "coverage": str(COVERAGE_JSON).replace("\\", "/"),
            "consistency": str(CONSISTENCY_JSON).replace("\\", "/"),
            "evolution": str(EVOLUTION_JSON).replace("\\", "/"),
            "ingest_log": str(INGEST_LOG_JSON).replace("\\", "/"),
            "external_input_jsonl": str(EXTERNAL_INPUT_JSONL).replace("\\", "/"),
        },
    }
    OUT_JSON.write_text(json.dumps(dashboard, ensure_ascii=False, indent=2), encoding="utf-8")

    md = [
        "# Vibe Daily Status Dashboard (Latest)",
        "",
        f"- Generated (UTC): {now}",
        f"- Overall health: {health}",
        f"- Gate: {dashboard['summary']['gate_status']} ({dashboard['summary']['gate_stage']})",
        f"- Gate message: {dashboard['summary']['gate_message']}",
        f"- Filled coverage ratio: {filled_cov}",
        f"- Consistency ratio: {consistency_ratio}",
        f"- Ingested rows: {updated_rows}",
        f"- Evolution suggestions: {evo_count}",
        f"- External input rows: {external_inputs['rows']}",
        f"- External input parse errors: {external_inputs['parse_errors']}",
        f"- External input latest as_of_utc: {external_inputs['latest_as_of_utc']}",
        "",
        "## External Input Buckets",
    ]
    for bucket, count in sorted(external_inputs["bucket_counts"].items()):
        md.append(f"- {bucket}: {count}")
    md.append("")
    OUT_MD.write_text("\n".join(md), encoding="utf-8")

    print(f"written: {OUT_JSON}")
    print(f"written: {OUT_MD}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

