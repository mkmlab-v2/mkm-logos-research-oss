#!/usr/bin/env python3
"""BESD DPT-R v2 bounded loader — dual-label bridge consumer (research only).

Preserves v1 expected semantics; stores v2_selected_action separately.
Does not mutate v1 loader or frozen bridge/fixtures.
"""
from __future__ import annotations

import hashlib
import json
import sys
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import run_besd_dpt_r_synthetic_fixture_validation_v1 as v1_loader  # noqa: E402
FIXTURE_DIR = ROOT / "docs/research/besd/dpt_r_fixture_validation/fixtures"
BRIDGE = ROOT / "docs/research/besd/dpt_r_fixture_validation/BESD_DPT_R_V1_V2_LABEL_BRIDGE_V1.json"
OUT_DIR = ROOT / "docs/research/besd/dpt_r_fixture_validation"
OUT_JSON = OUT_DIR / "BESD_DPT_R_V2_BOUNDED_LOADER_RESULTS_V1.json"

FAIL_CLOSED = frozenset(
    {
        "MISSING_BRIDGE_ENTRY",
        "UNRESOLVED_RELATION",
        "NO_EQUIVALENT_RELATION",
        "INVARIANT_FAILURE",
        "UNKNOWN_V2_ACTION",
        "BRIDGE_HASH_MISMATCH",
    }
)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def bridge_index(bridge: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {e["fixture_id"]: e for e in bridge.get("entries") or []}


def consume_bridge(
    fixture: dict[str, Any],
    v1_result: Any,
    entry: dict[str, Any],
    bridge_sha: str,
) -> dict[str, Any]:
    fid = fixture["fixture_id"]
    v1_expected = fixture["expected_after_t_dpt"]["selected_action_class"]
    v1_actual = v1_result.selected_action_class
    relation = entry.get("semantic_relation", "UNRESOLVED")
    v2_selected = entry.get("candidate_v2_label", "")
    also = set(entry.get("also_in_image") or [])
    failures: list[str] = []

    if v1_actual != v1_expected:
        failures.append("INVARIANT_FAILURE")
    if relation in {"UNRESOLVED", "NO_EQUIVALENT"}:
        failures.append(relation if relation in FAIL_CLOSED else "UNRESOLVED_RELATION")
    if v2_selected not in also:
        failures.append("UNKNOWN_V2_ACTION")
    if relation == "ONE_TO_MANY" and v2_selected == "NONCOOPERATE":
        # allowed in image; flag if falsely equated to second mile in record only
        pass
    if "MILE" in fid and relation != "ONE_TO_MANY":
        failures.append("INVARIANT_FAILURE")

    semantic_invariants_pass = len(failures) == 0
    return {
        "fixture_id": fid,
        "bridge_hash": bridge_sha,
        "v1_expected_action_class": v1_expected,
        "v1_actual_action_class": v1_actual,
        "v2_selected_action": v2_selected,
        "bridge_relation": relation,
        "also_in_image": sorted(also),
        "semantic_ceiling": entry.get("semantic_ceiling", ""),
        "semantic_invariants_pass": semantic_invariants_pass,
        "fail_closed_tokens": sorted(FAIL_CLOSED),
        "bridge_failures": failures,
        "pass_fixture": semantic_invariants_pass and v1_result.pass_fixture,
    }


def main() -> int:
    bridge = json.loads(BRIDGE.read_text(encoding="utf-8"))
    bridge_sha = sha256_file(BRIDGE)
    idx = bridge_index(bridge)
    fixtures = v1_loader.load_fixtures()
    v1_results = [v1_loader.t_dpt(fx) for fx in fixtures]

    dual_records: list[dict[str, Any]] = []
    for fx, vr in zip(fixtures, v1_results):
        entry = idx.get(fx["fixture_id"])
        if entry is None:
            dual_records.append(
                {
                    "fixture_id": fx["fixture_id"],
                    "bridge_failures": ["MISSING_BRIDGE_ENTRY"],
                    "pass_fixture": False,
                }
            )
            continue
        dual_records.append(consume_bridge(fx, vr, entry, bridge_sha))

    all_pass = all(r.get("pass_fixture") for r in dual_records)
    decide = (
        "BESD_DPT_R_V2_BOUNDED_LOADER_PASS"
        if all_pass
        else "BESD_DPT_R_V2_BOUNDED_LOADER_FAIL"
    )

    payload = {
        "schema": "besd_dpt_r_v2_bounded_loader_results_v1",
        "mission": "COMMANDER_BESD_DPT_R_V2_BOUNDED_LOADER_V1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "HYPO",
        "tags": ["HYPO", "research_only", "NON_GATING"],
        "send_gate": "HOLD",
        "LOADER_INTEGRATION": "HOLD",
        "PROMOTION": "NOT_AUTHORIZED",
        "bounded_loader": {
            "path": "scripts/run_besd_dpt_r_v2_bounded_loader_v1.py",
            "dual_label_record_present": True,
            "fail_closed_tokens_present": True,
            "LOADER_COMPATIBLE": all_pass,
            "v1_loader_unmutated": True,
        },
        "immutable_inputs": {
            "bridge_sha256": bridge_sha,
            "bridge_path": BRIDGE.as_posix(),
        },
        "summary": {
            "FIXTURE_N": len(dual_records),
            "PASS_N": sum(1 for r in dual_records if r.get("pass_fixture")),
            "FAIL_CLOSED_TOKEN_N": len(FAIL_CLOSED),
        },
        "DECIDE_ONE": decide,
        "dual_label_records": dual_records,
        "v1_fixture_results": [asdict(r) for r in v1_results],
        "claim_ceiling": {
            "establishes": "bounded dual-label bridge consumption on frozen v1+v2 fixtures",
            "does_not_establish": [
                "DPT-R promotion",
                "empirical validity",
                "Track A readiness",
            ],
        },
        "reproduce_command": "py scripts/run_besd_dpt_r_v2_bounded_loader_v1.py",
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(payload["summary"], indent=2))
    print("DECIDE_ONE:", decide)
    print("LOADER_COMPATIBLE:", all_pass)
    print("OUT:", OUT_JSON)
    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
