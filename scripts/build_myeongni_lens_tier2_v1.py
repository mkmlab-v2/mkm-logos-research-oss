#!/usr/bin/env python3
"""Myeongni lens Tier2 — corpus router + mid-horizon state [HYPO][NON_GATING]."""
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

DEFAULT_LENS = ROOT / "docs/final/artifacts/myeongni_independent_lens_latest.json"
DEFAULT_ROUTER = ROOT / "reports/btrack_lens_graphrag_myeongni_corpus_v1_latest.json"
DEFAULT_STATE = ROOT / "data/myeongni/16_STATE_MASTER_PROBE_v1.json"
DEFAULT_OUT = ROOT / "reports/myeongni_lens_tier2_v1_latest.json"
DEFAULT_ART = ROOT / "docs/final/artifacts/myeongni_lens_tier2_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        obj = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return None
    return obj if isinstance(obj, dict) else None


def build_myeongni_tier2(*, lens: dict[str, Any] | None, router: dict[str, Any] | None) -> dict[str, Any]:
    scores = (lens or {}).get("scores") if isinstance((lens or {}).get("scores"), dict) else {}
    paths = router.get("paths") if isinstance(router, dict) else []
    if not isinstance(paths, list):
        paths = []
    top_paths = [
        {
            "path_id": p.get("path_id"),
            "chunk_id": p.get("chunk_id"),
            "match_score": p.get("match_score"),
            "note_ko": p.get("note_ko"),
        }
        for p in paths[:5]
        if isinstance(p, dict)
    ]
    return {
        "schema": "myeongni_lens_tier2_v1",
        "generated_at_utc": _utc(),
        "hypothesis_tier": "B",
        "research_only": True,
        "non_gating": True,
        "lens_id": "myeongni",
        "gating_weight": 0.0,
        "tier2_role": "mid_horizon_corpus_router",
        "horizon_contract": "mid_10d",
        "direction_score": scores.get("direction_score"),
        "confidence": scores.get("confidence"),
        "corpus_paths": top_paths,
        "chunk_hits": router.get("chunk_hits") if isinstance(router, dict) else 0,
        "advisory_ko": "명리 Tier2: 중기 타이밍·일진 흐름 해설만 — direction head 미승격.",
        "forbidden": ["auto_direction_flip", "track_a_merge"],
        "send_gate": "HOLD",
        "pointers": {
            "corpus_router": "reports/btrack_lens_graphrag_myeongni_corpus_v1_latest.json",
            "state_probe": "data/myeongni/16_STATE_MASTER_PROBE_v1.json",
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--query", default="코스피 급락 후 명리 중기 타이밍 관측 일진 흐름")
    ap.add_argument("--lens-json", type=Path, default=DEFAULT_LENS)
    ap.add_argument("--router-json", type=Path, default=DEFAULT_ROUTER)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--skip-router-rebuild", action="store_true")
    args = ap.parse_args()

    if not args.skip_router_rebuild:
        subprocess.run(
            [PY, "scripts/build_myeongni_corpus_graphrag_router_v1.py", "--query", args.query],
            cwd=str(ROOT),
            check=False,
        )

    doc = build_myeongni_tier2(lens=_read(args.lens_json), router=_read(args.router_json))
    payload = json.dumps(doc, ensure_ascii=False, indent=2) + "\n"
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(payload, encoding="utf-8")
    DEFAULT_ART.parent.mkdir(parents=True, exist_ok=True)
    DEFAULT_ART.write_text(payload, encoding="utf-8")
    print(json.dumps({"ok": True, "corpus_paths": len(doc["corpus_paths"]), "out": str(args.out_json)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
