#!/usr/bin/env python3
"""Refresh promotion manifest gate flags from disk evidence."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "reports/multi_res_index_promotion_manifest_v1_latest.json"
HUMAN_APPROVAL = ROOT / "docs/final/artifacts/multi_res_index_human_approval_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    if not MANIFEST.is_file():
        print(f"FAIL: missing {MANIFEST}")
        return 1
    doc = json.loads(MANIFEST.read_text(encoding="utf-8-sig"))
    gates = doc.setdefault("gates", {})
    gates["schema_pytest_pass"] = (
        "pass" if (ROOT / "docs/final/schemas/multi_res_index_v1.schema.json").is_file() else "pending"
    )
    gates["fills_index_built"] = (
        "pass" if (ROOT / "reports/multi_res_fills_index_v1_latest.json").is_file() else "pending"
    )
    gates["fusion_bench_recorded"] = (
        "pass" if (ROOT / "reports/multi_res_fusion_bench_v1_latest.json").is_file() else "pending"
    )
    gates["must_keep_gate_pass"] = (
        "pass"
        if (ROOT / "storage/meta/mkm_ops_memory_index_v1.json").is_file()
        and "prism_ops_fills_multi_res_summary"
        in (
            json.loads(
                (ROOT / "storage/meta/mkm_ops_memory_index_v1.json").read_text(encoding="utf-8-sig")
            ).get("nodes")
            or {}
        )
        else "pending"
    )
    if HUMAN_APPROVAL.is_file():
        approval = json.loads(HUMAN_APPROVAL.read_text(encoding="utf-8-sig"))
        doc["human_approval"] = {
            "path": str(HUMAN_APPROVAL.relative_to(ROOT)).replace("\\", "/"),
            "decision": approval.get("decision"),
            "approved_at_utc": approval.get("approved_at_utc"),
            "reviewer": approval.get("reviewer"),
        }
        doc["would_change_active"] = bool(approval.get("would_change_active", False))
    else:
        doc["would_change_active"] = False
    doc["generated_at_utc"] = _utc_now()
    MANIFEST.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(gates, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
