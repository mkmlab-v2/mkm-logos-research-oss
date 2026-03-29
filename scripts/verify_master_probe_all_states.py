#!/usr/bin/env python3
"""
Master-Audit: verify all 16 states in 16_STATE_MASTER_PROBE JSON against audit_contract
and structural reproducibility rules (same spirit as verify_master_probe_state5.py).

Per state: mapping_target enum, vector_4d closure, no top-level evidence_grade,
audit object keys match contract set, sha256/confidence/lines.

Usage:
  py scripts/verify_master_probe_all_states.py [path/to/16_STATE_MASTER_PROBE_v1.json]
Exit: 0 if all checks pass, 1 otherwise.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

DEFAULT_PROBE = Path(__file__).resolve().parent.parent / "data" / "myeongni" / "16_STATE_MASTER_PROBE_v1.json"

AUDIT_CONTRACT_FIELD_KEYS = frozenset(
    [
        "schema_version",
        "source_work",
        "chunk_id",
        "line_start",
        "line_end",
        "sha256",
        "rules_version",
        "expected_parent",
        "confidence_score",
        "edition_or_url",
        "license_note",
    ]
)

MAPPING_ENUM = frozenset({"bull", "bear", "sideways"})
VEC_KEYS = ("S", "L", "K", "M")
VECTOR_SUM_EPS = 1e-6


def _load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def _find_state(states: list[dict[str, Any]], state_id: int) -> dict[str, Any] | None:
    for s in states:
        if s.get("state_id") == state_id:
            return s
    return None


def _sha256_valid(h: str) -> tuple[bool, str]:
    if not isinstance(h, str):
        return False, "not_a_string"
    if len(h) != 64:
        return False, f"length_{len(h)}_not_64"
    if not re.fullmatch(r"[0-9a-fA-F]{64}", h):
        return False, "not_64_hex"
    return True, "ok"


def _vector_ok(v: Any) -> tuple[bool, str | dict[str, Any]]:
    if not isinstance(v, dict):
        return False, "vector_not_object"
    for k in VEC_KEYS:
        if k not in v:
            return False, f"missing_axis_{k}"
        if not isinstance(v[k], (int, float)):
            return False, f"axis_{k}_not_number"
    s = sum(float(v[x]) for x in VEC_KEYS)
    if abs(s - 1.0) > VECTOR_SUM_EPS:
        return False, {"sum": s, "expected": 1.0, "eps": VECTOR_SUM_EPS}
    return True, "ok"


def _parse_args(argv: list[str]) -> Path:
    if len(argv) > 1:
        return Path(argv[1]).resolve()
    return DEFAULT_PROBE


def _verify_one_state(st: dict[str, Any], sid: int) -> dict[str, Any]:
    """Return { checks: [...], reproducibility_score: 0..100, failures: [...] }."""
    checks: list[dict[str, Any]] = []
    failures: list[str] = []

    def add(name: str, ok: bool, detail: Any = None) -> None:
        e: dict[str, Any] = {"name": name, "pass": ok}
        if detail is not None:
            e["detail"] = detail
        checks.append(e)
        if not ok:
            failures.append(name)

    add("state_id_field_matches_slot", st.get("state_id") == sid, {"expected": sid, "actual": st.get("state_id")})
    mt = st.get("mapping_target")
    add("mapping_target_enum", mt in MAPPING_ENUM, {"actual": mt, "allowed": sorted(MAPPING_ENUM)})

    vok, vd = _vector_ok(st.get("vector_4d"))
    add("vector_4d_valid_and_unit_sum", vok, vd)

    has_eg = "evidence_grade" in st
    add("top_level_evidence_grade_absent", not has_eg, None if not has_eg else st.get("evidence_grade"))

    audit = st.get("audit")
    add("audit_object_present", isinstance(audit, dict))
    if isinstance(audit, dict):
        ak = set(audit.keys())
        add(
            "audit_keys_match_contract_set",
            ak == AUDIT_CONTRACT_FIELD_KEYS,
            {"expected": sorted(AUDIT_CONTRACT_FIELD_KEYS), "actual": sorted(ak)},
        )
        sha = audit.get("sha256")
        s_ok, s_reason = _sha256_valid(sha) if isinstance(sha, str) else (False, "missing_or_wrong_type")
        add("audit_sha256_64_hex", s_ok, {"sha256": sha, "reason": s_reason})

        cs = audit.get("confidence_score")
        cs_ok = isinstance(cs, (int, float)) and 0.0 <= float(cs) <= 1.0
        add("audit_confidence_0_1", cs_ok, cs)

        ls, le = audit.get("line_start"), audit.get("line_end")
        lr_ok = (
            isinstance(ls, int)
            and isinstance(le, int)
            and ls <= le
        )
        add("audit_line_range_ordered", lr_ok, {"line_start": ls, "line_end": le})

    n = len(checks)
    passed = sum(1 for c in checks if c["pass"])
    score = round(100.0 * passed / n, 2) if n else 0.0
    tier = "A" if not failures else ("B" if len(failures) <= 2 else "F")
    return {
        "state_id": sid,
        "checks": checks,
        "reproducibility_score": score,
        "reproducibility_tier": tier,
        "failures": failures,
    }


def main() -> int:
    path = _parse_args(sys.argv)
    if not path.is_file():
        print(json.dumps({"error": "file_not_found", "path": str(path)}, indent=2))
        return 2

    data = _load_json(path)
    contract = data.get("audit_contract")
    states = data.get("states", [])

    report: dict[str, Any] = {
        "probe_path": str(path),
        "master_probe_version": data.get("master_probe_version"),
        "contract_and_inventory": {"checks": []},
        "states": [],
        "aggregate": {
            "states_checked": 0,
            "checks_passed": 0,
            "checks_failed": 0,
            "all_states_tier_A": True,
        },
    }

    def add_global(name: str, ok: bool, detail: Any = None) -> None:
        report["aggregate"]["checks_passed" if ok else "checks_failed"] += 1
        e: dict[str, Any] = {"name": name, "pass": ok}
        if detail is not None:
            e["detail"] = detail
        report["contract_and_inventory"]["checks"].append(e)

    # Root contract (same as state5)
    add_global(
        "audit_contract_present",
        isinstance(contract, dict) and "fields" in contract and "layers" in contract,
    )
    if isinstance(contract, dict) and isinstance(contract.get("fields"), dict):
        ck = set(contract["fields"].keys())
        add_global(
            "audit_contract_fields_match_expected_set",
            ck == AUDIT_CONTRACT_FIELD_KEYS,
            {"expected": sorted(AUDIT_CONTRACT_FIELD_KEYS), "actual": sorted(ck)},
        )
        add_global(
            "audit_contract_has_no_evidence_grade_field",
            "evidence_grade" not in ck,
            "[ABSENT_IN_CONTRACT] evidence_grade not defined in audit_contract.fields",
        )

    # Inventory: exactly 16 unique ids 1..16
    ids_found = sorted({s.get("state_id") for s in states if isinstance(s, dict)})
    expected_ids = list(range(1, 17))
    add_global("states_list_covers_1_to_16_unique", ids_found == expected_ids, {"actual": ids_found})

    cov = data.get("coverage_summary") or {}
    sip = cov.get("state_ids_present")
    if isinstance(sip, list):
        add_global(
            "coverage_summary_state_ids_match",
            sorted(int(x) for x in sip) == expected_ids,
            {"coverage_summary": sip},
        )

    for sid in range(1, 17):
        st = _find_state(states, sid)
        if st is None:
            report["states"].append(
                {
                    "state_id": sid,
                    "error": "missing_state",
                    "reproducibility_score": 0.0,
                    "reproducibility_tier": "F",
                }
            )
            report["aggregate"]["all_states_tier_A"] = False
            report["aggregate"]["checks_failed"] += 1
            continue

        one = _verify_one_state(st, sid)
        report["states"].append(one)
        report["aggregate"]["states_checked"] += 1
        for c in one["checks"]:
            report["aggregate"]["checks_passed" if c["pass"] else "checks_failed"] += 1
        if one["reproducibility_tier"] != "A":
            report["aggregate"]["all_states_tier_A"] = False

    total = report["aggregate"]["checks_passed"] + report["aggregate"]["checks_failed"]
    report["aggregate"]["checks_total"] = total
    report["summary"] = {
        "all_pass": report["aggregate"]["checks_failed"] == 0,
        "min_reproducibility_score": min(
            (s.get("reproducibility_score", 0) for s in report["states"]),
            default=0,
        ),
        "mean_reproducibility_score": round(
            sum(s.get("reproducibility_score", 0) for s in report["states"]) / max(len(report["states"]), 1),
            2,
        ),
    }

    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report["summary"]["all_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
