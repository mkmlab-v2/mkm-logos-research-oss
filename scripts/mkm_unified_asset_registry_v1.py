#!/usr/bin/env python3
"""DF-P1-05: Unified asset registry facade — resolve 31k corpus ∥ 41k lexicon paths (no file merge)."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "mkm_unified_asset_registry_v1"
VERSION = "1.0.0"
DEFAULT_OUT = ROOT / "docs/final/artifacts/mkm_unified_asset_registry_v1_latest.json"

# Lane isolation: resolving one lane must not stat/load assets of forbidden lanes.
LANE_FORBIDDEN_CROSS: dict[str, tuple[str, ...]] = {
    "corpus_core_31k": ("lexicon_master_41k", "compress_domain_policy", "decoy_experience_layer"),
    "lexicon_master_41k": ("corpus_core_31k", "decoy_experience_layer"),
    "compress_domain_policy": ("corpus_core_31k", "lexicon_master_41k", "decoy_experience_layer"),
    "manuscript_fabric_v2": ("lexicon_master_41k", "decoy_experience_layer"),
    "decoy_experience_layer": ("corpus_core_31k", "lexicon_master_41k", "manuscript_fabric_v2"),
}


@dataclass
class PathRef:
    key: str
    path: Path
    exists: bool
    bytes: int | None = None
    sha256_prefix: str | None = None


@dataclass
class LaneResolution:
    lane_key: str
    role: str
    lazy_load: bool
    paths: list[PathRef] = field(default_factory=list)
    glob_matches: dict[str, list[str]] = field(default_factory=dict)
    boundary_ack: str = ""


def _sha16(path: Path) -> str | None:
    if not path.is_file() or path.stat().st_size > 2_000_000:
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16].upper()


def _ref(key: str, rel: str, *, root: Path = ROOT) -> PathRef:
    p = root / rel.replace("\\", "/")
    exists = p.is_file()
    nbytes = p.stat().st_size if exists else None
    prefix = _sha16(p) if exists and nbytes is not None and nbytes <= 2_000_000 else None
    return PathRef(key=key, path=p, exists=exists, bytes=nbytes, sha256_prefix=prefix)


def _glob_rel(pattern: str, *, root: Path = ROOT) -> list[str]:
    return sorted(str(x.relative_to(root)).replace("\\", "/") for x in root.glob(pattern))


def resolve_corpus_core_31k(*, root: Path = ROOT) -> LaneResolution:
    manifest_path = root / "docs/final/artifacts/logos_corpus_manifest_v1_latest.json"
    refs = [
        _ref("corpus_array", "data/logos/verse_4pipeline_full_31102.json", root=root),
        _ref("corpus_manifest", "docs/final/artifacts/logos_corpus_manifest_v1_latest.json", root=root),
    ]
    verse_4d_manifest = root / "docs/final/artifacts/logos_verse_4d_corpus_v1_latest.json"
    if verse_4d_manifest.is_file():
        doc = json.loads(verse_4d_manifest.read_text(encoding="utf-8-sig"))
        out_rel = (doc.get("outputs") or {}).get("verse_4d_jsonl")
        if out_rel:
            refs.append(_ref("verse_4d_jsonl", str(out_rel), root=root))
    verse_count = None
    if manifest_path.is_file():
        verse_count = json.loads(manifest_path.read_text(encoding="utf-8-sig")).get("verse_count")
    res = LaneResolution(
        lane_key="corpus_core_31k",
        role="Graph · Wire verse_id · selective load",
        lazy_load=True,
        paths=refs,
        boundary_ack="Pointer-only resolve; does not load 31k array into memory.",
    )
    if verse_count is not None:
        res.glob_matches["verse_count"] = [str(verse_count)]
    return res


def resolve_lexicon_master_41k(*, root: Path = ROOT) -> LaneResolution:
    matches = _glob_rel(
        "reports/constitution/btrack_pilot/master_codebook_lexicon_v1_*_rows_latest.json",
        root=root,
    )
    refs: list[PathRef] = []
    if matches:
        refs.append(_ref("lexicon_rows", matches[-1], root=root))
    return LaneResolution(
        lane_key="lexicon_master_41k",
        role="Track A must_keep join (optional)",
        lazy_load=True,
        paths=refs,
        glob_matches={"lexicon_latest": matches},
        boundary_ack="Wire payload must not embed 41k lexicon rows.",
    )


def resolve_compress_domain_policy(*, root: Path = ROOT) -> LaneResolution:
    shards = _glob_rel("codebook/shards/zone_*.json", root=root)
    refs = [_ref(f"zone_{i}", rel, root=root) for i, rel in enumerate(shards[:8])]
    return LaneResolution(
        lane_key="compress_domain_policy",
        role="zone_* shard at compress time",
        lazy_load=True,
        paths=refs,
        glob_matches={"zone_shards": shards, "zone_shard_count": [str(len(shards))]},
        boundary_ack="Policy shards only; not merged with corpus_core_31k.",
    )


def resolve_decoy_experience_layer(*, root: Path = ROOT) -> LaneResolution:
    refs = [
        _ref("zone_tarot", "codebook/shards/zone_tarot.json", root=root),
        _ref("zone_mbti", "codebook/shards/zone_mbti.json", root=root),
        _ref(
            "readiness",
            "docs/final/artifacts/decoy_experience_layer_readiness_v1_latest.json",
            root=root,
        ),
    ]
    return LaneResolution(
        lane_key="decoy_experience_layer",
        role="Track C casual entry shards (tarot/MBTI routing only)",
        lazy_load=True,
        paths=refs,
        boundary_ack="DECOY-P0: no corpus/graph/wire merge; not Track A trigger; external copy = experience + premium report.",
    )


def resolve_manuscript_fabric_v2(*, root: Path = ROOT) -> LaneResolution:
    refs = [
        _ref("fabric_v2", "docs/final/artifacts/logos_canon_manuscript_fabric_v2_latest.json", root=root),
        _ref("bridge_edges", "data/logos/logos_variant_omission_bridge_edges_v2.jsonl", root=root),
    ]
    gap_policy = root / "data/logos/logos_gap_mt_only_policy_v1.jsonl"
    if gap_policy.is_file():
        refs.append(_ref("gap_policy", "data/logos/logos_gap_mt_only_policy_v1.jsonl", root=root))
    gap_n = ""
    fabric_path = refs[0].path
    if fabric_path.is_file():
        doc = json.loads(fabric_path.read_text(encoding="utf-8-sig"))
        cal = doc.get("canonical_address_layer") or {}
        gap_n = str(cal.get("gap_nt_textual_variant_count") or "")
    return LaneResolution(
        lane_key="manuscript_fabric_v2",
        role="Address vs ink · omission bridge · RE_ROUTE_TR wire flags",
        lazy_load=True,
        paths=refs,
        glob_matches={"gap_nt_textual_variant_count": [gap_n] if gap_n else []},
        boundary_ack="Does not merge TR into verse_decoded_v2_complete; core_corpus_sha_unchanged.",
    )


_RESOLVERS = {
    "corpus_core_31k": resolve_corpus_core_31k,
    "lexicon_master_41k": resolve_lexicon_master_41k,
    "compress_domain_policy": resolve_compress_domain_policy,
    "manuscript_fabric_v2": resolve_manuscript_fabric_v2,
    "decoy_experience_layer": resolve_decoy_experience_layer,
}


def resolve_lane(lane_key: str, *, root: Path = ROOT) -> LaneResolution:
    if lane_key not in _RESOLVERS:
        raise KeyError(f"unknown lane_key: {lane_key}")
    return _RESOLVERS[lane_key](root=root)


def lane_resolution_to_dict(res: LaneResolution) -> dict[str, Any]:
    return {
        "lane_key": res.lane_key,
        "role": res.role,
        "lazy_load": res.lazy_load,
        "boundary_ack": res.boundary_ack,
        "paths": [
            {
                "key": p.key,
                "relative_path": str(p.path.relative_to(ROOT)).replace("\\", "/")
                if p.path.is_relative_to(ROOT)
                else str(p.path),
                "exists": p.exists,
                "bytes": p.bytes,
                "sha256_prefix": p.sha256_prefix,
            }
            for p in res.paths
        ],
        "glob_matches": res.glob_matches,
    }


def assert_lane_isolation(lane_key: str) -> None:
    """Resolving lane_key must not touch forbidden lane asset paths."""
    forbidden = LANE_FORBIDDEN_CROSS.get(lane_key, ())
    primary = resolve_lane(lane_key)
    touched = {p.path.resolve() for p in primary.paths if p.exists}
    for other in forbidden:
        other_res = resolve_lane(other)
        for p in other_res.paths:
            if p.exists and p.path.resolve() in touched:
                raise RuntimeError(f"cross-lane path overlap: {lane_key} touched {other} path {p.path}")


def build_registry_manifest(*, root: Path = ROOT, out_path: Path = DEFAULT_OUT) -> dict[str, Any]:
    lanes = [resolve_lane(k, root=root) for k in _RESOLVERS]
    for lane in _RESOLVERS:
        assert_lane_isolation(lane)

    doc: dict[str, Any] = {
        "schema": SCHEMA,
        "schema_version": VERSION,
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "hypothesis_tier": "[HYPO]",
        "research_only": True,
        "policy": {
            "physical_merge_forbidden": True,
            "wire_lexicon_injection_forbidden": True,
            "lazy_resolve_only": True,
        },
        "lanes": [lane_resolution_to_dict(r) for r in lanes],
        "lane_keys": list(_RESOLVERS.keys()),
        "cross_lane_forbidden": {k: list(v) for k, v in LANE_FORBIDDEN_CROSS.items()},
        "boundary_ack": "Facade pointers only; 31k array and 41k lexicon stay separate files.",
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return doc


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("build", help="Write mkm_unified_asset_registry_v1_latest.json")
    p_resolve = sub.add_parser("resolve", help="Resolve one lane (stdout JSON)")
    p_resolve.add_argument("--lane", required=True, choices=list(_RESOLVERS.keys()))
    args = parser.parse_args()

    if args.cmd == "build":
        doc = build_registry_manifest()
        required_ok = all(
            p["exists"]
            for lane in doc["lanes"]
            if lane["lane_key"] == "corpus_core_31k"
            for p in lane["paths"]
            if p["key"] in ("corpus_array", "corpus_manifest")
        )
        print(
            json.dumps(
                {"ok": required_ok, "out": str(DEFAULT_OUT), "lane_count": len(doc["lanes"])},
                ensure_ascii=False,
            )
        )
        return 0 if required_ok else 1

    if args.cmd == "resolve":
        assert_lane_isolation(args.lane)
        res = resolve_lane(args.lane)
        print(json.dumps(lane_resolution_to_dict(res), ensure_ascii=False, indent=2))
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
