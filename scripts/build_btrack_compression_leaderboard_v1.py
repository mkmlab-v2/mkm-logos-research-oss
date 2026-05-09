#!/usr/bin/env python3
"""Merge Day1 summary, cap62 reference, optional decoder benchmark pointers into one leaderboard JSON."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "final" / "artifacts" / "btrack_compression_leaderboard_latest.json"
DAY1 = ROOT / "docs" / "final" / "artifacts" / "btrack_day1_three_band_summary_latest.json"
CAP62 = ROOT / "docs" / "final" / "artifacts" / "track_a_week22_e2_candidate_pool_spike_cap62_v1.json"


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(p: Path) -> dict[str, Any]:
    return json.loads(p.read_text(encoding="utf-8-sig"))


def _row_from_cap62(doc: dict[str, Any]) -> dict[str, Any]:
    m = doc.get("metrics") or {}
    inp = doc.get("inputs") or {}
    caps = inp.get("caps") or {}
    return {
        "source": "week22_cap62_reference",
        "label": "cap62_like_reference",
        "artifact": "docs/final/artifacts/track_a_week22_e2_candidate_pool_spike_cap62_v1.json",
        "saving": float(m.get("global_token_saving_rate", 0.0)),
        "jaccard": float(m.get("avg_reconstruction_fidelity_jaccard", 0.0)),
        "integrity": float(m.get("avg_sensitive_integrity", 0.0)),
        "caps": caps,
        "decision": doc.get("decision"),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--day1", type=Path, default=DAY1)
    ap.add_argument("--cap62", type=Path, default=CAP62)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()

    day1 = _load(args.day1)
    rows: list[dict[str, Any]] = []
    for r in day1.get("rows") or []:
        rows.append(
            {
                "source": "day1_three_band",
                "band_id": r.get("band_id"),
                "label": r.get("artifact_relative", "").split("/")[-1].replace(".json", ""),
                "artifact": r.get("artifact_relative"),
                "saving": float(r.get("saving", 0.0)),
                "jaccard": float(r.get("jaccard", 0.0)),
                "integrity": float(r.get("integrity", 0.0)),
                "caps": r.get("caps"),
                "decision": r.get("decision"),
            }
        )

    if args.cap62.is_file():
        rows.append(_row_from_cap62(_load(args.cap62)))

    integrity_ok = [x for x in rows if float(x.get("integrity") or 0) >= 1.0]
    ranked = sorted(
        integrity_ok,
        key=lambda x: (float(x.get("saving", 0.0)), float(x.get("jaccard", 0.0))),
        reverse=True,
    )

    out = {
        "schema": "btrack_compression_leaderboard_v1",
        "generated_at_utc": _utc(),
        "lane": "research_only",
        "inputs": {"day1": str(args.day1), "cap62": str(args.cap62) if args.cap62.is_file() else None},
        "best_overall": ranked[0] if ranked else None,
        "ranked_integrity_1": ranked,
        "notes": [
            "Rank key: saving desc, then jaccard desc, among integrity>=1.0 rows only.",
            "Week22 cap62 row is historical reference artifact for comparison.",
        ],
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(args.out), "best_saving": ranked[0]["saving"] if ranked else None}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
