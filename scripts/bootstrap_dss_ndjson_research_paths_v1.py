#!/usr/bin/env python3
"""Bootstrap missing DSS NDJSON manifest paths for local research lane (smoke fixture only).

Does not run dss-4d-ingest frontline. Copies tests/fixtures when --allow-smoke-bootstrap.
research_only · [HYPO] · not production scroll text.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FIXTURE = ROOT / "tests/fixtures/dss_tokens_research_smoke_v1.ndjson"
DEFAULT_OUT_DIR = ROOT / "projects/dss-4d-ingest/outputs"
DEFAULT_TARGETS = (
    "apocrypha_tokens_pilot_manifest_ext3_hebrew_priority.ndjson",
    "apocrypha_tokens_pilot_manifest_ext2_weighted.ndjson",
    "dss_tokens_ci_smoke_manifest_tf4.ndjson",
)
DEFAULT_REPORT = ROOT / "reports/dss_ndjson_research_bootstrap_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--fixture-ndjson", type=Path, default=DEFAULT_FIXTURE)
    ap.add_argument("--output-dir", type=Path, default=DEFAULT_OUT_DIR)
    ap.add_argument("--allow-smoke-bootstrap", action="store_true")
    ap.add_argument("--report-json", type=Path, default=DEFAULT_REPORT)
    args = ap.parse_args()

    missing = [name for name in DEFAULT_TARGETS if not (args.output_dir / name).is_file()]
    payload: dict[str, Any] = {
        "schema": "dss_ndjson_research_bootstrap_v1",
        "generated_at_utc": _utc_now(),
        "research_rail": "B",
        "hypothesis_tier": "[HYPO]",
        "allow_smoke_bootstrap": args.allow_smoke_bootstrap,
        "fixture_ndjson": str(args.fixture_ndjson),
        "output_dir": str(args.output_dir),
        "missing_before": missing,
        "bootstrapped": [],
        "skipped_existing": [],
    }

    if not missing:
        payload["status"] = "ok_all_present"
        args.report_json.parent.mkdir(parents=True, exist_ok=True)
        args.report_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"ok": True, "status": "ok_all_present", "report": str(args.report_json)}, ensure_ascii=False))
        return 0

    if not args.allow_smoke_bootstrap:
        payload["status"] = "watch_missing_paths"
        args.report_json.parent.mkdir(parents=True, exist_ok=True)
        args.report_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(
            json.dumps(
                {
                    "ok": True,
                    "status": "watch_missing_paths",
                    "missing": missing,
                    "report": str(args.report_json),
                },
                ensure_ascii=False,
            )
        )
        return 0

    if not args.fixture_ndjson.is_file():
        print(json.dumps({"ok": False, "error": f"missing fixture: {args.fixture_ndjson}"}), file=sys.stderr)
        return 2

    args.output_dir.mkdir(parents=True, exist_ok=True)
    for name in missing:
        dst = args.output_dir / name
        shutil.copy2(args.fixture_ndjson, dst)
        payload["bootstrapped"].append(str(dst))

    for name in DEFAULT_TARGETS:
        if name not in missing:
            payload["skipped_existing"].append(str(args.output_dir / name))

    payload["status"] = "smoke_bootstrapped"
    args.report_json.parent.mkdir(parents=True, exist_ok=True)
    args.report_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "status": "smoke_bootstrapped",
                "bootstrapped_count": len(payload["bootstrapped"]),
                "report": str(args.report_json),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
