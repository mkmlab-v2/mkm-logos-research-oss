#!/usr/bin/env python3
"""Emit showroom_topology_radar_snapshot_v1 JSON for Track C Topology Radar (read-only, no trade signals)."""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Repo-relative paths that may exist after Logos / Track C / Aramaic-side chains.
_CANDIDATE_REFS = [
    "docs/final/artifacts/logos_corpus_graph_bundle_v1_latest.json",
    "docs/final/artifacts/logos_track_c_freshness_sidecar_v1_latest.json",
    "docs/final/artifacts/insight_survivor_candidates_latest.json",
    "docs/final/artifacts/insight_survivor_health_alert_latest.json",
    "docs/final/artifacts/bible_meaning_insight_candidates_latest.json",
]
_STUB_REF = "docs/final/schemas/showroom_topology_radar_snapshot_v1.example.json"


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _collect_existing_refs(workspace: Path) -> list[str]:
    out: list[str] = []
    for rel in _CANDIDATE_REFS:
        p = workspace / rel.replace("/", os.sep)
        if p.is_file():
            out.append(rel.replace("\\", "/"))
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--workspace-root",
        default="",
        help="Monorepo root (default: MKM_WORKSPACE_ROOT or parent of scripts/).",
    )
    ap.add_argument(
        "--out",
        default="docs/final/artifacts/showroom_topology_radar_snapshot_v1_latest.json",
        help="Output path relative to workspace root.",
    )
    ap.add_argument(
        "--stale-hours",
        type=int,
        default=24,
        help="Hours after generated_at_utc for stale_after_utc (default 24).",
    )
    ap.add_argument(
        "--allow-stub-ref",
        action="store_true",
        help="If no candidate artifacts exist, include the committed schema example path once (meta fallback).",
    )
    args = ap.parse_args()

    workspace = Path(args.workspace_root or os.environ.get("MKM_WORKSPACE_ROOT") or ROOT).resolve()
    out_path = workspace / args.out.replace("/", os.sep)

    refs = _collect_existing_refs(workspace)
    stub_used = False
    if not refs:
        if args.allow_stub_ref:
            refs = [_STUB_REF]
            stub_used = True
        else:
            print(
                "build_showroom_topology_radar_snapshot_v1: no candidate artifacts; "
                "run Logos/graph/freshness chains or pass --allow-stub-ref",
                flush=True,
            )
            return 2

    now = _utc_now()
    gen = now.replace(microsecond=0).isoformat().replace("+00:00", "Z")
    stale = (now + timedelta(hours=args.stale_hours)).replace(microsecond=0)
    stale_s = stale.isoformat().replace("+00:00", "Z")

    if stub_used:
        hypo = "[HYPO] Topology snapshot (stub: no live graph artifacts; example ref only)"
        summary = (
            "No logos_corpus_graph_bundle or freshness sidecar on disk; "
            "emitted minimal contract path for UI wiring only."
        )
    else:
        hypo = "[HYPO] Topology snapshot (read-only graph / sidecar proximity)"
        summary = (
            f"Collected {len(refs)} artifact path(s) for showroom radar; not investment advice."
        )

    snapshot = {
        "schema_version": "showroom_topology_radar_snapshot_v1",
        "generated_at_utc": gen,
        "stale_after_utc": stale_s,
        "hypo_banner": hypo,
        "summary_one_line": summary[:500],
        "artifact_refs": refs[:32],
        "disclaimer_ref": "jemaai_showroom_v1",
        "no_trade_signals": True,
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {out_path.relative_to(workspace)} ({len(refs)} ref(s), stub={stub_used})", flush=True)

    schema_path = workspace / "docs/final/schemas/showroom_topology_radar_snapshot_v1.schema.json"
    try:
        import jsonschema  # noqa: WPS433
    except ImportError:
        return 0

    if not schema_path.is_file():
        return 0

    try:
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        jsonschema.validate(instance=snapshot, schema=schema)
    except Exception as exc:  # pragma: no cover
        print(f"jsonschema validate failed: {exc}", flush=True)
        return 3

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
