#!/usr/bin/env python3
"""Build/refresh Agent Handoff Governance Phase 1 pack (KPI + onepager timestamps).

Reads token bench when present; does not overwrite customer pilot fields.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCRIPT_ROOT = Path(__file__).resolve().parents[1]
KPI_PATH = SCRIPT_ROOT / "docs/final/artifacts/agent_handoff_governance_pilot_kpi_v1_latest.json"
ONEPAGER_JSON = SCRIPT_ROOT / "docs/final/artifacts/agent_handoff_governance_enterprise_onepager_v1_latest.json"
BENCH_PATH = SCRIPT_ROOT / "reports/mkm_ops_memory_index_token_bench_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, doc: dict[str, Any]) -> None:
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _update_kpi_from_bench(kpi: dict[str, Any], bench: dict[str, Any]) -> None:
    off = bench.get("resume_pack_inject_off", {})
    on = bench.get("resume_pack_inject_on", {})
    full = bench.get("full_anchor_slices", {})
    delta = bench.get("delta_vs_full_slices", {})
    slice_ab = bench.get("slice_on_off_ab", {})

    mapping = {
        "inject_tokens_off": off.get("tokens"),
        "inject_tokens_on_slice_1200": on.get("tokens"),
        "token_reduction_vs_full_anchors": delta.get("reduction_percent"),
    }
    for row in kpi.get("kpi_rows", []):
        kid = row.get("kpi_id")
        if kid in mapping and mapping[kid] is not None:
            row["baseline_internal"] = mapping[kid]
    kpi["generated_at_utc"] = _utc_now()
    if kpi.get("pilot_status") == "template":
        kpi["pilot_status"] = "internal_baseline"
    kpi["_bench_sync"] = {
        "source": str(BENCH_PATH.relative_to(SCRIPT_ROOT)).replace("\\", "/"),
        "inject_off_tokens": off.get("tokens"),
        "inject_on_tokens": on.get("tokens"),
        "full_anchor_tokens": full.get("tokens"),
        "reduction_percent": delta.get("reduction_percent"),
        "slice_max_chars": bench.get("slice_max_chars"),
        "tokens_added_by_slice": slice_ab.get("tokens_added_by_slice"),
    }


def _update_onepager_from_bench(onepager: dict[str, Any], bench: dict[str, Any]) -> None:
    off = bench.get("resume_pack_inject_off", {})
    on = bench.get("resume_pack_inject_on", {})
    full = bench.get("full_anchor_slices", {})
    delta = bench.get("delta_vs_full_slices", {})
    onepager["generated_at_utc"] = _utc_now()
    onepager["internal_baseline_snapshot"] = {
        "inject_off_tokens": off.get("tokens"),
        "inject_on_tokens_slice_1200": on.get("tokens"),
        "full_anchor_tokens_top3": full.get("tokens"),
        "reduction_percent_vs_full_anchors": delta.get("reduction_percent"),
        "method": off.get("method", "tiktoken:cl100k_base"),
        "evidence_path": str(BENCH_PATH.relative_to(SCRIPT_ROOT)).replace("\\", "/"),
        "scope_note": (
            "Lab measurement on top-3 ops nodes — customer ROI requires pilot fields "
            "in agent_handoff_governance_pilot_kpi_v1_latest.json"
        ),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--skip-bench-sync", action="store_true", help="Only refresh timestamps.")
    args = ap.parse_args()

    if not KPI_PATH.is_file():
        print(f"FAIL: missing {KPI_PATH}", flush=True)
        return 1
    if not ONEPAGER_JSON.is_file():
        print(f"FAIL: missing {ONEPAGER_JSON}", flush=True)
        return 1

    kpi = _read_json(KPI_PATH)
    onepager = _read_json(ONEPAGER_JSON)

    if not args.skip_bench_sync and BENCH_PATH.is_file():
        bench = _read_json(BENCH_PATH)
        _update_kpi_from_bench(kpi, bench)
        _update_onepager_from_bench(onepager, bench)
    else:
        kpi["generated_at_utc"] = _utc_now()
        onepager["generated_at_utc"] = _utc_now()

    _write_json(KPI_PATH, kpi)
    _write_json(ONEPAGER_JSON, onepager)
    print(f"WROTE: {KPI_PATH}")
    print(f"WROTE: {ONEPAGER_JSON}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
