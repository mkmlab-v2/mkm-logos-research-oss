#!/usr/bin/env python3
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
OUT_JSON = ART / "news_third_party_repro_bundle_latest.json"
OUT_MD = ART / "news_third_party_repro_bundle_latest.md"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    payload = {
        "schema": "news_third_party_repro_bundle_v1",
        "generated_at_utc": _utc_now(),
        "status": "PENDING_EXTERNAL_EXECUTION",
        "third_party_repro_evidence_present": False,
        "required_artifacts": [
            {"name": "external_runner_manifest", "status": "pending"},
            {"name": "raw_logs_with_checksums", "status": "pending"},
            {"name": "independent_result_digest", "status": "pending"},
            {"name": "signed_repro_statement", "status": "pending"},
        ],
        "runbook": [
            "Freeze input corpus + seed + config hash.",
            "Run benchmark in independent environment.",
            "Publish raw logs and output hashes.",
            "Compare outputs against public claim pack ranges.",
            "Record pass/fail with timestamp and runner identity.",
        ],
        "note": "Template bundle only. Flip status after real third-party run evidence is attached.",
    }
    OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    md = [
        "# Third-Party Repro Bundle (Template)",
        "",
        f"- generated_at_utc: `{payload['generated_at_utc']}`",
        f"- status: `{payload['status']}`",
        f"- third_party_repro_evidence_present: `{payload['third_party_repro_evidence_present']}`",
        "",
        "## Required Artifacts",
    ]
    md.extend([f"- {x['name']}: `{x['status']}`" for x in payload["required_artifacts"]])
    md.extend(["", "## Runbook", *[f"- {x}" for x in payload["runbook"]], ""])
    OUT_MD.write_text("\n".join(md), encoding="utf-8")
    print(str(OUT_JSON))
    print(str(OUT_MD))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

