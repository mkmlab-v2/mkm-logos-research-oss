#!/usr/bin/env python3
"""B-track router sharp v2: v1 keyword overlay + legacy routing trim (research shard dir)."""

from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC_SHARDS = ROOT / "codebook" / "shards"
V1_OVERLAY = ROOT / "docs/final/artifacts/router_sharp_v1_keyword_overlay.json"
V2_TRIM = ROOT / "docs/final/artifacts/router_sharp_v2_legacy_trim_overlay.json"
OUT_SHARDS = ROOT / "codebook" / "shards_btrack_router_sharp_v2"
OUT_META = ROOT / "reports/constitution/btrack_pilot/router_sharp_v2_shards_build_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rel(p: Path) -> str:
    try:
        return str(p.resolve().relative_to(ROOT.resolve())).replace("\\", "/")
    except ValueError:
        return str(p.resolve()).replace("\\", "/")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src-shards", type=Path, default=SRC_SHARDS)
    ap.add_argument("--v1-overlay-json", type=Path, default=V1_OVERLAY)
    ap.add_argument("--v2-trim-json", type=Path, default=V2_TRIM)
    ap.add_argument("--out-dir", type=Path, default=OUT_SHARDS)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    v1 = json.loads(args.v1_overlay_json.read_text(encoding="utf-8-sig"))
    v2 = json.loads(args.v2_trim_json.read_text(encoding="utf-8-sig"))
    add_kw: dict[str, list[str]] = v1.get("overlay_by_shard_id") or {}
    remove_kw: dict[str, list[str]] = v2.get("remove_routing_keywords_by_shard_id") or {}
    tiebreak = v1.get("tiebreak_priority") or []

    if args.dry_run:
        print(json.dumps({"dry_run": True, "out_dir": _rel(args.out_dir)}, ensure_ascii=False))
        return 0

    if args.out_dir.exists():
        shutil.rmtree(args.out_dir)
    args.out_dir.mkdir(parents=True, exist_ok=True)

    patched_add: list[str] = []
    patched_trim: list[str] = []
    for src in sorted(args.src_shards.glob("zone_*.json")):
        doc = json.loads(src.read_text(encoding="utf-8-sig"))
        sid = str(doc.get("shard_id", src.stem))
        keys = {str(k).lower() for k in doc.get("routing_keywords", [])}
        extra = [str(k).lower() for k in add_kw.get(sid, [])]
        if extra:
            keys.update(extra)
            patched_add.append(sid)
        for rk in remove_kw.get(sid, []):
            keys.discard(str(rk).lower())
        if remove_kw.get(sid):
            patched_trim.append(sid)
        doc["routing_keywords"] = sorted(keys)
        (args.out_dir / src.name).write_text(
            json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )

    meta = {
        "schema": "router_sharp_v2_shards_build_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "out_dir": _rel(args.out_dir),
        "patched_add_shard_ids": patched_add,
        "patched_trim_shard_ids": patched_trim,
        "tiebreak_priority": tiebreak,
    }
    OUT_META.parent.mkdir(parents=True, exist_ok=True)
    OUT_META.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (args.out_dir / "_router_sharp_v1_meta.json").write_text(
        json.dumps({"tiebreak_priority": tiebreak}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"out_dir": meta["out_dir"], "trim": patched_trim}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
