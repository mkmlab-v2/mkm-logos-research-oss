#!/usr/bin/env python3
"""
Automated Digital Hearing / Laser Prompt checks for 16_STATE_MASTER_PROBE:
- Contrast root audit_contract with a target state (default state_id=5).
- Enforce: no invented Tier/vectors beyond JSON; evidence_grade only if present on object + justified by contract fields.
- Stub semantics: fields absent on state use [ABSENT_IN_OBJECT] in report.

Usage:
  py scripts/verify_master_probe_state5.py [path/to/16_STATE_MASTER_PROBE_v1.json]
  echo "optional model answer text" | py scripts/verify_master_probe_state5.py --stdin

  Note: --stdin is required to read model-answer text. Without it, stdin is never read
  (avoids indefinite blocking when the terminal is non-interactive and stdin is not closed).
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

DEFAULT_PROBE = Path(__file__).resolve().parent.parent / "data" / "myeongni" / "16_STATE_MASTER_PROBE_v1.json"
TARGET_STATE_ID = 5

# Expected canonical values for state 5 (from SSOT JSON; used as fact-lock).
EXPECTED_STATE5 = {
    "mapping_target": "sideways",
    "vector_4d": {"S": 0.24, "L": 0.26, "K": 0.25, "M": 0.25},
    "audit": {
        "source_work": "corpus:myeongni_proxy_sample",
        "chunk_id": "nl_chunk_0042",
        "license_note": "research_audit_stub",
    },
}

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


def _approx_vec(a: dict[str, float], b: dict[str, float], eps: float = 1e-9) -> bool:
    for k in ("S", "L", "K", "M"):
        if abs(float(a[k]) - float(b[k])) > eps:
            return False
    return True


def _score_model_answer(text: str) -> dict[str, Any]:
    """Lightweight rubric: must not claim evidence_grade without JSON; must mention key stubs if discussing audit."""
    t = text.strip()
    out: dict[str, Any] = {
        "length": len(t),
        "flags": [],
        "pass_heuristic": True,
    }
    if not t:
        out["flags"].append("empty_model_answer")
        out["pass_heuristic"] = True
        return out
    lower = t.lower()
    if "evidence_grade" in lower and "[absent_in_object]" not in t and "absent" not in lower:
        out["flags"].append("mentions_evidence_grade_without_absent_disclaimer")
        out["pass_heuristic"] = False
    if "tier" in lower and "audit_contract" not in lower and "contract" not in lower:
        out["flags"].append("possible_tier_without_contract_citation")
        out["pass_heuristic"] = False
    return out


def _parse_args(argv: list[str]) -> tuple[Path, bool]:
    """Return (json_path, read_stdin_for_rubric)."""
    args = [a for a in argv[1:] if a != "--stdin"]
    read_stdin = "--stdin" in argv[1:]
    if args:
        return Path(args[0]).resolve(), read_stdin
    return DEFAULT_PROBE, read_stdin


def main() -> int:
    path, read_stdin = _parse_args(sys.argv)
    if not path.is_file():
        print(json.dumps({"error": "file_not_found", "path": str(path)}, indent=2))
        return 2

    data = _load_json(path)
    contract = data.get("audit_contract")
    states = data.get("states", [])
    st = _find_state(states, TARGET_STATE_ID)

    report: dict[str, Any] = {
        "probe_path": str(path),
        "target_state_id": TARGET_STATE_ID,
        "checks": [],
        "truthfulness": {"passed": 0, "failed": 0, "total": 0},
        "model_answer_rubric": None,
    }

    def add_check(name: str, ok: bool, detail: Any = None) -> None:
        report["truthfulness"]["total"] += 1
        if ok:
            report["truthfulness"]["passed"] += 1
        else:
            report["truthfulness"]["failed"] += 1
        entry = {"name": name, "pass": ok}
        if detail is not None:
            entry["detail"] = detail
        report["checks"].append(entry)

    # Contract presence
    add_check(
        "audit_contract_present",
        isinstance(contract, dict) and "fields" in contract and "layers" in contract,
    )
    if isinstance(contract, dict) and isinstance(contract.get("fields"), dict):
        ck = set(contract["fields"].keys())
        add_check(
            "audit_contract_fields_match_expected_set",
            ck == AUDIT_CONTRACT_FIELD_KEYS,
            {"expected": sorted(AUDIT_CONTRACT_FIELD_KEYS), "actual": sorted(ck)},
        )
        add_check(
            "audit_contract_has_no_evidence_grade_field",
            "evidence_grade" not in ck,
            "[ABSENT_IN_CONTRACT] evidence_grade not defined in audit_contract.fields",
        )

    add_check("state_5_present", st is not None)
    if not st:
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return 1

    add_check(
        "state_5_mapping_target",
        st.get("mapping_target") == EXPECTED_STATE5["mapping_target"],
        {"expected": EXPECTED_STATE5["mapping_target"], "actual": st.get("mapping_target")},
    )
    add_check(
        "state_5_vector_4d",
        _approx_vec(st.get("vector_4d", {}), EXPECTED_STATE5["vector_4d"]),
        {"expected": EXPECTED_STATE5["vector_4d"], "actual": st.get("vector_4d")},
    )

    # evidence_grade on state object
    has_eg = "evidence_grade" in st
    add_check(
        "state_5_top_level_evidence_grade_absent",
        not has_eg,
        "[ABSENT_IN_OBJECT] evidence_grade" if not has_eg else st.get("evidence_grade"),
    )

    audit = st.get("audit")
    add_check("state_5_audit_object_present", isinstance(audit, dict))

    if isinstance(audit, dict):
        for k, v in EXPECTED_STATE5["audit"].items():
            add_check(
                f"state_5_audit_{k}",
                audit.get(k) == v,
                {"expected": v, "actual": audit.get(k)},
            )
        sha = audit.get("sha256")
        ok_sha, reason = _sha256_valid(sha) if isinstance(sha, str) else (False, "missing_or_wrong_type")
        add_check("state_5_audit_sha256_64_hex", ok_sha, {"sha256": sha, "reason": reason})

    # Optional model-answer rubric (explicit --stdin only; avoids blocking on IDE/CI)
    if read_stdin:
        stdin_text = sys.stdin.read()
        report["model_answer_rubric"] = _score_model_answer(stdin_text)

    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report["truthfulness"]["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
