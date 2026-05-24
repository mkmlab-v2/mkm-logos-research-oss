#!/usr/bin/env python3
"""Validate compression domain adoption tier matrix SSOT (internal governance)."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MATRIX = ROOT / "docs" / "final" / "artifacts" / "compression_domain_adoption_tier_matrix_v1.json"

REQUIRED_TIER_IDS = ("adopt_ok", "adopt_limited", "adopt_not_recommended")
HARDENING_STATUSES = frozenset({"current", "partial", "b_track", "not_started"})
CRITERIA_VERDICTS = frozenset(
    {
        "success",
        "success_bench_scope",
        "limited_success",
        "conditional_fail",
        "fail",
    }
)


def validate(doc: dict, *, matrix_path: Path = MATRIX) -> tuple[list[dict[str, object]], list[str]]:
    checks: list[dict[str, object]] = []
    errors: list[str] = []

    def record(cid: str, ok: bool, detail: object = None) -> None:
        row: dict[str, object] = {"id": cid, "ok": ok}
        if detail is not None:
            row["detail"] = detail
        checks.append(row)
        if not ok:
            errors.append(cid)

    record("file:matrix_exists", matrix_path.is_file())
    if not matrix_path.is_file():
        return checks, errors

    record("schema", doc.get("schema") == "compression_domain_adoption_tier_matrix_v1")
    record("version_present", bool(doc.get("version")))

    tiers = doc.get("adoption_tiers")
    record("adoption_tiers_is_list", isinstance(tiers, list))
    if isinstance(tiers, list):
        tier_ids = [t.get("tier_id") for t in tiers if isinstance(t, dict)]
        record(
            "tier_ids_exact",
            tier_ids == list(REQUIRED_TIER_IDS),
            {"found": tier_ids},
        )
        for tid in REQUIRED_TIER_IDS:
            match = next((t for t in tiers if isinstance(t, dict) and t.get("tier_id") == tid), None)
            record(
                f"tier:{tid}:fields",
                bool(match)
                and bool(match.get("definition_ko"))
                and bool(match.get("example_workloads")),
            )

    criteria = doc.get("four_enterprise_criteria")
    record("four_criteria_count", isinstance(criteria, list) and len(criteria) == 4)
    if isinstance(criteria, list):
        for row in criteria:
            if not isinstance(row, dict):
                continue
            vid = row.get("poc_verdict")
            if vid not in CRITERIA_VERDICTS:
                record(f"criteria:{row.get('id')}:verdict", False, vid)

    roadmap = doc.get("hardening_roadmap")
    record("hardening_roadmap_is_list", isinstance(roadmap, list) and len(roadmap) >= 3)
    if isinstance(roadmap, list):
        for item in roadmap:
            if not isinstance(item, dict):
                continue
            st = item.get("status")
            if st not in HARDENING_STATUSES:
                record(f"hardening:{item.get('id')}:status", False, st)

    record("fail_comp_pointer", "FAIL-COMP-004" in str(doc.get("position_statement", {})))

    pointers = doc.get("position_statement", {}).get("evidence_pointers", [])
    record(
        "evidence_active_report",
        any("MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT" in str(p) for p in pointers),
    )

    return checks, errors


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--matrix",
        type=Path,
        default=MATRIX,
        help="Path to tier matrix JSON (default: repo SSOT)",
    )
    ap.add_argument(
        "--out-json",
        default="reports/compression_domain_adoption_tier_readiness_v1_latest.json",
    )
    ap.add_argument("--stdout-only", action="store_true")
    args = ap.parse_args()

    matrix_path = args.matrix.resolve()

    doc: dict = {}
    if matrix_path.is_file():
        doc = json.loads(matrix_path.read_text(encoding="utf-8"))

    checks, errors = validate(doc, matrix_path=matrix_path)
    ok = not errors and matrix_path.is_file()

    out = {
        "schema": "compression_domain_adoption_tier_readiness_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "matrix_path": str(matrix_path.relative_to(ROOT)) if matrix_path.is_file() else str(matrix_path),
        "matrix_ok": ok,
        "checks": checks,
        "failed_check_ids": errors,
        "note": "Internal governance only; does not authorize Track A active write or external send.",
    }

    out_path = ROOT / args.out_json
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    payload = {"matrix_ok": ok, "exit_code": 0 if ok else 1}
    if args.stdout_only:
        print(json.dumps(payload, ensure_ascii=False))
    else:
        print(f"WROTE: {out_path}")
        print(json.dumps(payload, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
