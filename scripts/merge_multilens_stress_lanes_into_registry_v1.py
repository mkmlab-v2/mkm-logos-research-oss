#!/usr/bin/env python3
"""Idempotently append large-stress lanes to universal_compression_bench_matrix_registry_v1.json."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REG = ROOT / "docs/final/artifacts/universal_compression_bench_matrix_registry_v1.json"

STRESS_LANES = [
    {
        "lane_id": "server_log_stress_v1",
        "domain_tag": "server_log_stress",
        "input_path": "docs/final/artifacts/universal_compression_bench_lane_server_log_stress_v1.json",
        "enabled": True,
        "priority": 10,
        "note": "Large stress — synthetic server/nginx logs",
    },
    {
        "lane_id": "en_tech_spec_stress_v1",
        "domain_tag": "en_tech_spec_stress",
        "input_path": "docs/final/artifacts/universal_compression_bench_lane_en_tech_spec_stress_v1.json",
        "enabled": True,
        "priority": 11,
        "note": "Large stress — English tech spec paragraphs",
    },
    {
        "lane_id": "finance_alnum_dense_v1",
        "domain_tag": "finance_alnum_dense",
        "input_path": "docs/final/artifacts/universal_compression_bench_lane_finance_alnum_dense_v1.json",
        "enabled": True,
        "priority": 12,
        "note": "Large stress — alphanumeric finance blocks",
    },
    {
        "lane_id": "enterprise_jsonl_stress_v1",
        "domain_tag": "enterprise_general",
        "input_path": "docs/final/artifacts/universal_compression_bench_lane_enterprise_jsonl_stress_v1.json",
        "enabled": True,
        "priority": 13,
        "note": "PoC JSONL harvest (stateless structured)",
    },
]


def main() -> int:
    if not REG.is_file():
        print(json.dumps({"error": "registry_missing", "path": str(REG)}))
        return 2
    reg = json.loads(REG.read_text(encoding="utf-8-sig"))
    existing = {str(ln.get("lane_id")) for ln in reg.get("lanes") or []}
    added = 0
    for ln in STRESS_LANES:
        if ln["lane_id"] not in existing:
            reg.setdefault("lanes", []).append(ln)
            added += 1
    reg["generated_at_utc"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    REG.write_text(json.dumps(reg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"lanes_total": len(reg["lanes"]), "added": added}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
