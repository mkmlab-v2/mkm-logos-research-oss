#!/usr/bin/env python3
"""Build UR-B0-MISS-HOLDOUT-v1 — named public mini-bench on B0 misses [HYPO · HOLD]."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
CROSSWALK = ROOT / "reports/universal_root_topology_crosswalk_v1_latest.json"
AUDIT = ROOT / "reports/nsm_41k_lexicon_crosswalk_audit_hf_checkpoint_v1_latest.json"
FIXTURE = ROOT / "tests/fixtures/nsm_41k_lexicon_crosswalk_500_v1.json"
OUT_FIXTURE = ROOT / "tests/fixtures/universal_root_b0_miss_holdout_bench_v1.json"
OUT_REPORT = ROOT / "reports/universal_root_b0_miss_holdout_bench_v1_latest.json"
BUILD_CROSSWALK = ROOT / "scripts/build_universal_root_topology_crosswalk_v1.py"
PHASE1A = ROOT / "scripts/run_universal_root_baseline_compare_v1.py"
BENCH_SSOT = ROOT / "docs/final/artifacts/universal_root_named_public_bench_v1.json"


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _ensure_inputs() -> None:
    if not CROSSWALK.is_file():
        subprocess.run([PY, str(BUILD_CROSSWALK)], cwd=str(ROOT), check=True)
    if not (ROOT / "reports/universal_root_phase1a_baseline_compare_v1_latest.json").is_file():
        subprocess.run([PY, str(PHASE1A)], cwd=str(ROOT), check=True)


def _fixture_by_prime() -> dict[str, dict[str, Any]]:
    doc = _read(FIXTURE)
    out: dict[str, dict[str, Any]] = {}
    for row in doc.get("samples") or []:
        if isinstance(row, dict) and row.get("prime_en"):
            out[str(row["prime_en"])] = row
    return out


def build_holdout() -> dict[str, Any]:
    _ensure_inputs()
    crosswalk = _read(CROSSWALK)
    audit = _read(AUDIT)
    fixture_by_prime = _fixture_by_prime()
    audit_by_prime = {
        str(r.get("prime_en") or ""): r
        for r in ((audit.get("baseline") or {}).get("rows") or [])
        if r.get("prime_en")
    }

    misses: list[dict[str, Any]] = []
    non_control = 0
    en_hits = 0
    for row in crosswalk.get("rows") or []:
        if str(row.get("control") or "") == "negative":
            continue
        non_control += 1
        prime = str(row.get("prime_en") or "")
        audit_row = audit_by_prime.get(prime, {})
        en_hit = bool(audit_row.get("en_hit"))
        if en_hit:
            en_hits += 1
        if en_hit:
            continue
        sample = fixture_by_prime.get(prime, {})
        misses.append(
            {
                "prime_en": prime,
                "probe_en": sample.get("probe_en"),
                "lexicon_hit": bool(row.get("lexicon_hit")),
                "topology_reachable": bool(row.get("topology_reachable")),
                "wall_status": row.get("wall_status"),
                "audit_status": audit_row.get("status") or row.get("audit_status"),
                "expected_evaluator": "english_only_naive_miss",
            }
        )

    b0_miss_rate = round((non_control - en_hits) / non_control, 4) if non_control else None
    b0_hit_rate = round(en_hits / non_control, 4) if non_control else None

    holdout_doc = {
        "schema": "universal_root_b0_miss_holdout_bench_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "research_only": True,
        "send_gate": "HOLD",
        "bench_name": "UR-B0-MISS-HOLDOUT-v1",
        "bench_ssot": str(BENCH_SSOT.relative_to(ROOT)).replace("\\", "/"),
        "parent_fixture": str(FIXTURE.relative_to(ROOT)).replace("\\", "/"),
        "parent_fixture_sha256": _sha256(FIXTURE),
        "pair_count": len(misses),
        "non_control_pairs": non_control,
        "b0_hit_rate": b0_hit_rate,
        "b0_miss_rate": b0_miss_rate,
        "pairs": misses,
        "reproduce": "py scripts/build_universal_root_b0_miss_holdout_bench_v1.py",
    }

    report = {
        **holdout_doc,
        "schema": "universal_root_b0_miss_holdout_bench_report_v1",
        "holdout_fixture": str(OUT_FIXTURE.relative_to(ROOT)).replace("\\", "/"),
        "evaluator": "scripts/check_universal_root_named_public_bench_v1.py --strict",
    }
    return {"holdout": holdout_doc, "report": report}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-fixture", type=Path, default=OUT_FIXTURE)
    ap.add_argument("--out", type=Path, default=OUT_REPORT)
    args = ap.parse_args()

    built = build_holdout()
    holdout = built["holdout"]
    report = built["report"]

    args.out_fixture.parent.mkdir(parents=True, exist_ok=True)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out_fixture.write_text(json.dumps(holdout, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    args.out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(
        json.dumps(
            {
                "ok": True,
                "bench_name": holdout["bench_name"],
                "pair_count": holdout["pair_count"],
                "b0_miss_rate": holdout["b0_miss_rate"],
                "holdout_fixture": str(args.out_fixture),
                "out": str(args.out),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
