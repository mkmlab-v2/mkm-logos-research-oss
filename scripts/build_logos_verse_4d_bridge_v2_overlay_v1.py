#!/usr/bin/env python3
"""[HYPO] Build reports-only verse jsonl with bridge_v2 vectors — no data/logos SSOT write."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_IN = ROOT / "data/logos/verse_decoded_v2_single_anchor_v1.jsonl"
DEFAULT_OUT = ROOT / "reports/logos_verse_4d_bridge_v2_overlay_v1_latest.jsonl"
DEFAULT_MANIFEST = ROOT / "reports/logos_verse_4d_bridge_v2_overlay_v1_latest.json"


def _iter_jsonl(path: Path) -> Iterator[dict[str, Any]]:
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                yield json.loads(line)


def main() -> int:
    from scripts.core.gematria_to_4d_bridge_v2_hypo import build_gematria_4d_bridge_v2_hypo

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input-jsonl", type=Path, default=DEFAULT_IN)
    ap.add_argument("--out-jsonl", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--out-manifest", type=Path, default=DEFAULT_MANIFEST)
    ap.add_argument("--max-rows", type=int, default=0)
    args = ap.parse_args()

    if not args.input_jsonl.is_file():
        print(json.dumps({"ok": False, "error": f"missing input: {args.input_jsonl}"}))
        return 2

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    emitted = 0
    skipped = 0

    args.out_jsonl.parent.mkdir(parents=True, exist_ok=True)
    with args.out_jsonl.open("w", encoding="utf-8") as out_f:
        for i, row in enumerate(_iter_jsonl(args.input_jsonl)):
            if args.max_rows and i >= args.max_rows:
                break
            vid = str(row.get("verse_id") or "").strip()
            if not vid:
                skipped += 1
                continue
            vec = build_gematria_4d_bridge_v2_hypo(row)
            out_row = dict(row)
            out_row["vector_4d"] = vec
            out_row["unified_4d_vector"] = dict(vec)
            out_row["bridge_v2_hypo"] = {
                "recipe_id": "gematria_to_4d_bridge_v2_hypo",
                "generated_at_utc": ts,
                "research_only": True,
                "non_gating": True,
                "compression_track_a_touch": False,
            }
            out_f.write(json.dumps(out_row, ensure_ascii=False) + "\n")
            emitted += 1

    manifest = {
        "schema": "logos_verse_4d_bridge_v2_overlay_v1",
        "generated_at_utc": ts,
        "hypothesis_tier": "B",
        "research_only": True,
        "non_gating": True,
        "final_action": "HOLD_EXPLORATION",
        "inputs": {"jsonl": str(args.input_jsonl.relative_to(ROOT)).replace("\\", "/")},
        "outputs": {"overlay_jsonl": str(args.out_jsonl.relative_to(ROOT)).replace("\\", "/")},
        "counts": {"rows_emitted": emitted, "rows_skipped": skipped},
        "track_wall": {"a_track_auto_promotion": False, "compression_track_a_touch": False},
        "note": "Reports-only overlay — do not promote to data/logos SSOT without human sign-off.",
    }
    args.out_manifest.parent.mkdir(parents=True, exist_ok=True)
    args.out_manifest.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "emitted": emitted, "skipped": skipped, "out_jsonl": str(args.out_jsonl)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
