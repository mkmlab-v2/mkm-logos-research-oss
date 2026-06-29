#!/usr/bin/env python3
"""Human sign-off promotion: Luke.22.4 path → regime_watch GraphRAG SSOT (reports/)."""
from __future__ import annotations

import argparse
import json
import shutil
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "reports/logos_graphrag_2026_regime_watch_latest.json"
PATCHED = ROOT / "reports/logos_graphrag_2026_regime_watch_luke_patch_v1_latest.json"
SIGNOFF = ROOT / "reports/logos_graphrag_regime_watch_luke_promotion_signoff_v1_latest.json"


def _apply_luke_delta(doc: dict, ts: str) -> dict:
    out = deepcopy(doc)
    new_path = {
        "bridge_artifact": "docs/final/artifacts/logos_concept_bridge_regime_watchfulness_gemini_v1_latest.json",
        "path_id": "path_4_betrayal_watch_btrack_hypo",
        "steps": [
            "mc_regime_transition_watchfulness",
            "func_spiritual_readiness",
            "lp_gregoreo",
            "vr_luke_22_4",
        ],
        "note_ko": "체제 전환기 배신·음모 징후 — 누가복음 22:4 [HYPO] human sign-off promoted.",
        "match_score": 3,
    }
    paths = list(out.get("paths") or [])
    if not any(p.get("path_id") == new_path["path_id"] for p in paths if isinstance(p, dict)):
        paths.append(new_path)
    out["paths"] = paths
    verse_ids = list(out.get("verse_ids") or [])
    for vid in ("vr_luke_22_4", "greek::Luke.22.4"):
        if vid not in verse_ids:
            verse_ids.append(vid)
    out["verse_ids"] = verse_ids
    out["generated_at_utc"] = ts
    out.pop("patch_meta", None)
    out["promotion_signoff"] = {
        "schema": "logos_graphrag_regime_watch_luke_promotion_signoff_v1",
        "approved_at_utc": ts,
        "hypothesis_tier": "B",
        "research_only": True,
        "non_gating": True,
        "gap_closed_seed": "Luke.22.4",
        "topic_id": "regime_watch_lehman_shadow",
        "approver": "human_signoff",
        "track_wall": "B_track_not_track_A",
    }
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--target-json", type=Path, default=TARGET)
    ap.add_argument("--from-patched", type=Path, default=PATCHED)
    ap.add_argument("--out-signoff", type=Path, default=SIGNOFF)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    if args.from_patched.is_file():
        base = json.loads(args.from_patched.read_text(encoding="utf-8-sig"))
        promoted = deepcopy(base)
        promoted.pop("patch_meta", None)
        promoted["generated_at_utc"] = ts
        if promoted.get("paths"):
            for p in promoted["paths"]:
                if isinstance(p, dict) and p.get("path_id") == "path_4_betrayal_watch_btrack_hypo":
                    p["note_ko"] = "체제 전환기 배신·음모 징후 — 누가복음 22:4 [HYPO] human sign-off promoted."
        promoted["promotion_signoff"] = {
            "schema": "logos_graphrag_regime_watch_luke_promotion_signoff_v1",
            "approved_at_utc": ts,
            "hypothesis_tier": "B",
            "research_only": True,
            "non_gating": True,
            "gap_closed_seed": "Luke.22.4",
            "topic_id": "regime_watch_lehman_shadow",
            "approver": "human_signoff",
            "track_wall": "B_track_not_track_A",
            "source_patch": str(args.from_patched.relative_to(ROOT)).replace("\\", "/"),
        }
    elif args.target_json.is_file():
        base = json.loads(args.target_json.read_text(encoding="utf-8-sig"))
        promoted = _apply_luke_delta(base, ts)
    else:
        print(json.dumps({"ok": False, "error": "missing patched and target json"}))
        return 2

    backup = args.target_json.with_suffix(args.target_json.suffix + ".pre_luke_promotion.bak")
    if args.dry_run:
        print(json.dumps({"ok": True, "dry_run": True, "would_write": str(args.target_json), "luke_in_verse_ids": "Luke.22.4" in json.dumps(promoted)}))
        return 0

    if args.target_json.is_file():
        shutil.copy2(args.target_json, backup)
    args.target_json.parent.mkdir(parents=True, exist_ok=True)
    args.target_json.write_text(json.dumps(promoted, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    signoff = {
        "schema": "logos_graphrag_regime_watch_luke_promotion_signoff_v1",
        "approved_at_utc": ts,
        "ok": True,
        "hypothesis_tier": "B",
        "research_only": True,
        "target": str(args.target_json.relative_to(ROOT)).replace("\\", "/"),
        "backup": str(backup.relative_to(ROOT)).replace("\\", "/") if backup.is_file() else None,
        "gap_closed_seed": "Luke.22.4",
    }
    args.out_signoff.write_text(json.dumps(signoff, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "target": str(args.target_json), "signoff": str(args.out_signoff)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
