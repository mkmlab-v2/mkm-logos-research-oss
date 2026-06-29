#!/usr/bin/env python3
"""Lint Track L / Logos public-facing copy surfaces vs PUBLIC_FACING v1.7 (local, no network)."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "docs/final/PUBLIC_FACING_SECURITY_AND_IP_COPY_CHECKLIST_V1.md"
DEFAULT_OUT = ROOT / "reports/logos_track_l_public_facing_readiness_v1_latest.json"

SCAN_PATHS = [
    ROOT / "docs/final/LOGOS_HERMENEUTICS_TRACK_L_CHARTER_V1.md",
    ROOT / "docs/final/LOGOS_ORIGINAL_LANGUAGE_GRAPH_RAG_BRIDGE_V1.md",
    ROOT / "docs/final/artifacts/logos_graphrag_bridge_evidence_pack_v1_latest.md",
    ROOT / "docs/final/artifacts/logos_s1_shadow_promotion_review_packet_latest.md",
    ROOT / "docs/final/MKM_PROMOTION_GATE_CHECKLIST_L0_L12_V1.md",
]

FORBIDDEN_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"guaranteed\s+returns?", re.I), "guaranteed_returns"),
    (re.compile(r"clinical\s+proof", re.I), "clinical_proof"),
    (re.compile(r"zero[- ]?liability", re.I), "zero_liability"),
    (re.compile(r"neuroscience[- ]?proven", re.I), "neuroscience_proven"),
    (re.compile(r"신경과학적으로\s*증명", re.I), "ko_neuroscience_proof"),
    (re.compile(r"always\s+profitable", re.I), "always_profitable"),
    (re.compile(r"live\s+trading\s+enabled", re.I), "live_trading_enabled"),
    (re.compile(r"promotion_to_a_track_allowed\s*:\s*true", re.I), "a_track_promotion_true"),
    (re.compile(r"ready_for_external_send\s*:\s*true", re.I), "external_send_true_in_body"),
]

REQUIRED_MARKERS = [
    (re.compile(r"\[NON_GATING\]|non_gating|NON_GATING", re.I), "non_gating_marker"),
    (re.compile(r"research_only|\[HYPO\]", re.I), "hypo_or_research_only"),
]


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(path.resolve().as_posix())


def _scan_file(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {"path": _rel(path), "exists": False, "forbidden_hits": [], "markers_missing": []}
    text = path.read_text(encoding="utf-8", errors="replace")
    forbidden = [code for pat, code in FORBIDDEN_PATTERNS if pat.search(text)]
    missing_markers = [code for pat, code in REQUIRED_MARKERS if not pat.search(text)]
    return {
        "path": _rel(path),
        "exists": True,
        "forbidden_hits": forbidden,
        "markers_missing": missing_markers,
        "ok": not forbidden,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Track L public-facing copy readiness lint")
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--stdout-only", action="store_true")
    args = ap.parse_args()

    evidence = ROOT / "docs/final/artifacts/logos_graphrag_bridge_evidence_pack_v1_latest.json"
    evidence_doc: dict[str, Any] = {}
    if evidence.is_file():
        try:
            evidence_doc = json.loads(evidence.read_text(encoding="utf-8-sig"))
        except json.JSONDecodeError:
            evidence_doc = {}

    file_scans = [_scan_file(p) for p in SCAN_PATHS]
    forbidden_union: list[str] = []
    for row in file_scans:
        forbidden_union.extend(row.get("forbidden_hits") or [])

    checks = {
        "public_facing_checklist": {"exists": PUBLIC.is_file(), "path": _rel(PUBLIC)},
        "evidence_pack_external_send_false": evidence_doc.get("ready_for_external_send") is False,
        "file_scans": file_scans,
        "forbidden_union": sorted(set(forbidden_union)),
    }

    ready_internal = bool(
        checks["public_facing_checklist"]["exists"]
        and checks["evidence_pack_external_send_false"]
        and not forbidden_union
        and all(row.get("exists") for row in file_scans[:3])
    )

    out: dict[str, Any] = {
        "schema": "logos_track_l_public_facing_readiness_v1",
        "generated_at_utc": _utc_now(),
        "ready_for_external_send": False,
        "ready_for_internal_track_c_draft": ready_internal,
        "checks": checks,
        "policy_pointer": _rel(PUBLIC),
        "note": (
            "ready_for_external_send remains false until legal counsel sign-off (L12). "
            "Track L Logos surfaces are [NON_GATING] / research_only."
        ),
    }

    text = json.dumps(out, ensure_ascii=False, indent=2) + "\n"
    if not args.stdout_only:
        out_path = args.output_json if args.output_json.is_absolute() else ROOT / args.output_json
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(text, encoding="utf-8")
    print(json.dumps({"ok": ready_internal, "ready_for_external_send": False}, ensure_ascii=False))
    return 0 if ready_internal else 1


if __name__ == "__main__":
    raise SystemExit(main())
