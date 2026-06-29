#!/usr/bin/env python3
"""[HYPO] Reports-only GraphRAG patch: add Luke.22.4 path for regime_watch seed gap."""
from __future__ import annotations

import argparse
import json
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "reports/logos_graphrag_2026_regime_watch_latest.json"
DEFAULT_OUT = ROOT / "reports/logos_graphrag_2026_regime_watch_luke_patch_v1_latest.json"
MANIFEST = ROOT / "reports/logos_graphrag_regime_watch_luke_patch_v1_latest.json"
REF_OVERRIDE = ROOT / "reports/logos_graphrag_regime_watch_ref_override_v1.json"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--source-json", type=Path, default=SOURCE)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--out-manifest", type=Path, default=MANIFEST)
    args = ap.parse_args()

    if not args.source_json.is_file():
        print(json.dumps({"ok": False, "error": f"missing source: {args.source_json}"}))
        return 2

    doc = json.loads(args.source_json.read_text(encoding="utf-8-sig"))
    patched = deepcopy(doc)
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    new_path = {
        "bridge_artifact": "docs/final/artifacts/logos_concept_bridge_regime_watchfulness_gemini_v1_latest.json",
        "path_id": "path_4_betrayal_watch_btrack_hypo",
        "steps": [
            "mc_regime_transition_watchfulness",
            "func_spiritual_readiness",
            "lp_gregoreo",
            "vr_luke_22_4",
        ],
        "note_ko": "체제 전환기 배신·음모 징후 — 누가복음 22:4 [HYPO] fixture gap closure (reports-only).",
        "match_score": 3,
    }
    patched.setdefault("paths", []).append(new_path)
    verse_ids = list(patched.get("verse_ids") or [])
    for vid in ("vr_luke_22_4", "greek::Luke.22.4"):
        if vid not in verse_ids:
            verse_ids.append(vid)
    patched["verse_ids"] = verse_ids
    patched["patch_meta"] = {
        "schema": "logos_graphrag_regime_watch_luke_patch_v1",
        "applied_at_utc": ts,
        "hypothesis_tier": "B",
        "research_only": True,
        "source": str(args.source_json.relative_to(ROOT)).replace("\\", "/"),
        "gap_closed_seed": "Luke.22.4",
        "note": "Not promoted to reports/logos_graphrag_2026_regime_watch_latest.json without human sign-off.",
    }

    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(patched, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    manifest = {
        "schema": "logos_graphrag_regime_watch_luke_patch_manifest_v1",
        "generated_at_utc": ts,
        "hypothesis_tier": "B",
        "research_only": True,
        "source": str(args.source_json.relative_to(ROOT)).replace("\\", "/"),
        "patched_output": str(args.out_json.relative_to(ROOT)).replace("\\", "/"),
        "gap_seed": "Luke.22.4",
        "topic_id": "regime_watch_lehman_shadow",
    }
    args.out_manifest.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    ref_override = {
        "regime_watch_lehman_shadow": str(args.out_json.relative_to(ROOT)).replace("\\", "/"),
    }
    REF_OVERRIDE.write_text(json.dumps(ref_override, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(args.out_json), "paths_added": 1, "ref_override": str(REF_OVERRIDE)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
