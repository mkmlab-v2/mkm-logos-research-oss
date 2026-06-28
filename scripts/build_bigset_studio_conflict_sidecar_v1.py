#!/usr/bin/env python3
"""Build Logos Studio conflict sidecar from BigSet conflict_surface [HYPO].

B-track · NON_GATING · schools are not merged.

Reproducible:
  py scripts/build_bigset_studio_conflict_sidecar_v1.py
  py scripts/build_bigset_studio_conflict_sidecar_v1.py --conflict-surface docs/final/artifacts/bigset_conflict_surface_v1_latest.json
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_IN = ROOT / "docs/final/artifacts/bigset_conflict_surface_v1_latest.json"
DEFAULT_SUPPLEMENT = ROOT / "docs/final/artifacts/bigset_multi_topic_conflict_surface_v1_latest.json"
DEFAULT_JOB_SUPPLEMENT = ROOT / "docs/final/artifacts/job_studio_conflict_surface_v1_latest.json"
DEFAULT_ISAIAH_SUPPLEMENT = ROOT / "docs/final/artifacts/isaiah_studio_conflict_surface_v1_latest.json"
DEFAULT_OUT = ROOT / "docs/final/artifacts/bigset_studio_conflict_sidecar_v1_latest.json"
DEFAULT_STUDIO = (
    ROOT / "projects/no1kmedi/public/data/logos_studio/bigset_conflict_sidecar_v1.json"
)
DEFAULT_HUMAN_REVIEW_PENDING = (
    ROOT / "docs/final/artifacts/bigset_tier0_atypical_human_review_pending_v1_latest.json"
)

# Soft links conflict_group_id → Studio preset ids (read-only hints, not gating).
DEFAULT_PRESET_LINKS: dict[str, list[str]] = {
    "MKM_CONCEPT_SONS_OF_GOD": ["era_genesis_order_and_fall"],
    "MKM_CONCEPT_NEPHILIM": ["bigset_topic_nephilim"],
    "MKM_CONCEPT_JOB_SUFFERING": ["job_job_suffering_reason", "job_existential_suffering"],
    "MKM_CONCEPT_ISAIAH_YOUTUBE": ["isaiah_youtube_spine_v1"],
}


def _merge_conflict_groups(primary: dict[str, Any], supplement: dict[str, Any] | None) -> dict[str, Any]:
    if not supplement:
        return primary
    by_id = {
        str(g.get("conflict_group_id") or ""): g
        for g in primary.get("groups") or []
        if isinstance(g, dict) and g.get("conflict_group_id")
    }
    for g in supplement.get("groups") or []:
        if not isinstance(g, dict):
            continue
        gid = str(g.get("conflict_group_id") or "").strip()
        if not gid or gid in by_id or gid == "UNGROUPED":
            continue
        by_id[gid] = g
    merged = dict(primary)
    merged["groups"] = list(by_id.values())
    return merged


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_human_review_pending_count(path: Path | None) -> int | None:
    if path is None or not path.is_file():
        return None
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    if isinstance(doc.get("pending_count"), int):
        return doc["pending_count"]
    pending = doc.get("pending")
    return len(pending) if isinstance(pending, list) else None


def build_sidecar(
    conflict: dict[str, Any],
    *,
    preset_links: dict[str, list[str]] | None = None,
    human_review_pending_count: int | None = None,
    human_review_pending_source: str | None = None,
) -> dict[str, Any]:
    groups_in = conflict.get("groups") if isinstance(conflict.get("groups"), list) else []
    links = preset_links if preset_links is not None else DEFAULT_PRESET_LINKS
    groups: list[dict[str, Any]] = []
    for g in groups_in:
        if not isinstance(g, dict):
            continue
        gid = str(g.get("conflict_group_id") or "").strip()
        schools_out: list[dict[str, Any]] = []
        for s in g.get("schools") or []:
            if not isinstance(s, dict):
                continue
            schools_out.append(
                {
                    "school_tier": s.get("school_tier"),
                    "interpretation_ko": s.get("interpretation_ko"),
                    "citation_lock_anchors": s.get("citation_lock_anchors") or [],
                    "verse_refs": s.get("verse_refs") or [],
                    "traditions": s.get("traditions") or [],
                    "labels": s.get("labels") or ["research_only", "NON_GATING"],
                }
            )
        groups.append(
            {
                "conflict_group_id": gid,
                "lexicon_base": g.get("lexicon_base"),
                "school_count": len(schools_out),
                "schools": schools_out,
                "linked_preset_ids": links.get(gid, []),
            }
        )
    observability: dict[str, Any] = {}
    if human_review_pending_count is not None:
        observability["human_review_pending_count"] = human_review_pending_count
        if human_review_pending_source:
            observability["human_review_pending_source"] = human_review_pending_source

    return {
        "schema": "bigset_studio_conflict_sidecar_v1",
        "generated_at_utc": _now(),
        "research_only": True,
        "hypothesis_tier": "B",
        "send_gate": "HOLD",
        "non_gating": True,
        "no_lens_supremacy": True,
        "source_conflict_surface": conflict.get("schema"),
        "group_count": len(groups),
        "observability": observability,
        "groups": groups,
        "ui_contract": {
            "panel_title_ko": "학파별 해석 격벽 (BigSet Tier-0)",
            "disclaimer_ko": "[HYPO] 외부 웹 수집·fixture 혼합. citation lock 전 연구용. 단일 학파 우위 없음.",
        },
        "reproduce": "py scripts/build_bigset_studio_conflict_sidecar_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--conflict-surface", type=Path, default=DEFAULT_IN)
    ap.add_argument(
        "--conflict-surface-supplement",
        type=Path,
        default=DEFAULT_SUPPLEMENT,
        help="Merge missing conflict groups (e.g. MKM_CONCEPT_NEPHILIM)",
    )
    ap.add_argument(
        "--job-conflict-supplement",
        type=Path,
        default=DEFAULT_JOB_SUPPLEMENT,
        help="Merge Job reading-pack conflict group (MKM_CONCEPT_JOB_SUFFERING)",
    )
    ap.add_argument(
        "--isaiah-conflict-supplement",
        type=Path,
        default=DEFAULT_ISAIAH_SUPPLEMENT,
        help="Merge Isaiah YouTube reading-pack conflict group (MKM_CONCEPT_ISAIAH_YOUTUBE)",
    )
    ap.add_argument("--out-artifact", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--studio-mirror", type=Path, default=DEFAULT_STUDIO)
    ap.add_argument("--skip-studio-mirror", action="store_true")
    ap.add_argument(
        "--human-review-pending",
        type=Path,
        default=DEFAULT_HUMAN_REVIEW_PENDING,
        help="export-pending artifact; omit file → field skipped",
    )
    args = ap.parse_args()
    if not args.conflict_surface.is_file():
        print(json.dumps({"ok": False, "error": f"missing: {args.conflict_surface}"}), file=sys.stderr)
        return 2
    conflict = json.loads(args.conflict_surface.read_text(encoding="utf-8"))
    supplement = None
    if args.conflict_surface_supplement.is_file():
        supplement = json.loads(args.conflict_surface_supplement.read_text(encoding="utf-8"))
    conflict = _merge_conflict_groups(conflict, supplement)
    job_supplement = None
    if args.job_conflict_supplement.is_file():
        job_supplement = json.loads(args.job_conflict_supplement.read_text(encoding="utf-8"))
    conflict = _merge_conflict_groups(conflict, job_supplement)
    isaiah_supplement = None
    if args.isaiah_conflict_supplement.is_file():
        isaiah_supplement = json.loads(args.isaiah_conflict_supplement.read_text(encoding="utf-8"))
    conflict = _merge_conflict_groups(conflict, isaiah_supplement)
    pending_path = args.human_review_pending
    pending_count = _read_human_review_pending_count(pending_path)
    pending_source = None
    if pending_count is not None and pending_path is not None:
        try:
            pending_source = str(pending_path.relative_to(ROOT)).replace("\\", "/")
        except ValueError:
            pending_source = str(pending_path)
    doc = build_sidecar(
        conflict,
        human_review_pending_count=pending_count,
        human_review_pending_source=pending_source,
    )
    args.out_artifact.parent.mkdir(parents=True, exist_ok=True)
    args.out_artifact.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if not args.skip_studio_mirror:
        args.studio_mirror.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(args.out_artifact, args.studio_mirror)
    print(
        json.dumps(
            {
                "ok": True,
                "groups": doc["group_count"],
                "human_review_pending_count": doc.get("observability", {}).get(
                    "human_review_pending_count"
                ),
                "artifact": str(args.out_artifact.relative_to(ROOT)).replace("\\", "/"),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
