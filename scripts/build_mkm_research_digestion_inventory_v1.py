#!/usr/bin/env python3
"""[HYPO] Research digestion inventory: S0–S3 tier stamps + priority backlog (B-track)."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
RESEARCH = ROOT / "docs" / "research"
RAW = RESEARCH / "raw"
ARTIFACTS = ROOT / "docs" / "final" / "artifacts"
DEFAULT_OUT = ROOT / "reports/mkm_research_digestion_inventory_v1_latest.json"
DIGESTION_CHAIN = ROOT / "reports/mkm_digestion_engine_chain_v1_latest.json"
GATE = ARTIFACTS / "mkm_digested_facts_gate_latest.json"

PRIORITY_KEYWORDS: tuple[tuple[str, int], ...] = (
    ("compression", 8),
    ("nextgen", 8),
    ("golden40", 7),
    ("ng40", 7),
    ("public_facing", 6),
    ("track_a", 6),
    ("promotion", 5),
    ("b2b", 5),
    ("prophecy", 4),
    ("regime", 4),
    ("fact_lock", 4),
    ("digestion", 4),
    ("lexicon", 3),
    ("logos", 2),
)

LIT_GLOB = "*LIT_REVIEW*.md"
MERGED_GLOB = "*MERGED_LIT_REVIEW*.md"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _slug(text: str) -> str:
    s = re.sub(r"_LIT_REVIEW.*$", "", text, flags=re.IGNORECASE)
    s = re.sub(r"_MERGED_LIT_REVIEW.*$", "", s, flags=re.IGNORECASE)
    s = re.sub(r"_MERGED$", "", s, flags=re.IGNORECASE)
    s = re.sub(r"_tier0.*$", "", s, flags=re.IGNORECASE)
    s = re.sub(r"_explore.*$", "", s, flags=re.IGNORECASE)
    s = re.sub(r"\.md$", "", s, flags=re.IGNORECASE)
    return re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_")


def _load_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def _score_slug(slug: str) -> int:
    score = 0
    low = slug.lower()
    for kw, pts in PRIORITY_KEYWORDS:
        if kw in low:
            score += pts
    return score


def _digested_paths() -> dict[str, Path]:
    out: dict[str, Path] = {}
    for p in ARTIFACTS.glob("*_digested_facts_latest.json"):
        stem = p.name.replace("_digested_facts_latest.json", "")
        out[_slug(stem)] = p
        out[stem.lower()] = p
    return out


def _gate_ok_for(path: Path) -> bool | None:
    gate = _load_json(GATE)
    if not gate:
        return None
    failures = gate.get("failures") or []
    inp = _rel(path)
    for row in gate.get("results") or []:
        if str(row.get("digested_path") or "").replace("\\", "/") == inp:
            return bool(row.get("ok"))
    return len(failures) == 0 if gate.get("ok") else False


def _chain_ok_for(path: Path) -> bool | None:
    chain = _load_json(DIGESTION_CHAIN)
    if not chain:
        return None
    dig = _rel(path)
    if str(chain.get("digested_facts_path") or "").replace("\\", "/") == dig:
        return bool(chain.get("ok"))
    return None


def _match_raw(slug: str, raw_files: list[Path]) -> Path | None:
    best: Path | None = None
    best_len = 0
    for p in raw_files:
        rs = _slug(p.stem)
        if slug in rs or rs in slug:
            if len(rs) > best_len:
                best = p
                best_len = len(rs)
    return best


def _match_digested(slug: str, digested: dict[str, Path]) -> Path | None:
    if slug in digested:
        return digested[slug]
    for key, path in digested.items():
        if slug in key or key in slug:
            return path
    return None


def _tier_for(*, lit: bool, raw: Path | None, digested: Path | None, gate_ok: bool | None) -> str:
    if digested and gate_ok is True:
        return "S3"
    if digested:
        return "S2b"
    if raw:
        return "S2"
    if lit:
        return "S1"
    return "S0"


def _collect_lit_paths() -> list[Path]:
    seen: set[str] = set()
    paths: list[Path] = []
    for pattern in (LIT_GLOB, MERGED_GLOB):
        for p in sorted(RESEARCH.glob(pattern)):
            rel = _rel(p)
            if rel in seen:
                continue
            seen.add(rel)
            paths.append(p)
    return paths


def _collect_raw_files() -> list[Path]:
    if not RAW.is_dir():
        return []
    return sorted(
        p for p in RAW.iterdir() if p.is_file() and p.suffix.lower() in {".md", ".txt"}
    )


def build() -> dict[str, Any]:
    lit_paths = _collect_lit_paths()
    raw_files = _collect_raw_files()
    digested_map = _digested_paths()

    entries: list[dict[str, Any]] = []
    tier_counts = {"S0": 0, "S1": 0, "S2": 0, "S2b": 0, "S3": 0}

    for lit in lit_paths:
        slug = _slug(lit.stem)
        raw = _match_raw(slug, raw_files)
        dig = _match_digested(slug, digested_map)
        gate_ok = _gate_ok_for(dig) if dig else None
        chain_ok = _chain_ok_for(dig) if dig else None
        if gate_ok is None and chain_ok is not None:
            gate_ok = chain_ok
        tier = _tier_for(lit=True, raw=raw, digested=dig, gate_ok=gate_ok)
        tier_counts[tier] = tier_counts.get(tier, 0) + 1
        entries.append(
            {
                "id": slug,
                "tier": tier,
                "priority_score": _score_slug(slug),
                "lit_review_path": _rel(lit),
                "raw_path": _rel(raw) if raw else None,
                "digested_facts_path": _rel(dig) if dig else None,
                "gate_ok": gate_ok,
                "digestion_backlog": tier in ("S1", "S2", "S2b"),
            }
        )

    # Orphan raw (no LIT match)
    lit_slugs = {_slug(p.stem) for p in lit_paths}
    for raw in raw_files:
        rs = _slug(raw.stem)
        if any(rs in ls or ls in rs for ls in lit_slugs):
            continue
        dig = _match_digested(rs, digested_map)
        gate_ok = _gate_ok_for(dig) if dig else None
        tier = _tier_for(lit=False, raw=raw, digested=dig, gate_ok=gate_ok)
        tier_counts[tier] = tier_counts.get(tier, 0) + 1
        entries.append(
            {
                "id": rs,
                "tier": tier,
                "priority_score": _score_slug(rs),
                "lit_review_path": None,
                "raw_path": _rel(raw),
                "digested_facts_path": _rel(dig) if dig else None,
                "gate_ok": gate_ok,
                "digestion_backlog": tier in ("S1", "S2", "S2b"),
            }
        )

    backlog = sorted(
        [e for e in entries if e["digestion_backlog"]],
        key=lambda x: (-x["priority_score"], x["id"]),
    )
    priority_queue = backlog[:10]

    s3 = [e for e in entries if e["tier"] == "S3"]
    policy = {
        "S3": "digested_facts + gate exit 0 — promotion/citation OK for wired facts",
        "S2b": "digested JSON present; gate not confirmed — re-run chain",
        "S2": "raw Tier0 only — run run_mkm_digestion_engine_chain_v1.py",
        "S1": "LIT only — reference/hooks; no implementation claims",
        "S0": "not in repo scan scope",
    }

    return {
        "schema": "mkm_research_digestion_inventory_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "send_gate": "HOLD",
        "summary": {
            "lit_review_count": len(lit_paths),
            "raw_tier0_count": len(raw_files),
            "digested_facts_count": len(list(ARTIFACTS.glob("*_digested_facts_latest.json"))),
            "tier_counts": tier_counts,
            "s3_count": len(s3),
            "backlog_count": len(backlog),
        },
        "tier_policy": policy,
        "entries": sorted(entries, key=lambda x: (-x["priority_score"], x["id"])),
        "priority_queue_top10": priority_queue,
        "recommended_actions": [
            {
                "action": "digest_raw",
                "targets": [
                    e["raw_path"]
                    for e in priority_queue
                    if e.get("raw_path") and e["tier"] in ("S2", "S2b")
                ][:5],
            },
            {
                "action": "tier0_ingest_then_digest",
                "targets": [
                    e["lit_review_path"]
                    for e in priority_queue
                    if e.get("lit_review_path") and not e.get("raw_path")
                ][:5],
            },
            {
                "action": "blocked_public_rollup",
                "command": "py scripts/build_mkm_digestion_blocked_public_claims_v1.py",
            },
        ],
        "reproducible_command": "py scripts/build_mkm_research_digestion_inventory_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--json", action="store_true", help="print summary json to stdout")
    args = ap.parse_args()

    doc = build()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.json:
        print(
            json.dumps(
                {
                    "wrote": str(args.out),
                    "s3": doc["summary"]["s3_count"],
                    "backlog": doc["summary"]["backlog_count"],
                    "top": [e["id"] for e in doc["priority_queue_top10"]],
                },
                ensure_ascii=False,
            )
        )
    else:
        print(f"Wrote: {args.out}")
        print(
            f"LIT={doc['summary']['lit_review_count']} raw={doc['summary']['raw_tier0_count']} "
            f"S3={doc['summary']['s3_count']} backlog={doc['summary']['backlog_count']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
