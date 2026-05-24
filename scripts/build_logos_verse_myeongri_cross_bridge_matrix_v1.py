#!/usr/bin/env python3
"""Track B: top-N medoid verses × multiple human Myeongri 4D profiles — L2/cosine matrix."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.build_logos_verse_myeongri_cross_bridge_v1 import (  # noqa: E402
    DEFAULT_MEDOID_MANIFEST,
    DEFAULT_VERSE_JSONL,
    _load_verse_row,
    _rel,
    _sha256_file,
    resolve_human_profiles,
)

DEFAULT_OUT = ROOT / "docs/final/artifacts/logos_verse_myeongri_cross_bridge_matrix_v1_latest.json"
SCHEMA = "logos_verse_myeongri_cross_bridge_matrix_v1"
VERSION = "1.1.0"


def build_matrix(
    *,
    verse_jsonl: Path,
    medoid_manifest: Path,
    top_n: int,
    human_profiles: list[dict[str, Any]],
) -> dict[str, Any]:
    from tools.myeongni.gematria_myeongri_math_v1 import cosine_similarity, l2_distance

    medoids_doc = json.loads(medoid_manifest.read_text(encoding="utf-8"))
    medoid_rows = (medoids_doc.get("global_medoids") or [])[:top_n]

    rows_out: list[dict[str, Any]] = []
    unique_vectors: set[tuple[float, float, float, float]] = set()

    for row in medoid_rows:
        if not isinstance(row, dict):
            continue
        verse_id = str(row["verse_id"])
        verse_row = _load_verse_row(verse_jsonl, verse_id)
        os_vec = verse_row["vector_4d"]
        key = tuple(round(float(os_vec[k]), 8) for k in ("S", "L", "K", "M"))
        unique_vectors.add(key)

        per_human: dict[str, Any] = {}
        for hp in human_profiles:
            pid = str(hp["profile_id"])
            hvec = hp["vector_4d"]
            per_human[pid] = {
                "l2_os_human": round(l2_distance(os_vec, hvec), 8),
                "cosine_os_human": round(cosine_similarity(os_vec, hvec), 8),
            }

        rows_out.append(
            {
                "rank": int(row["rank"]),
                "verse_id": verse_id,
                "centrality": float(row.get("centrality") or 0),
                "vector_4d": {k: float(os_vec[k]) for k in ("S", "L", "K", "M")},
                "geometry_by_profile": per_human,
            }
        )

    return {
        "schema": SCHEMA,
        "version": VERSION,
        "subset_id": "v1_core_subset",
        "ts_utc": datetime.now(timezone.utc).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "hypothesis_tier": "B",
        "boundary_ack": True,
        "interpretation_note": (
            "[HYPO] Medoid verse gematria-bridge 4D vs one or more Myeongri birth 4D profiles. "
            "Identical L2/cosine across verses indicates duplicate vector_4d under the bridge recipe, "
            "not theological equivalence. Not clinical or trading proof."
        ),
        "human_profiles": [
            {
                "profile_id": hp["profile_id"],
                "birth_instant_utc": hp.get("birth_instant_utc"),
                "iana_tz": hp.get("iana_tz"),
                "vector_4d": hp["vector_4d"],
                "ssot": hp.get("ssot"),
            }
            for hp in human_profiles
        ],
        "rows": rows_out,
        "summary": {
            "medoid_count": len(rows_out),
            "human_profile_count": len(human_profiles),
            "unique_verse_vector_4d_count": len(unique_vectors),
            "vector_4d_collapse_note": (
                "When unique_verse_vector_4d_count < medoid_count, gematria_bridge maps "
                "distinct verses to the same (S,L,K,M) — report hub rank separately from coordinate diversity."
            ),
        },
        "inputs": {
            "verse_4d_jsonl": _rel(verse_jsonl),
            "verse_4d_jsonl_sha256": _sha256_file(verse_jsonl),
            "medoid_manifest": _rel(medoid_manifest),
            "top_n": top_n,
        },
        "track_wall": {
            "a_track_auto_promotion": False,
            "live_trading_trigger": False,
            "ready_for_external_send": False,
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--verse-jsonl", type=Path, default=DEFAULT_VERSE_JSONL)
    ap.add_argument("--medoid-manifest", type=Path, default=DEFAULT_MEDOID_MANIFEST)
    ap.add_argument("--top-n", type=int, default=10)
    ap.add_argument(
        "--profile-id",
        action="append",
        dest="profile_ids",
        help="Repeatable; default = all STANDARD_HUMAN_PROFILES",
    )
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    verse_jsonl = args.verse_jsonl if args.verse_jsonl.is_absolute() else ROOT / args.verse_jsonl
    medoid_manifest = (
        args.medoid_manifest if args.medoid_manifest.is_absolute() else ROOT / args.medoid_manifest
    )
    if not verse_jsonl.is_file() or not medoid_manifest.is_file():
        print("missing verse jsonl or medoid manifest", file=sys.stderr)
        return 1

    profiles = resolve_human_profiles(args.profile_ids or None)
    doc = build_matrix(
        verse_jsonl=verse_jsonl,
        medoid_manifest=medoid_manifest,
        top_n=max(1, int(args.top_n)),
        human_profiles=profiles,
    )
    out_path = args.out_json if args.out_json.is_absolute() else ROOT / args.out_json
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"Wrote {out_path} rows={len(doc['rows'])} profiles={len(profiles)} "
        f"unique_4d={doc['summary']['unique_verse_vector_4d_count']}",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
