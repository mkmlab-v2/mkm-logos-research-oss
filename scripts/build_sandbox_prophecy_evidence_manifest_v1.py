#!/usr/bin/env python3
"""Manifest of SANDBOX artifact paths for human review / handoff (JSON only)."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "reports/sandbox_prophecy_evidence_manifest_v1_latest.json"

ARTIFACTS: list[tuple[str, str]] = [
    ("stream", "reports/sandbox_prophecy_stream_v1.jsonl"),
    ("panel", "reports/sandbox_prophecy_panel_v1_latest.json"),
    ("daily_chain", "reports/sandbox_prophecy_daily_chain_v1_latest.json"),
    ("brief", "reports/sandbox_prophecy_brief_v1_latest.json"),
    ("rollup", "reports/sandbox_prophecy_rollup_v1_latest.json"),
    ("watchlist", "reports/sandbox_prophecy_watchlist_v1_latest.json"),
    ("holdout", "reports/sandbox_prophecy_holdout_report_v1_latest.json"),
    ("promotion_research", "reports/sandbox_prophecy_promotion_research_pack_v1_latest.json"),
    ("bridge_draft", "reports/sandbox_prophecy_track_a_candidate_bridge_draft_v1_latest.json"),
    ("health", "reports/sandbox_prophecy_health_v1_latest.json"),
    ("ops_dashboard", "reports/sandbox_prophecy_ops_dashboard_v1_latest.json"),
    ("accumulation_status", "reports/sandbox_prophecy_accumulation_status_v1_latest.json"),
    ("human_review_pack", "reports/sandbox_prophecy_human_review_pack_v1_latest.json"),
    ("operator_digest", "reports/sandbox_prophecy_operator_digest_v1_latest.json"),
    ("artifacts_verify", "reports/sandbox_prophecy_artifacts_verify_v1_latest.json"),
    ("scheduled_tasks_verify", "reports/sandbox_prophecy_scheduled_tasks_verify_v1_latest.json"),
    ("mainline_candidate_ref", "docs/final/artifacts/prophecy_track_a_candidate_v1_latest.json"),
    ("prod_score_ref_readonly", "docs/final/artifacts/btrack_prophecy_score_latest.json"),
]


def _sha256(path: Path) -> str | None:
    if not path.is_file():
        return None
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def build_manifest(*, with_hashes: bool = False) -> dict[str, Any]:
    files: list[dict[str, Any]] = []
    for key, rel in ARTIFACTS:
        p = ROOT / rel.replace("/", "\\") if "\\" in rel else ROOT / rel
        entry: dict[str, Any] = {
            "key": key,
            "path": rel,
            "exists": p.is_file(),
            "size_bytes": p.stat().st_size if p.is_file() else None,
        }
        if with_hashes and p.is_file():
            entry["sha256"] = _sha256(p)
        files.append(entry)

    return {
        "schema": "sandbox_prophecy_evidence_manifest_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "hypothesis_tier": "SANDBOX",
        "research_only": True,
        "prod_score_mutation_by_sandbox": False,
        "n_files": len(files),
        "n_present": sum(1 for f in files if f.get("exists")),
        "files": files,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--with-hashes", action="store_true")
    args = ap.parse_args()

    doc = build_manifest(with_hashes=args.with_hashes)
    args.output.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output.resolve()} present={doc['n_present']}/{doc['n_files']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
