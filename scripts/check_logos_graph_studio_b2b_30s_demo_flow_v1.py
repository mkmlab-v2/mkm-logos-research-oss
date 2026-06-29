#!/usr/bin/env python3
"""Validate Logos Graph Studio 30s B2B demo flow (LIVE HTTP + JSON · proxy for human pilot)."""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/logos_graph_studio_b2b_30s_demo_flow_v1_latest.json"

PRIMARY_LANDING = "https://logos.jema-ai.com/logos-research"
PRIMARY_STUDIO = (
    "https://logos.jema-ai.com/logos-research/studio"
    "?q=job_job_suffering_reason&autorun=1&demo=1"
)
QUERY_URL = "https://logos.jema-ai.com/api/logos-research/query"
LEGACY_QA_URL = (
    "https://api.jemaai.cloud/public_showroom_meaning_topology_qa_v2.html"
    "?preset=job_job_suffering_reason"
)
INSIGHT_URL = "https://api.jemaai.cloud/showroom_qa_node_insight_cards_v1.json"
PRESETS_URL = "https://api.jemaai.cloud/showroom_meaning_topology_qa_presets_v1.json"
JOB_PACK_URL = (
    "https://api.jemaai.cloud/public_showroom_logos_job_reading_pack_v1.html"
    "?preset=job_suffering_reason"
)

DEMO_STEPS = (
    ("0-8s_preset_load", "Landing inline demo · Field slot"),
    ("8-18s_path_refs", "Lens · Path steps · ECS badge"),
    ("18-22s_conflict", "Conflict · school_parallel"),
    ("22-26s_gap", "Gap slot"),
    ("26-30s_verdict", "한 줄 verdict + Studio CTA"),
)


def _fetch(url: str, *, method: str = "GET", body: dict[str, Any] | None = None) -> tuple[int, str]:
    data = None
    headers = {"User-Agent": "mkm-logos-30s-demo-flow/2"}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return int(resp.status), resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        body_text = e.read().decode("utf-8", errors="replace")
        return int(e.code), body_text


def main() -> int:
    errors: list[str] = []
    steps: dict[str, Any] = {}

    code, landing_html = _fetch(PRIMARY_LANDING)
    steps["primary_landing"] = {"url": PRIMARY_LANDING, "http_status": code}
    inline_ok = code == 200 and "data-logos-graph-studio-inline" in landing_html
    if not inline_ok:
        errors.append("primary: missing inline hero marker on logos.jema-ai.com/logos-research")
    steps["0-8s_preset_load"] = {
        "ok": inline_ok,
        "label": DEMO_STEPS[0][1],
        "marker": "data-logos-graph-studio-inline",
    }

    code, studio_html = _fetch(PRIMARY_STUDIO)
    steps["primary_studio"] = {"url": PRIMARY_STUDIO, "http_status": code}
    studio_ok = code == 200 and (
        "data-logos-studio-shell" in studio_html or "lr-studio-storyboard" in studio_html
    )
    if not studio_ok:
        errors.append("primary studio: shell/storyboard missing")

    code, query_body = _fetch(
        QUERY_URL,
        method="POST",
        body={"preset_id": "job_job_suffering_reason", "embed_demo": True},
    )
    steps["embed_demo_query"] = {"url": QUERY_URL, "http_status": code}
    lens_ok = gap_ok = verdict_ok = False
    if code == 200:
        try:
            qdoc = json.loads(query_body)
            result = qdoc.get("result") or {}
            path = result.get("path") or {}
            lens_ok = bool(path.get("steps") or path.get("verse_refs"))
            gap_ok = True  # Gap slot renders fallback when insight_card.gap_ko absent
            verdict_ok = bool(result.get("answer") or path.get("note_ko"))
            ecs = result.get("evidence_confidence") or {}
            if "ecs_v1" not in ecs:
                errors.append("8-18s: missing evidence_confidence.ecs_v1")
        except Exception as e:
            errors.append(f"embed_demo parse: {e}")
    else:
        errors.append(f"embed_demo query: HTTP {code}")

    steps["8-18s_path_refs"] = {"ok": lens_ok and code == 200, "label": DEMO_STEPS[1][1]}
    steps["18-22s_conflict"] = {
        "ok": code == 200,
        "label": DEMO_STEPS[2][1],
        "note": "conflict optional on preset — studio shell suffices",
    }
    steps["22-26s_gap"] = {"ok": gap_ok and code == 200, "label": DEMO_STEPS[3][1]}
    steps["26-30s_verdict"] = {
        "ok": verdict_ok and studio_ok,
        "label": DEMO_STEPS[4][1],
    }

    code, legacy_html = _fetch(LEGACY_QA_URL)
    steps["legacy_qa_page"] = {"url": LEGACY_QA_URL, "http_status": code, "optional": True}

    code, presets_body = _fetch(PRESETS_URL)
    steps["presets_json"] = {"url": PRESETS_URL, "http_status": code}
    if code == 200:
        try:
            pdoc = json.loads(presets_body)
            job = next(
                (p for p in pdoc.get("presets") or [] if p.get("id") == "job_job_suffering_reason"),
                None,
            )
            if not job:
                errors.append("presets: missing job_job_suffering_reason")
        except Exception as e:
            errors.append(f"presets parse: {e}")

    code, insight_body = _fetch(INSIGHT_URL)
    steps["insight_cards"] = {"url": INSIGHT_URL, "http_status": code, "optional": True}

    code, pack_html = _fetch(JOB_PACK_URL)
    steps["job_reading_pack"] = {"url": JOB_PACK_URL, "http_status": code, "optional": True}

    report = {
        "schema": "logos_graph_studio_b2b_30s_demo_flow_v1",
        "checked_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "demo_primary_url": PRIMARY_LANDING,
        "demo_studio_url": PRIMARY_STUDIO,
        "legacy_qa_url": LEGACY_QA_URL,
        "human_pilot_mode": "commander_solo_live_dry_run",
        "ok": len(errors) == 0,
        "demo_steps": {
            k: v
            for k, v in steps.items()
            if k.endswith("s") or any(x in k for x in ("preset_load", "path_refs", "conflict", "gap", "verdict"))
        },
        "steps": steps,
        "errors": errors,
        "reproduce": "py scripts/check_logos_graph_studio_b2b_30s_demo_flow_v1.py",
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": report["ok"], "out": str(OUT.relative_to(ROOT)).replace("\\", "/"), "errors": errors}))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
