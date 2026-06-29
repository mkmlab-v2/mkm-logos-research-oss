#!/usr/bin/env python3
"""Build Track C B2B counsel export manifest (SHA256 file list)."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/final/artifacts"
DEFAULT_OUT = ART / "track_c_b2b_counsel_export_manifest_v1_latest.json"
SCAN_REPORT = ROOT / "reports/track_c_b2b_counsel_copy_scan_v1_latest.json"
READINESS = ROOT / "reports/track_c_b2b_meeting_pack_readiness_v1_latest.json"

DEFAULT_PATHS: tuple[str, ...] = (
    "docs/final/artifacts/track_c_b2b_meeting_pack_index_v1_latest.md",
    "docs/final/artifacts/track_c_b2b_two_layer_agent_slide_v1_latest.md",
    "docs/final/artifacts/track_c_b2b_two_layer_agent_slide_v1_print.html",
    "docs/final/artifacts/track_c_b2b_internal_rehearsal_runbook_v1_latest.md",
    "docs/final/artifacts/track_c_logos_b2b_exec_summary_slide_v1_latest.md",
    "docs/final/artifacts/track_c_logos_redacted_demo_excerpt_v1_latest.md",
    "docs/final/artifacts/track_c_combined_b2b_offer_onepager_v1_latest.md",
    "docs/final/artifacts/track_c_logos_deep_risk_narrative_offer_onepager_v1_latest.md",
    "docs/final/artifacts/track_c_b2b_macro_alert_offer_onepager_latest.md",
    "docs/final/artifacts/track_c_b2b_logos_lens_appendix_v1_latest.md",
    "docs/final/artifacts/track_c_b2b_compression_plugin_appendix_v1_latest.md",
    "docs/final/artifacts/dynamic_bgm_melody_chain_demo_v1_latest.json",
    "docs/final/artifacts/dynamic_bgm_hp_sweep_v1_latest.json",
    "reports/track_c_audio_hook_samples_v1/track_c_audio_hook_samples_manifest_v1_latest.json",
    "reports/track_c_audio_hook_samples_v1/dynamic_bgm_hp100_pass_v1.wav",
    "reports/track_c_audio_hook_samples_v1/dynamic_bgm_hp050_pass_v1.wav",
    "reports/track_c_audio_hook_samples_v1/dynamic_bgm_hp020_pass_v1.wav",
    "reports/track_c_b2b_15min_rehearsal_script_v1_latest.md",
    "reports/track_c_b2b_internal_rehearsal_readiness_v1_latest.json",
    "docs/final/artifacts/track_c_b2b_longform_spine_sla_draft_v1_latest.md",
    "docs/final/PUBLIC_FACING_SECURITY_AND_IP_COPY_CHECKLIST_V1.md",
    "docs/final/TRACK_C_IP_BUSINESS_PLAN_2026-04-17.md",
    "reports/track_c_b2b_counsel_copy_scan_v1_latest.json",
    "reports/track_c_b2b_meeting_pack_readiness_v1_latest.json",
    "reports/track_c_b2b_counsel_one_minute_brief_v1_latest.md",
    "reports/track_c_showroom_deck_screenshots_manifest_v1_latest.json",
    "reports/track_c_showroom_deck_screenshots_v1/topology_radar_v1.png",
    "reports/track_c_showroom_deck_screenshots_v1/meaning_topology_graph_v1.png",
    "reports/track_c_showroom_deck_screenshots_v1/logos_oracle_v6_v1.png",
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _audio_gate_paths_from_staging() -> list[str]:
    staging_path = ROOT / "reports/track_c_audio_hook_samples_v1/track_c_audio_hook_samples_manifest_v1_latest.json"
    doc = _read_json(staging_path) or {}
    out: list[str] = []
    for row in doc.get("samples") or []:
        if not isinstance(row, dict):
            continue
        gate = row.get("gate_report")
        if isinstance(gate, str) and gate.strip():
            out.append(gate.replace("\\", "/"))
    return out


def _all_manifest_paths() -> list[str]:
    paths = list(DEFAULT_PATHS)
    for rel in _audio_gate_paths_from_staging():
        if rel not in paths:
            paths.append(rel)
    return paths


def build_manifest(paths: list[str]) -> dict[str, Any]:
    files: list[dict[str, Any]] = []
    missing: list[str] = []
    for rel in paths:
        src = ROOT / rel
        if not src.is_file():
            missing.append(rel)
            continue
        files.append(
            {
                "path": rel.replace("\\", "/"),
                "size_bytes": src.stat().st_size,
                "sha256": _sha256(src),
            }
        )
    scan = _read_json(SCAN_REPORT) or {}
    readiness = _read_json(READINESS) or {}
    return {
        "schema": "track_c_b2b_counsel_export_manifest_v1",
        "generated_at_utc": _utc_now(),
        "classification": "INTERNAL_ONLY",
        "lane": "track_c_b2b",
        "ready_for_external_send": False,
        "file_count": len(files),
        "files": files,
        "missing_paths": missing,
        "preflight": {
            "copy_scan_ok": scan.get("scan_ok"),
            "internal_meeting_ready": readiness.get("ready_for_internal_meeting"),
        },
        "zip_hint": "scripts/build_track_c_b2b_counsel_zip_pack_v1.py",
        "boundary_ack": "Manifest integrity only; not COUNSEL_REVIEWED or external send authorization.",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--fail-if-missing", action="store_true")
    args = ap.parse_args()
    doc = build_manifest(_all_manifest_paths())
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": len(doc.get("missing_paths") or []) == 0,
                "file_count": doc["file_count"],
                "missing": doc.get("missing_paths"),
            },
            ensure_ascii=False,
        )
    )
    if args.fail_if_missing and doc.get("missing_paths"):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
