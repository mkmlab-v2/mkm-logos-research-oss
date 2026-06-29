#!/usr/bin/env python3
"""Live preflight for B2B Graph Studio 30s rehearsal (HTTP markers + insight cards)."""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/logos_graph_studio_b2b_rehearsal_live_v1_latest.json"

QA_URL = (
    "https://api.jemaai.cloud/public_showroom_meaning_topology_qa_v2.html"
    "?preset=job_job_suffering_reason"
)
CANONICAL_QA = (
    "https://jemaai.cloud/public_showroom_meaning_topology_qa_v2.html"
    "?preset=job_job_suffering_reason"
)
INSIGHT_URL = "https://api.jemaai.cloud/showroom_qa_node_insight_cards_v1.json"
LOGOS_RESEARCH = "https://logos.jema-ai.com/logos-research"

HTML_MARKERS = (
    "insightPanel", "showInsightPanel", "path-chip", "cite-ref", "metaArchPanel", "META_ARCH_URL",
    "b2bDemoHero", "beginColdStart", "graphSkeleton",
    "runB2bAutoplayTimeline", "applyEmbedMode", "layerBB2bTimeline", "embed-hero",
    "citation-reveal", "b2bAutoplayBar", "data-layer-b-contract",
)
META_ARCH_URL = "https://api.jemaai.cloud/logos_cosmic_meta_architecture_ui_v1.json"
INSIGHT_ANCHORS = (
    "showroom_job_verse::Job.1.6",
    "showroom_psalm_verse::Ps.27.14",
    "theme::hope_endurance_psalm",
)
LOGOS_MARKERS = (
    "api.jemaai.cloud/public_showroom_meaning_topology_qa_v2.html",
    "api.jemaai.cloud/public_showroom_logos_job_reading_pack_v1.html",
    "data-layer-b-embed",
    "data-logos-graph-studio-embed",
    "30s autoplay",
)


def _fetch(url: str, *, head: bool = False) -> tuple[int, str, dict[str, str]]:
    req = urllib.request.Request(url, method="HEAD" if head else "GET")
    req.add_header("User-Agent", "mkm-logos-b2b-rehearsal-live/1")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = "" if head else resp.read().decode("utf-8", errors="replace")
            headers = {k.lower(): v for k, v in resp.headers.items()}
            return int(resp.status), body, headers
    except urllib.error.HTTPError as e:
        body = ""
        if not head:
            try:
                body = e.read().decode("utf-8", errors="replace")
            except Exception:
                pass
        return int(e.code), body, {}


def main() -> int:
    errors: list[str] = []
    steps: dict[str, Any] = {}

    for key, url in (
        ("qa_mirror", QA_URL),
        ("canonical_qa", CANONICAL_QA),
        ("insight_cards", INSIGHT_URL),
        ("cosmic_meta_arch_ui", META_ARCH_URL),
        ("logos_research", LOGOS_RESEARCH),
    ):
        code, body, headers = _fetch(url)
        steps[key] = {"url": url, "http_status": code}
        if code != 200:
            errors.append(f"{key}: expected 200 got {code}")
            continue
        if key == "insight_cards":
            try:
                doc = json.loads(body)
                cards = doc.get("cards") or {}
                steps[key]["card_count"] = len(cards)
                for anchor in INSIGHT_ANCHORS:
                    if anchor not in cards:
                        errors.append(f"insight_cards: missing {anchor}")
            except Exception as e:
                errors.append(f"insight_cards parse: {e}")
        elif key in ("qa_mirror", "canonical_qa"):
            missing = [m for m in HTML_MARKERS if m not in body]
            steps[key]["html_markers_missing"] = missing
            if missing:
                errors.append(f"{key}: missing markers {missing}")
        elif key == "cosmic_meta_arch_ui":
            try:
                doc = json.loads(body)
                steps[key]["schema"] = doc.get("schema")
                steps[key]["force_row_count"] = len(doc.get("force_rows") or [])
                if doc.get("schema") != "logos_cosmic_meta_architecture_ui_v1":
                    errors.append("cosmic_meta_arch_ui: schema mismatch")
            except Exception as e:
                errors.append(f"cosmic_meta_arch_ui parse: {e}")
        elif key == "logos_research":
            missing = [m for m in LOGOS_MARKERS if m not in body]
            steps[key]["demo_url_markers_missing"] = missing
            if missing:
                errors.append(f"logos_research: missing demo URLs {missing}")

    report = {
        "schema": "logos_graph_studio_b2b_rehearsal_live_v1",
        "checked_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "ok": len(errors) == 0,
        "steps": steps,
        "errors": errors,
        "reproducible_command": "py scripts/check_logos_graph_studio_b2b_rehearsal_live_v1.py",
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": report["ok"], "out": str(OUT), "errors": errors}))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
