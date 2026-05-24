#!/usr/bin/env python3
"""Track B Phase 2 fusion: policy pipeline + theme integrate (if not stopped) + verse 4D surface + optional B2B/showroom/VPS.

Does not merge theme DB with verse OS vectors (operational chain only). NON_GATING / hypothesis_tier B.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
STATE_OUT = ROOT / "reports/logos_phase2_fusion_state_v1_latest.json"
STOP_FILE = ROOT / "docs/research/logos_metaphor_db_v1/LOGOS_THEME_RUN.stop"
READINESS = ROOT / "docs/final/artifacts/logos_track_b_policy_readiness_v1_latest.json"
MATRIX = ROOT / "docs/final/artifacts/logos_verse_myeongri_cross_bridge_matrix_v1_latest.json"
THEME_SLICE = (
    ROOT
    / "projects/bitcoin-trading/ops/windows-rehearsal/jemaai-cloud-mvp/showroom_logos_research_slice_v0.json"
)
B2B_READINESS = ROOT / "reports/track_c_b2b_meeting_pack_readiness_v1_latest.json"
ANN_REPORT = ROOT / "docs/final/artifacts/logos_vector_index_ann_lite_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _run_step(name: str, cmd: list[str], *, cwd: Path | None = None) -> int:
    print(f"[phase2-fusion] {name}", flush=True)
    if not cmd:
        return 0
    rc = subprocess.run(cmd, cwd=str(cwd or ROOT)).returncode
    if rc != 0:
        print(f"[phase2-fusion] failed {name} exit={rc}", flush=True)
    return rc


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (json.JSONDecodeError, OSError):
        return {}


def _summarize_state() -> dict[str, Any]:
    readiness = _read_json(READINESS)
    matrix = _read_json(MATRIX)
    theme_slice = _read_json(THEME_SLICE)
    b2b = _read_json(B2B_READINESS)
    ann = _read_json(ANN_REPORT)
    gap_meta = _read_json(ROOT / "docs/final/artifacts/logos_verse_gap_ingest_queue_v1_latest.json")
    union_meta = _read_json(ROOT / "docs/final/artifacts/logos_verse_decoded_v2_union_v1_latest.json")
    os_compare = _read_json(ROOT / "docs/final/artifacts/logos_verse_4d_os_compare_v1_latest.json")
    inputs = matrix.get("inputs") if isinstance(matrix.get("inputs"), dict) else {}
    summary = matrix.get("summary") if isinstance(matrix.get("summary"), dict) else {}
    profiles = matrix.get("human_profiles")
    if not isinstance(profiles, list):
        profiles = inputs.get("human_profiles") if isinstance(inputs.get("human_profiles"), list) else []
    top_n = inputs.get("top_n") if inputs.get("top_n") is not None else summary.get("medoid_count")
    return {
        "schema": "logos_phase2_fusion_state_v1",
        "updated_utc": _utc_now(),
        "theme_stop_frozen": STOP_FILE.is_file(),
        "track_b_policy_overall_ok": readiness.get("overall_ok"),
        "theme_count": theme_slice.get("theme_count"),
        "matrix_top_n": top_n,
        "matrix_human_profiles": len(profiles),
        "matrix_unique_verse_vector_4d_count": summary.get("unique_verse_vector_4d_count"),
        "ready_for_internal_meeting": b2b.get("ready_for_internal_meeting"),
        "ready_for_external_send": b2b.get("ready_for_external_send"),
        "ann_lite_rows_written": ann.get("rows_written"),
        "ann_lite_unlimited": (ann.get("verse_source") or {}).get("unlimited"),
        "semantic_queryset_recommended": _read_json(
            ROOT / "docs/final/artifacts/logos_semantic_queryset_ab_compare_latest.json"
        ).get("recommended_set"),
        "gap_ingest_queue_rows": gap_meta.get("rows_written"),
        "verse_decoded_union_rows": union_meta.get("union_rows"),
        "phase4_os_compare_canon_rows": next(
            (c.get("rows") for c in (os_compare.get("corpora") or []) if c.get("label") == "canon"),
            None,
        ),
        "phase4_full_graph": (os_compare.get("build") or {}).get("full_graph"),
        "hypothesis_tier": "B",
        "gating_status": "NON_GATING",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--include-ann-lite", action="store_true", help="Pass --include-ann-lite to track_b pipeline (policy active)")
    ap.add_argument("--skip-gap-queue", action="store_true")
    ap.add_argument("--include-gap-union-rebuild", action="store_true", help="gap staging + union + 4D rebuild (slow)")
    ap.add_argument("--skip-gap-union-rebuild", action="store_true")
    ap.add_argument("--skip-phase4-full-graph", action="store_true")
    ap.add_argument("--skip-track-b-pipeline", action="store_true")
    ap.add_argument("--skip-theme-integrate", action="store_true")
    ap.add_argument("--skip-verse-4d", action="store_true")
    ap.add_argument("--skip-regression", action="store_true")
    ap.add_argument("--skip-b2b-pack", action="store_true")
    ap.add_argument("--skip-showroom-bundle", action="store_true")
    ap.add_argument("--skip-deploy", action="store_true")
    ap.add_argument("--skip-vps-sync", action="store_true")
    ap.add_argument("--reload-nginx", action="store_true", help="Pass -ReloadNginx to sync_showroom_to_vps.ps1")
    ap.add_argument("--dry-run", action="store_true", help="Print planned steps only")
    args = ap.parse_args()

    py = sys.executable
    pwsh = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File"]
    steps: list[tuple[str, list[str]]] = []

    if not args.skip_gap_queue:
        steps.append(
            (
                "gap_ingest_queue",
                [py, str(ROOT / "scripts/build_logos_verse_gap_ingest_queue_v1.py")],
            )
        )
    if args.include_gap_union_rebuild and not args.skip_gap_union_rebuild:
        steps.append(
            (
                "gap_union_rebuild",
                [py, str(ROOT / "scripts/run_logos_gap_union_rebuild_chain_v1.py")],
            )
        )
    if not args.skip_phase4_full_graph:
        steps.append(
            (
                "phase4_full_graph",
                [
                    py,
                    str(ROOT / "scripts/run_logos_verse_4d_phase4_chain_v1.py"),
                    "--full-graph",
                    "--sample-size",
                    "28741",
                    "--max-rows",
                    "0",
                ],
            )
        )
    if not args.skip_track_b_pipeline:
        track_b_cmd = [py, str(ROOT / "scripts/run_logos_track_b_pipeline_chain_v1.py")]
        if args.include_ann_lite:
            track_b_cmd.append("--include-ann-lite")
        steps.append(("track_b_pipeline", track_b_cmd))
    if not args.skip_theme_integrate:
        steps.append(
            (
                "theme_integrate",
                [
                    py,
                    str(ROOT / "scripts/run_logos_theme_integrate_chain_v1.py"),
                    "--skip-if-unchanged",
                    "--skip-deploy",
                ],
            )
        )
    if not args.skip_verse_4d:
        steps.append(
            ("verse_4d_showroom_b2b", [py, str(ROOT / "scripts/run_logos_verse_4d_showroom_b2b_chain_v1.py")])
        )
    if not args.skip_regression:
        steps.append(
            ("verse_4d_regression", [py, str(ROOT / "scripts/run_logos_verse_4d_regression_bundle_v1.py")])
        )
    if not args.skip_b2b_pack:
        steps.append(
            ("b2b_meeting_pack", pwsh + [str(ROOT / "scripts/Invoke-TrackCB2bMeetingPack_v1.ps1")])
        )
    if not args.skip_showroom_bundle:
        steps.append(
            (
                "showroom_track_c_bundle",
                pwsh + [str(ROOT / "scripts/build_showroom_track_c_bundle_chain_v1.ps1")],
            )
        )
    if not args.skip_deploy:
        steps.append(
            (
                "deploy_showroom_static",
                pwsh
                + [str(ROOT / "projects/bitcoin-trading/ops/windows-rehearsal/deploy_showroom_static.ps1")],
            )
        )
    if not args.skip_vps_sync:
        vps_cmd = pwsh + [str(ROOT / "scripts/sync_showroom_to_vps.ps1"), "-RefreshStaging"]
        if args.reload_nginx:
            vps_cmd.append("-ReloadNginx")
        steps.append(("vps_sync", vps_cmd))

    if args.dry_run:
        for name, _ in steps:
            print(f"[phase2-fusion] dry-run would run: {name}", flush=True)
        return 0

    for name, cmd in steps:
        rc = _run_step(name, cmd)
        if rc != 0:
            return rc

    payload = _summarize_state()
    STATE_OUT.parent.mkdir(parents=True, exist_ok=True)
    STATE_OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"[phase2-fusion] wrote {STATE_OUT}", flush=True)
    print("[phase2-fusion] done", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
