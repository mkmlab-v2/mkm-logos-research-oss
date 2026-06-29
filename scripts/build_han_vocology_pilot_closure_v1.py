#!/usr/bin/env python3
"""Build Han Vocology KM-VHI pilot closure report (B-track · M14/M15)."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_JSONL = ROOT / "reports/han_vocology_km_vhi_pilot_records.jsonl"
GATE = ROOT / "reports/han_vocology_km_vhi_pilot_cohort_gate_v1_latest.json"
REGISTRY = ROOT / "docs/final/artifacts/han_vocology_multisite_registry_v1_latest.json"
OUT = ROOT / "reports/han_vocology_pilot_closure_v1_latest.json"

CB11_16 = ["CB-11", "CB-12", "CB-13", "CB-14", "CB-15", "CB-16"]
CB06_10 = [
    "CB-06-A", "CB-06-B", "CB-08-A", "CB-08-B", "CB-09-A", "CB-09-B", "CB-10-A", "CB-10-B",
]


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def build_closure(*, jsonl: Path, gate: dict[str, Any], registry: dict[str, Any]) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for line in jsonl.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))

    cb_seen = sorted({str(r.get("cb_id")) for r in rows if r.get("cb_id")})
    sites = sorted({str(r.get("site_id")) for r in rows if r.get("site_id")})
    cohorts = sorted({str(r.get("pseudonym_id")) for r in rows if r.get("pseudonym_id")})

    week12 = [c for c in gate.get("cohorts") or [] if c.get("delta_pct_week12") is not None]

    cb11_complete = all(cb in cb_seen for cb in CB11_16)
    cb06_complete = all(cb in cb_seen for cb in CB06_10)
    cb_full_complete = cb11_complete and cb06_complete
    gate_ok = bool(gate.get("ok"))
    registry_ok = bool(registry.get("cb11_16_pilot_complete")) and bool(
        registry.get("cb06_10_legacy_complete", False)
    )

    ok = (
        gate_ok
        and cb11_complete
        and cb06_complete
        and registry_ok
        and len(cohorts) >= 14
        and len(week12) >= 6
        and rows
        and all(r.get("send_gate") == "HOLD" for r in rows)
        and all(r.get("track") == "B" for r in rows)
    )

    return {
        "schema": "han_vocology_pilot_closure_v1",
        "ok": ok,
        "track": "B",
        "send_gate": "HOLD",
        "patient_facing": "blocked",
        "row_count": len(rows),
        "cohort_count": len(cohorts),
        "site_count": len(sites),
        "cb_ids": cb_seen,
        "cb11_16_complete": cb11_complete,
        "cb06_10_complete": cb06_complete,
        "cb_full_bank_complete": cb_full_complete,
        "sites": sites,
        "cohorts": cohorts,
        "gate": {
            "ok": gate_ok,
            "excellent_at_week8": gate.get("excellent_at_week8"),
            "cohorts_with_week8": gate.get("cohorts_with_week8"),
            "band_counts_week8": gate.get("band_counts_week8"),
        },
        "week12_followup_count": len(week12),
        "registry_version": registry.get("version"),
        "disclaimer_ko": "교육·[HYPO] 파일럿 클로저 — 임상 효능·IRB 승인·send_gate 해제를 의미하지 않음.",
        "reproduce": [
            "py scripts/validate_han_vocology_km_vhi_pilot_jsonl_v1.py",
            "py scripts/build_han_vocology_km_vhi_pilot_cohort_gate_v1.py",
            "py scripts/build_han_vocology_pilot_closure_v1.py",
        ],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--jsonl", type=Path, default=DEFAULT_JSONL)
    ap.add_argument("--gate", type=Path, default=GATE)
    ap.add_argument("--registry", type=Path, default=REGISTRY)
    ap.add_argument("--out", type=Path, default=OUT)
    ap.add_argument("--skip-validate", action="store_true")
    args = ap.parse_args()

    if not args.jsonl.is_file():
        print(json.dumps({"ok": False, "error": "jsonl_missing"}, ensure_ascii=False))
        return 1

    if not args.skip_validate:
        proc = subprocess.run(
            [sys.executable, str(ROOT / "scripts/validate_han_vocology_km_vhi_pilot_jsonl_v1.py"), "--jsonl", str(args.jsonl)],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        if proc.returncode != 0:
            print(proc.stdout or proc.stderr)
            return 1
        subprocess.run(
            [sys.executable, str(ROOT / "scripts/build_han_vocology_km_vhi_pilot_cohort_gate_v1.py")],
            cwd=ROOT,
            check=False,
        )

    if not args.gate.is_file():
        print(json.dumps({"ok": False, "error": "gate_missing"}, ensure_ascii=False))
        return 1

    gate = _load_json(args.gate)
    registry = _load_json(args.registry) if args.registry.is_file() else {}
    result = build_closure(jsonl=args.jsonl, gate=gate, registry=registry)
    result["generated_at_utc"] = _utc()
    result["jsonl"] = str(args.jsonl)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": result["ok"],
                "cohort_count": result["cohort_count"],
                "cb11_16_complete": result["cb11_16_complete"],
                "cb06_10_complete": result["cb06_10_complete"],
                "cb_full_bank_complete": result["cb_full_bank_complete"],
                "out": str(args.out),
            },
            ensure_ascii=False,
        )
    )
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
