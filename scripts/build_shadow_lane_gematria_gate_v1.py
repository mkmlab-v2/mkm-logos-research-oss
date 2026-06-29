#!/usr/bin/env python3
"""Gate: shadow appendix gematria isolated from Logos core 31k/41k paths [HYPO]."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
APPENDIX = ROOT / "reports/shadow_lane_appendix_gematria_v1_latest.json"
XREF = ROOT / "reports/shadow_canon_gematria_xref_map_v1_latest.json"
CANON_JSONL = ROOT / "reports/constitution/btrack_pilot/logos_verse_4d_v1_latest.jsonl"
OUT_DEFAULT = ROOT / "docs/final/artifacts/shadow_lane_gematria_gate_v1_latest.json"

# Mainline builders must NOT default-load appendix gematria (opt-in only).
MAINLINE_SCRIPTS = [
    "scripts/build_logos_key_verses_shadow_v1.py",
    "scripts/run_logos_track_b_themed_deep_push_v1.py",
    "scripts/build_logos_track_b_integration_closure_v1.py",
    "scripts/sync_compression_bench_to_audit_smoke_v1.py",
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


def _mainline_isolation_ok() -> tuple[bool, list[dict[str, Any]]]:
    needle = "shadow_lane_appendix_gematria"
    results: list[dict[str, Any]] = []
    all_ok = True
    for rel in MAINLINE_SCRIPTS:
        path = ROOT / rel
        if not path.is_file():
            results.append({"script": rel, "ok": False, "reason": "missing"})
            all_ok = False
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        hit = needle in text
        results.append({"script": rel, "ok": not hit, "references_appendix_default": hit})
        if hit:
            all_ok = False
    return all_ok, results


def _canon_has_no_apo_dss() -> tuple[bool, int]:
    bad = 0
    if not CANON_JSONL.is_file():
        return False, 0
    with CANON_JSONL.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            vid = str(row.get("verse_id") or "")
            if vid.startswith("apo:") or vid.lower().startswith("dss"):
                bad += 1
    return bad == 0, bad


def build() -> dict[str, Any]:
    appendix = _load(APPENDIX)
    xref = _load(XREF)
    iso_ok, iso_detail = _mainline_isolation_ok()
    canon_ok, canon_bad = _canon_has_no_apo_dss()

    checks = {
        "appendix_present": {
            "passed": appendix.get("schema") == "shadow_lane_appendix_gematria_v1",
            "rows": (appendix.get("summary") or {}).get("total_rows"),
        },
        "xref_present": {
            "passed": xref.get("schema") == "shadow_canon_gematria_xref_map_v1",
            "mapped_links": (xref.get("summary") or {}).get("mapped_links"),
        },
        "mainline_no_default_appendix_load": {
            "passed": iso_ok,
            "scripts": iso_detail,
        },
        "canon_jsonl_no_apo_dss": {
            "passed": canon_ok,
            "non_canon_verse_rows": canon_bad,
        },
        "track_wall_flags": {
            "passed": (appendix.get("track_wall") or {}).get("merge_into_canon_31k_41k") is False,
            "value": appendix.get("track_wall"),
        },
    }
    gate_ok = all(c.get("passed") for c in checks.values())

    return {
        "schema": "shadow_lane_gematria_gate_v1",
        "generated_at_utc": _utc(),
        "hypothesis_tier": "B",
        "research_only": True,
        "non_gating": True,
        "gate_ok": gate_ok,
        "checks": checks,
        "opt_in_flag": "--include-shadow-gematria-appendix",
        "track_wall": {
            "logos_core_mutation_forbidden": True,
            "send_gate": "HOLD",
        },
        "reproduce": "py scripts/build_shadow_lane_gematria_gate_v1.py",
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
