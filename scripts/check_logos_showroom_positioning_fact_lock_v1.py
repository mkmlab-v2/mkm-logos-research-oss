#!/usr/bin/env python3
"""Fact-Lock guard: showroom positioning SSOT + forbidden overclaim scan ([HYPO], B-track)."""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SSOT = ROOT / "docs/final/artifacts/logos_showroom_positioning_fact_lock_v1_latest.json"
DEFAULT_OUT = ROOT / "reports/logos_showroom_positioning_fact_lock_gate_v1_latest.json"

# PUBLIC_FACING §2 — showroom lattice must not leak proprietary theory tokens.
LATTICE_INTERNAL_TERM_FORBIDDEN = (
    "甲木",
    "금화",
    "금화교역",
    "보명지주",
    "병증약리",
    "보명지조",
)

SCAN_PATHS = [
    ROOT / "docs/final/artifacts/showroom_meaning_topology_qa_presets_v1_latest.json",
    ROOT
    / "projects/bitcoin-trading/ops/windows-rehearsal/jemaai-cloud-mvp/public_showroom_logos_oracle_v6.html",
    ROOT
    / "projects/bitcoin-trading/ops/windows-rehearsal/jemaai-cloud-mvp/showroom_meaning_topology_qa_presets_v1.json",
    ROOT
    / "projects/bitcoin-trading/ops/windows-rehearsal/jemaai-cloud-mvp/showroom_era_insight_lattice_v1.json",
    ROOT / "docs/final/artifacts/showroom_era_insight_lattice_genesis_v1_latest.json",
    ROOT / "docs/final/artifacts/logos_showroom_v6_staging_performance_profile_v1_latest.json",
]


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(path)


def _scan_forbidden(text: str, patterns: list[str]) -> list[str]:
    hits: list[str] = []
    lower = text.lower()
    for pat in patterns:
        if not pat.strip():
            continue
        if pat.lower() in lower:
            hits.append(pat)
    return hits


def _check_ssot_structure(doc: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    if doc.get("schema") != "logos_showroom_positioning_fact_lock_v1":
        failures.append("schema mismatch")
    for key in ("products", "allowed_claims_ko", "forbidden_claims_ko", "one_liner_ko"):
        if key not in doc:
            failures.append(f"missing key: {key}")
    v6 = (doc.get("products") or {}).get("logos_oracle_v6") or {}
    orb = (doc.get("products") or {}).get("magic_orb_graph_bloom") or {}
    if v6.get("hot_path") is None:
        failures.append("products.logos_oracle_v6.hot_path missing")
    if orb.get("node_cap") != 64:
        failures.append("magic_orb node_cap must be 64")
    if "64" in str(v6.get("engine", "")):
        failures.append("v6 engine must not claim 64-node cap")
    return failures


def check(*, ssot_path: Path, scan_paths: list[Path]) -> dict[str, Any]:
    ssot = json.loads(ssot_path.read_text(encoding="utf-8-sig"))
    struct_failures = _check_ssot_structure(ssot)

    forbidden = list(ssot.get("forbidden_claims_ko") or []) + list(
        ssot.get("forbidden_claims_en") or []
    )
    scan_results: list[dict[str, Any]] = []
    content_failures: list[str] = []

    for path in scan_paths:
        if not path.is_file():
            content_failures.append(f"missing scan file: {_rel(path)}")
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        hits = _scan_forbidden(text, forbidden)
        scan_results.append({"path": _rel(path), "forbidden_hits": hits})
        if hits:
            content_failures.append(f"{path.name}: forbidden {hits}")

    presets_path = ROOT / "docs/final/artifacts/showroom_meaning_topology_qa_presets_v1_latest.json"
    preset_checks: dict[str, Any] = {}
    if presets_path.is_file():
        presets = json.loads(presets_path.read_text(encoding="utf-8-sig"))
        fb = presets.get("fallback") or {}
        preset_checks["fallback_abstention"] = fb.get("abstention") is True
        preset_checks["fallback_empty_highlights"] = not (fb.get("highlight_node_ids") or [])
        genesis = next(
            (p for p in (presets.get("presets") or []) if p.get("id") == "era_genesis_order_and_fall"),
            None,
        )
        if genesis:
            kws = [str(x).lower() for x in (genesis.get("keywords") or [])]
            preset_checks["genesis_has_우주"] = "우주" in kws
            preset_checks["genesis_has_창조"] = "창조" in kws
        else:
            content_failures.append("missing era_genesis_order_and_fall preset")
        if fb.get("abstention") is not True:
            content_failures.append("fallback abstention not true")
        if fb.get("highlight_node_ids"):
            content_failures.append("fallback highlight_node_ids must be empty")

    lattice_paths = [
        ROOT
        / "projects/bitcoin-trading/ops/windows-rehearsal/jemaai-cloud-mvp/showroom_era_insight_lattice_v1.json",
        ROOT / "docs/final/artifacts/showroom_era_insight_lattice_genesis_v1_latest.json",
    ]
    lattice_checks: dict[str, Any] = {"internal_term_hits": []}
    for lp in lattice_paths:
        if not lp.is_file():
            continue
        text = lp.read_text(encoding="utf-8", errors="replace")
        hits = [t for t in LATTICE_INTERNAL_TERM_FORBIDDEN if t in text]
        if hits:
            lattice_checks["internal_term_hits"].append({"path": _rel(lp), "terms": hits})
            content_failures.append(f"{lp.name}: internal theory leak {hits}")

    gate_failures = struct_failures + content_failures
    ok = len(gate_failures) == 0

    return {
        "schema": "logos_showroom_positioning_fact_lock_gate_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypothesis_tier": "B",
        "non_gating": True,
        "send_gate": "HOLD",
        "ok": ok,
        "gate_pass": ok,
        "gate_failures": gate_failures,
        "ssot_path": _rel(ssot_path),
        "scan_results": scan_results,
        "preset_checks": preset_checks,
        "lattice_checks": lattice_checks,
        "reproducible_command": "py scripts/check_logos_showroom_positioning_fact_lock_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--ssot", type=Path, default=DEFAULT_SSOT)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    if not args.ssot.is_file():
        print(f"missing ssot: {args.ssot}", file=sys.stderr)
        return 2

    doc = check(ssot_path=args.ssot, scan_paths=SCAN_PATHS)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc["ok"], "gate_failures": doc["gate_failures"], "out": str(args.output)}, ensure_ascii=False))
    return 0 if doc["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
