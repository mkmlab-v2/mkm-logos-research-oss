#!/usr/bin/env python3
"""Build jemaai.cloud public showroom URL SSOT (Logos demo spine + commercial workspace pointer)."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "docs/final/artifacts/jemaai_showroom_public_urls_v1_latest.json"

JEMAAI_CLOUD = "https://jemaai.cloud"
JEMAAI_API = "https://api.jemaai.cloud"
LOGOS_COMMERCIAL = "https://logos.jema-ai.com"


def _page(path: str, *, data_json: str | None = None, extra: dict[str, Any] | None = None) -> dict[str, Any]:
    block: dict[str, Any] = {
        "path": path,
        "canonical": f"{JEMAAI_CLOUD}{path}",
        "api_mirror": f"{JEMAAI_API}{path}",
    }
    if data_json:
        block["data_json"] = data_json
    if extra:
        block.update(extra)
    return block


def build_doc() -> dict[str, Any]:
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return {
        "schema": "jemaai_showroom_public_urls_v1",
        "generated_at_utc": generated_at,
        "policy_ref": "docs/final/MKM_DOMAIN_PORTFOLIO_POINTER_V1.md §1.1",
        "hosts": {
            "static_showroom_canonical": JEMAAI_CLOUD,
            "static_showroom_demo_primary": JEMAAI_API,
            "public_event_api": JEMAAI_API,
        },
        "commercial_workspace": {
            "public_domain": LOGOS_COMMERCIAL,
            "product_primary_url": LOGOS_COMMERCIAL,
            "note_ko": "Track B 성경·텍스트 연구 워크스페이스(SKU). jemaai.cloud 데모와 분리.",
        },
        "logos_demo_spine": {
            "badge_ko": "Track C demo · [HYPO][NON_GATING] · 상용 워크스페이스 아님",
            "entry_point": "meaning_topology_qa_v2",
            "order": [
                "meaning_topology_qa_v2",
                "logos_job_reading_pack",
                "logos_isaiah_youtube_reading_pack",
                "logos_job_cosmic_code",
                "logos_research",
            ],
            "cta_to_commercial": LOGOS_COMMERCIAL,
        },
        "pages": {
            "topology_radar": _page("/public_showroom_topology_radar_v1.html"),
            "meaning_topology_graph": _page(
                "/public_showroom_meaning_topology_graph_v1.html",
                data_json=f"{JEMAAI_CLOUD}/showroom_meaning_topology_graph_slice_v1.json",
            ),
            "meaning_topology_qa_v2": _page(
                "/public_showroom_meaning_topology_qa_v2.html",
                data_json=f"{JEMAAI_CLOUD}/showroom_meaning_topology_qa_presets_v1.json",
                extra={"b2b_demo_primary": True, "logos_demo_spine_entry": True, "demo_primary_url": f"{JEMAAI_API}/public_showroom_meaning_topology_qa_v2.html?preset=job_job_suffering_reason"},
            ),
            "logos_job_reading_pack": _page(
                "/public_showroom_logos_job_reading_pack_v1.html",
                data_json=f"{JEMAAI_CLOUD}/showroom_logos_job_reading_pack_slice_v1.json",
                extra={"logos_demo_spine_step": 2},
            ),
            "logos_isaiah_youtube_reading_pack": _page(
                "/public_showroom_logos_isaiah_youtube_reading_pack_v1.html",
                data_json=f"{JEMAAI_CLOUD}/showroom_logos_isaiah_youtube_reading_pack_slice_v1.json",
                extra={
                    "logos_demo_spine_step": 2.2,
                    "companion_of": "meaning_topology_qa_v2",
                    "note_ko": "이사야 유튜브 16챕터 MKM bridge 3-Pack · [HYPO][NON_GATING]",
                },
            ),
            "logos_job_cosmic_code": _page(
                "/public_showroom_logos_job_cosmic_code_v1.html",
                extra={
                    "logos_demo_spine_step": 2.5,
                    "companion_of": "logos_job_reading_pack",
                    "note_ko": "욥기 OS·장별 슬라이더 교육 SPA",
                },
            ),
            "logos_research": _page(
                "/public_showroom_logos_research_v1.html",
                extra={"logos_demo_spine_step": 3},
            ),
            "logos_oracle_v6": _page(
                "/public_showroom_logos_oracle_v6.html",
                extra={
                    "legacy_observatory_demo": True,
                    "note": "Chronology overlay demo; prefer logos_demo_spine for sales walkthrough",
                },
            ),
            "logos_integrity_orb": _page(
                "/public_showroom_logos_integrity_orb_v1.html",
                extra={"api_mirror_primary": f"{JEMAAI_API}/public_showroom_logos_integrity_orb_v1.html"},
            ),
            "board_minimal": _page(
                "/public_showroom_board_minimal.html",
                extra={"hub_cta_default": f"{JEMAAI_API}/public_showroom_board_minimal.html"},
            ),
        },
        "deprecated_pages": {
            "logos_oracle_v3": {
                "path": "/public_showroom_logos_oracle_v3.html",
                "status": "deprecated",
                "redirect_to": "logos_oracle_v6",
            },
            "logos_oracle_v4": {
                "path": "/public_showroom_logos_oracle_v4.html",
                "status": "deprecated",
                "redirect_to": "logos_oracle_v6",
            },
            "logos_oracle_v5": {
                "path": "/public_showroom_logos_oracle_v5.html",
                "status": "deprecated",
                "redirect_to": "logos_oracle_v6",
            },
        },
        "api": {
            "public_events_latest": f"{JEMAAI_API}/api/public-events/latest",
        },
        "demo_script": "docs/final/artifacts/track_c_showroom_topology_sales_demo_script_v1_latest.md",
        "logos_graph_studio_30s_demo_script": (
            "docs/final/artifacts/logos_graph_studio_b2b_30s_demo_script_v1_latest.md"
        ),
        "logos_graph_studio_b2b_poc_one_pager": (
            "docs/final/artifacts/logos_graph_studio_b2b_poc_one_pager_v1_latest.md"
        ),
        "logos_graph_studio_pilot_sow_template": (
            "docs/final/artifacts/logos_graph_studio_pilot_sow_template_v1_latest.md"
        ),
        "logos_graph_studio_pilot_sow_executive_summary": (
            "docs/final/artifacts/logos_graph_studio_pilot_sow_executive_summary_v1_latest.md"
        ),
        "logos_graph_studio_b2b_meeting_pack_index": (
            "docs/final/artifacts/logos_graph_studio_b2b_meeting_pack_index_v1_latest.md"
        ),
        "logos_graph_studio_b2b_meeting_pack_readiness": (
            "reports/logos_graph_studio_b2b_meeting_pack_readiness_v1_latest.json"
        ),
        "publish_routine": "scripts/Invoke-ShowroomTrackCPublishRoutine_v1.ps1",
        "publish_daily_task": "scripts/Register-ShowroomTrackCPublishDailyTask.ps1",
        "nginx_weekly_task": "scripts/Register-ShowroomTrackCNginxWeeklyTask.ps1",
        "nginx_snippet_ssot": (
            "projects/bitcoin-trading/ops/windows-rehearsal/jemaai-cloud-mvp/"
            "nginx_snippets/jemaai_showroom_ui.conf"
        ),
        "vps_static_root": "/var/www/jemaai",
        "reproduce": "py scripts/build_jemaai_showroom_public_urls_v1.py",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-json", default=str(DEFAULT_OUT))
    args = parser.parse_args()
    out = Path(args.out_json)
    out.parent.mkdir(parents=True, exist_ok=True)
    doc = build_doc()
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(out), "spine": doc["logos_demo_spine"]["order"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
