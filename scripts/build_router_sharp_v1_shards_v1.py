#!/usr/bin/env python3
"""Build B-track sharp router shard dir (keyword overlay + tiebreak metadata)."""

from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC_SHARDS = ROOT / "codebook" / "shards"
OVERLAY = ROOT / "docs/final/artifacts/router_sharp_v1_keyword_overlay.json"
OUT_SHARDS = ROOT / "codebook" / "shards_btrack_router_sharp_v1"
OUT_META = ROOT / "reports/constitution/btrack_pilot/router_sharp_v1_shards_build_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src-shards", type=Path, default=SRC_SHARDS)
    ap.add_argument("--overlay-json", type=Path, default=OVERLAY)
    ap.add_argument("--out-dir", type=Path, default=OUT_SHARDS)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    overlay_doc = json.loads(args.overlay_json.read_text(encoding="utf-8-sig"))
    by_shard: dict[str, list[str]] = overlay_doc.get("overlay_by_shard_id") or {}
    tiebreak = overlay_doc.get("tiebreak_priority") or []

    if args.dry_run:
        print(
            json.dumps(
                {
                    "dry_run": True,
                    "shard_overlay_count": len(by_shard),
                    "out_dir": str(args.out_dir.relative_to(ROOT)).replace("\\", "/"),
                },
                ensure_ascii=False,
            )
        )
        return 0

    if args.out_dir.exists():
        shutil.rmtree(args.out_dir)
    args.out_dir.mkdir(parents=True, exist_ok=True)

    patched: list[str] = []
    for src in sorted(args.src_shards.glob("zone_*.json")):
        doc = json.loads(src.read_text(encoding="utf-8-sig"))
        sid = str(doc.get("shard_id", src.stem))
        extra = [str(k).lower() for k in by_shard.get(sid, [])]
        if extra:
            keys = {str(k).lower() for k in doc.get("routing_keywords", [])}
            keys.update(extra)
            doc["routing_keywords"] = sorted(keys)
            patched.append(sid)
        dest = args.out_dir / src.name
        dest.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def _rel(p: Path) -> str:
        try:
            return str(p.resolve().relative_to(ROOT.resolve())).replace("\\", "/")
        except ValueError:
            return str(p.resolve()).replace("\\", "/")

    meta = {
        "schema": "router_sharp_v1_shards_build_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "src_shards": _rel(args.src_shards),
        "overlay_json": _rel(args.overlay_json),
        "out_dir": _rel(args.out_dir),
        "patched_shard_ids": patched,
        "tiebreak_priority": tiebreak,
    }
    OUT_META.parent.mkdir(parents=True, exist_ok=True)
    OUT_META.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (args.out_dir / "_router_sharp_v1_meta.json").write_text(
        json.dumps({"tiebreak_priority": tiebreak}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print(
        json.dumps(
            {
                "out_dir": meta["out_dir"],
                "patched_shard_ids": patched,
                "wrote_meta": str(OUT_META.relative_to(ROOT)).replace("\\", "/"),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
