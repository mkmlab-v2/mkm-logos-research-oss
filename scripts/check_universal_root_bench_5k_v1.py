#!/usr/bin/env python3
"""Gate MKM-UR-Bench-5K holdout artifacts [HYPO · HOLD]."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SSOT = ROOT / "docs/final/artifacts/universal_root_bench_5k_named_v1.json"
OUT = ROOT / "reports/universal_root_bench_5k_check_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _read(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def evaluate(*, ssot_path: Path = SSOT) -> dict[str, Any]:
    ssot = _read(ssot_path)
    violations: list[str] = []

    full_fixture = ROOT / str(ssot.get("full_fixture") or "tests/fixtures/nsm_41k_lexicon_crosswalk_5000_v1.json")
    holdout_fixture = ROOT / str(
        ssot.get("holdout_fixture") or "tests/fixtures/universal_root_bench_5k_holdout_v1.json"
    )
    phase1a = ROOT / str(
        ssot.get("phase1a_report") or "reports/universal_root_bench_5k_holdout_phase1a_v1_latest.json"
    )
    chain_report = ROOT / str(
        ssot.get("chain_report") or "reports/universal_root_bench_5k_holdout_chain_v1_latest.json"
    )

    min_full = int(ssot.get("min_full_pairs") or 5000)
    min_holdout = int(ssot.get("min_holdout_pairs") or 500)

    full_doc = _read(full_fixture)
    holdout_doc = _read(holdout_fixture)
    phase_doc = _read(phase1a)
    chain_doc = _read(chain_report)

    if int(full_doc.get("pair_count") or 0) < min_full:
        violations.append(f"full_fixture_below_min:{full_doc.get('pair_count')}<{min_full}")
    if holdout_doc.get("schema") != "universal_root_bench_5k_holdout_v1":
        violations.append("holdout_fixture_schema_mismatch")
    if int(holdout_doc.get("pair_count") or 0) < min_holdout:
        violations.append(f"holdout_pair_count_below_min:{holdout_doc.get('pair_count')}<{min_holdout}")
    if phase_doc.get("schema") != "universal_root_phase1a_baseline_compare_v1":
        violations.append("phase1a_report_missing_or_schema_mismatch")
    if not chain_doc.get("ok"):
        violations.append("chain_report_not_ok")

    method_ids = {m.get("id") for m in phase_doc.get("methods") or []}
    for required in ("B0", "B3"):
        if required not in method_ids:
            violations.append(f"missing_method:{required}")

    b0 = next((m for m in phase_doc.get("methods") or [] if m.get("id") == "B0"), {})
    b3 = next((m for m in phase_doc.get("methods") or [] if m.get("id") == "B3"), {})

    b0_rate = b0.get("primary_value")
    min_b0 = ssot.get("min_holdout_b0_rate")
    if min_b0 is not None and b0_rate is not None and float(b0_rate) < float(min_b0):
        violations.append(f"holdout_b0_below_min:{b0_rate}<{min_b0}")

    ok = not violations
    delta_b3_b0 = None
    if b0_rate is not None and b3.get("primary_value") is not None:
        delta_b3_b0 = round(float(b3["primary_value"]) - float(b0_rate), 4)
    return {
        "bench_5k_ok": ok,
        "bench_name": ssot.get("name") or "MKM-UR-Bench-5K",
        "full_pair_count": int(full_doc.get("pair_count") or 0),
        "holdout_pair_count": int(holdout_doc.get("pair_count") or 0),
        "B0_english_only_hit_rate": b0_rate,
        "B3_dual_plane_aligned_rate": b3.get("primary_value"),
        "delta_b3_minus_b0": delta_b3_b0,
        "violations": violations,
        "ssot": str(ssot_path.relative_to(ROOT)).replace("\\", "/"),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--strict", action="store_true")
    ap.add_argument("--ssot", type=Path, default=SSOT)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()

    ev = evaluate(ssot_path=args.ssot)
    doc = {
        "schema": "universal_root_bench_5k_check_v1",
        "generated_at_utc": _utc(),
        **ev,
        "reproduce": "py scripts/check_universal_root_bench_5k_v1.py --strict",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"ok": ev["bench_5k_ok"], "holdout_pair_count": ev.get("holdout_pair_count"), "out": str(args.out)}))
    return 0 if ev["bench_5k_ok"] or not args.strict else 1


if __name__ == "__main__":
    raise SystemExit(main())
