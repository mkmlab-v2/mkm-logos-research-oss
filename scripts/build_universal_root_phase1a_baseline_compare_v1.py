#!/usr/bin/env python3
"""Phase 1A — 500-pair baseline vs dual-plane comparison table [HYPO · HOLD]."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
CROSSWALK = ROOT / "reports/universal_root_topology_crosswalk_v1_latest.json"
OUT = ROOT / "reports/universal_root_phase1a_baseline_compare_v1_latest.json"
BUILDER = ROOT / "scripts/build_universal_root_topology_crosswalk_v1.py"


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _read(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _rate(num: int, den: int) -> float | None:
    if den <= 0:
        return None
    return round(num / den, 4)


def recompute_b0_english_only_rate(crosswalk: dict[str, Any], audit: dict[str, Any]) -> float | None:
    """Same counting path as _build_comparison B0 (crosswalk rows + audit en_hit)."""
    audit_rows = ((audit.get("baseline") or {}).get("rows")) or []
    rows_by_prime = {str(r.get("prime_en") or ""): r for r in audit_rows if r.get("prime_en")}
    en_only_hits = 0
    non_control = 0
    for row in crosswalk.get("rows") or []:
        if str(row.get("control") or "") == "negative":
            continue
        non_control += 1
        prime = str(row.get("prime_en") or "")
        audit_row = rows_by_prime.get(prime, {})
        if bool(audit_row.get("en_hit")):
            en_only_hits += 1
    return _rate(en_only_hits, non_control)


def _build_comparison(crosswalk: dict[str, Any], audit: dict[str, Any]) -> dict[str, Any]:
    rows = crosswalk.get("rows") or []
    baseline = audit.get("baseline") or {}
    non_control = int(crosswalk.get("summary", {}).get("non_control_pairs") or baseline.get("non_control_pairs") or 0)
    neg_control = int(baseline.get("negative_control_pairs") or 0)

    audit_by_prime = {
        str(r.get("prime_en") or ""): r
        for r in (baseline.get("rows") or [])
        if r.get("prime_en")
    }

    en_only_hits = 0
    lexicon_hits = 0
    topology_hits = 0
    dual_aligned = 0
    collapsed_or = 0
    gap_both = 0

    for row in rows:
        if str(row.get("control") or "") == "negative":
            continue
        prime = str(row.get("prime_en") or "")
        audit_row = audit_by_prime.get(prime, {})
        en_hit = bool(audit_row.get("en_hit"))
        lh = bool(row.get("lexicon_hit"))
        th = bool(row.get("topology_reachable"))
        if en_hit:
            en_only_hits += 1
        if lh:
            lexicon_hits += 1
        if th:
            topology_hits += 1
        if lh and th:
            dual_aligned += 1
        if lh or th:
            collapsed_or += 1
        if not lh and not th:
            gap_both += 1

    wall = crosswalk.get("wall_divergence") or {}
    lexicon_plane = crosswalk.get("lexicon_plane") or {}
    topology_plane = crosswalk.get("topology_plane") or {}

    methods: list[dict[str, Any]] = [
        {
            "id": "B0",
            "name": "english_only_naive",
            "description": "English probe hit only (no multilingual lexicon gate)",
            "primary_metric": "english_only_hit_rate",
            "primary_value": _rate(en_only_hits, non_control),
            "pair_count": non_control,
            "hits": en_only_hits,
            "raw": {"english_only_distortion_rate": lexicon_plane.get("english_only_distortion_rate")},
        },
        {
            "id": "B1",
            "name": "lexicon_plane",
            "description": "41k lexicon multilingual prime hit (audit baseline)",
            "primary_metric": "prime_hit_rate",
            "primary_value": lexicon_plane.get("prime_hit_rate"),
            "pair_count": non_control,
            "hits": lexicon_hits,
        },
        {
            "id": "B2",
            "name": "topology_plane",
            "description": "31k verse topology reachability without lexicon gate",
            "primary_metric": "verse_reachable_rate",
            "primary_value": topology_plane.get("verse_reachable_rate"),
            "pair_count": non_control,
            "hits": topology_hits,
        },
        {
            "id": "B3",
            "name": "dual_plane_aligned",
            "description": "Both lexicon and topology planes hit (MKM dual-plane integrity)",
            "primary_metric": "dual_plane_aligned_rate",
            "primary_value": _rate(dual_aligned, non_control),
            "pair_count": non_control,
            "hits": dual_aligned,
            "wall_lexicon_only_without_topology": wall.get("lexicon_only_without_topology"),
            "wall_topology_only_without_lexicon": wall.get("topology_only_without_lexicon"),
            "wall_gap_both_planes": wall.get("gap_both_planes"),
        },
        {
            "id": "B4",
            "name": "collapsed_or_forbidden",
            "description": "Lexicon OR topology (single headline — forbidden for public copy)",
            "primary_metric": "collapsed_or_rate",
            "primary_value": _rate(collapsed_or, non_control),
            "pair_count": non_control,
            "hits": collapsed_or,
            "forbidden_headline": True,
        },
    ]

    dual_rate = _rate(dual_aligned, non_control)
    lex_rate = float(lexicon_plane.get("prime_hit_rate") or 0)
    topo_rate = float(topology_plane.get("verse_reachable_rate") or 0)

    return {
        "schema": "universal_root_phase1a_baseline_compare_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "research_only": True,
        "send_gate": "HOLD",
        "fixture": crosswalk.get("fixture") or "tests/fixtures/nsm_41k_lexicon_crosswalk_500_v1.json",
        "pair_count": int(crosswalk.get("summary", {}).get("pair_count") or 500),
        "non_control_pairs": non_control,
        "negative_control_pairs": neg_control,
        "methods": methods,
        "headline_table": [
            {
                "method": m["name"],
                "metric": m["primary_metric"],
                "value": m["primary_value"],
                "note": "forbidden" if m.get("forbidden_headline") else "reportable_raw",
            }
            for m in methods
        ],
        "delta_dual_minus_lexicon": round((dual_rate or 0) - lex_rate, 4) if dual_rate is not None else None,
        "delta_dual_minus_topology": round((dual_rate or 0) - topo_rate, 4) if dual_rate is not None else None,
        "interpretation": (
            "Dual-plane reports B1/B2 separately; B3 is stricter aligned subset. "
            "Do not publish B4 as model quality."
        ),
        "crosswalk_pointer": "reports/universal_root_topology_crosswalk_v1_latest.json",
        "reproduce": "py scripts/build_universal_root_phase1a_baseline_compare_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--skip-crosswalk-build", action="store_true")
    ap.add_argument("--crosswalk", type=Path, default=CROSSWALK)
    ap.add_argument(
        "--lexicon-audit",
        type=Path,
        default=ROOT / "reports/nsm_41k_lexicon_crosswalk_audit_hf_checkpoint_v1_latest.json",
    )
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()

    if not args.skip_crosswalk_build:
        proc = subprocess.run([PY, str(BUILDER)], cwd=str(ROOT), capture_output=True, text=True, check=False)
        if proc.returncode != 0:
            print(json.dumps({"ok": False, "error": "crosswalk_build_failed", "tail": (proc.stderr or proc.stdout)[-400:]}))
            return 1

    crosswalk = _read(args.crosswalk)
    audit = _read(args.lexicon_audit)
    if not crosswalk.get("rows"):
        print(json.dumps({"ok": False, "error": "missing_crosswalk_rows"}))
        return 2
    if not audit.get("baseline"):
        print(json.dumps({"ok": False, "error": "missing_lexicon_audit"}))
        return 2

    doc = _build_comparison(crosswalk, audit)
    doc["ok"] = True
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "out": str(args.out),
                "dual_plane_aligned_rate": next(m["primary_value"] for m in doc["methods"] if m["id"] == "B3"),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
