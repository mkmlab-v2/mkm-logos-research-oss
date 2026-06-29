#!/usr/bin/env python3
"""Analyze mkm-universal-root public export bundle sizes — jsonl slim guidance."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "docs/final/artifacts/mkm_universal_root_public_export_manifest_v1.json"
DEFAULT_OUT = ROOT / "reports/mkm_universal_root_export_size_audit_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--manifest", type=Path, default=MANIFEST)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--top", type=int, default=10)
    args = ap.parse_args()

    manifest = json.loads(args.manifest.read_text(encoding="utf-8-sig"))
    rows: list[dict] = []
    total = 0
    for rel in manifest.get("paths") or []:
        rel_s = str(rel).replace("\\", "/")
        p = ROOT / rel_s
        if p.is_file():
            sz = p.stat().st_size
            total += sz
            rows.append({"path": rel_s, "bytes": sz, "mb": round(sz / 1024 / 1024, 4)})

    rows.sort(key=lambda r: r["bytes"], reverse=True)
    top = rows[: args.top]
    jsonl_rows = [r for r in rows if r["path"].endswith(".jsonl")]
    jsonl_bytes = sum(r["bytes"] for r in jsonl_rows)

    doc = {
        "schema": "mkm_universal_root_export_size_audit_v1",
        "ok": True,
        "generated_at_utc": _utc(),
        "research_only": True,
        "send_gate": "HOLD",
        "manifest": str(args.manifest.relative_to(ROOT)).replace("\\", "/"),
        "file_count": len(rows),
        "total_bytes": total,
        "total_mb": round(total / 1024 / 1024, 4),
        "jsonl_bytes": jsonl_bytes,
        "jsonl_share_of_total": round(jsonl_bytes / total, 4) if total else 0.0,
        "top_files": top,
        "slim_recommendation": {
            "primary_bloat": jsonl_rows[0]["path"] if jsonl_rows else None,
            "options": [
                "Git LFS for verse atom jsonl (document in README; no auto migrate)",
                "Ship prebuilt topology_crosswalk artifact only + optional slim jsonl slice fixture",
                "Split full jsonl to monorepo-only; OSS uses tests/fixtures slice for rebuild smoke",
            ],
            "note": "Smoke currently rebuilds topology via build_universal_root_topology_crosswalk_v1.py — slim requires manifest+script change together",
        },
        "reproduce": "py scripts/analyze_mkm_universal_root_export_size_v1.py",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "total_mb": doc["total_mb"],
                "jsonl_share": doc["jsonl_share_of_total"],
                "primary_bloat": doc["slim_recommendation"]["primary_bloat"],
                "out": str(args.out),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
