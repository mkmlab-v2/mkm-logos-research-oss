#!/usr/bin/env python3
"""P5 manuscript integrity gate (sidecars only, no mainline promotion) [HYPO]."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CANON = ROOT / "reports/constitution/btrack_pilot/logos_verse_4d_v1_latest.jsonl"
PROMO = ROOT / "docs/final/artifacts/dss_line_witness_promotion_gate_v1_latest.json"
OUT_DEFAULT = ROOT / "docs/final/artifacts/p5_manuscript_integrity_gate_v1_latest.json"

REQUIRED = [
    ROOT / "reports/cross_ref_entry_12_mt_only_sidecar_v1_latest.json",
    ROOT / "reports/cross_ref_entry_12_13_bench_relabel_sidecar_v1_latest.json",
    ROOT / "reports/dss_4q_ps5_line_witness_map_v1_latest.json",
    ROOT / "reports/shadow_4q_ps5_witness_registry_v1_latest.json",
    ROOT / "reports/manuscript_integrity_audit_11q5_psalms_commander_v1_latest.json",
]


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (json.JSONDecodeError, OSError):
        return {}


def _canon_clean() -> tuple[bool, int]:
    bad = 0
    if not CANON.is_file():
        return False, 0
    with CANON.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            vid = str(row.get("verse_id") or "")
            if vid.startswith("dss:") or "11Q5" in vid:
                bad += 1
    return bad == 0, bad


def build() -> dict[str, Any]:
    promo = _load(PROMO)
    mt = _load(ROOT / "reports/cross_ref_entry_12_mt_only_sidecar_v1_latest.json")
    relabel = _load(ROOT / "reports/cross_ref_entry_12_13_bench_relabel_sidecar_v1_latest.json")
    map4q = _load(ROOT / "reports/dss_4q_ps5_line_witness_map_v1_latest.json")
    audit = _load(ROOT / "reports/manuscript_integrity_audit_11q5_psalms_commander_v1_latest.json")
    canon_ok, canon_bad = _canon_clean()

    checks = {
        "artifacts_present": {"passed": all(p.is_file() for p in REQUIRED), "paths": [str(p.name) for p in REQUIRED]},
        "entry_12_mt_only": {
            "passed": mt.get("witness_rail") == "mt_only" and mt.get("eleven_q5_bench_status") == "hypothesis_retired",
        },
        "entry_13_retargeted": {
            "passed": any(
                e.get("entry_id") == "ENTRY_13" and e.get("bench_status") == "retargeted"
                for e in relabel.get("entries") or []
            ),
        },
        "4q_witness_map": {
            "passed": int((map4q.get("summary") or {}).get("witness_rows") or 0) >= 4,
            "witness_rows": (map4q.get("summary") or {}).get("witness_rows"),
        },
        "commander_audit": {
            "passed": audit.get("audit_only") is True and audit.get("send_gate") == "HOLD",
        },
        "promotion_lock": {
            "passed": canon_ok,
            "promotion_ok": promo.get("promotion_ok"),
            "note": "mainline canon must stay clean; shadow promotion_ok may be true",
        },
        "canon_jsonl_clean": {"passed": canon_ok, "non_canon_rows": canon_bad},
        "cross_ref_sidecar_only": {
            "passed": (mt.get("track_wall") or {}).get("cross_ref_draft_mutation_forbidden") is True,
        },
    }
    gate_ok = all(c.get("passed") for c in checks.values())
    return {
        "schema": "p5_manuscript_integrity_gate_v1",
        "generated_at_utc": _utc(),
        "hypothesis_tier": "B",
        "research_only": True,
        "non_gating": True,
        "gate_ok": gate_ok,
        "checks": checks,
        "reproduce": "py scripts/build_p5_manuscript_integrity_gate_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    args = ap.parse_args()
    doc = build()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "gate_ok": doc["gate_ok"]}, ensure_ascii=False))
    return 0 if doc["gate_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
