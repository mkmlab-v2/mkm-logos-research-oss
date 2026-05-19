#!/usr/bin/env python3
"""HTTP smoke: showroom public pages (dual-host) + public-events API."""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports" / "showroom_trust_viz_public_chain_smoke_latest.json"

CANONICAL = "https://jemaai.cloud"
API_MIRROR = "https://api.jemaai.cloud"

URLS: dict[str, str] = {
    "trust_html": f"{API_MIRROR}/public_showroom_trust_visualization_v0.html",
    "trust_json": f"{API_MIRROR}/showroom_trust_visualization_slice_v0.json",
    "meaning_graph_canonical": f"{CANONICAL}/public_showroom_meaning_topology_graph_v1.html",
    "meaning_graph_mirror": f"{API_MIRROR}/public_showroom_meaning_topology_graph_v1.html",
    "meaning_json_canonical": f"{CANONICAL}/showroom_meaning_topology_graph_slice_v1.json",
    "meaning_json_mirror": f"{API_MIRROR}/showroom_meaning_topology_graph_slice_v1.json",
    "radar_canonical": f"{CANONICAL}/public_showroom_topology_radar_v1.html",
    "radar_mirror": f"{API_MIRROR}/public_showroom_topology_radar_v1.html",
    "public_events_latest": f"{API_MIRROR}/api/public-events/latest",
}


def _fetch(url: str, *, head: bool = False) -> tuple[int, bytes, dict[str, str]]:
    req = urllib.request.Request(url, method="HEAD" if head else "GET")
    req.add_header("User-Agent", "mkm-showroom-trust-viz-smoke/1")
    with urllib.request.urlopen(req, timeout=20) as resp:
        body = b"" if head else resp.read()
        headers = {k.lower(): v for k, v in resp.headers.items()}
        return int(resp.status), body, headers


def main() -> int:
    errors: list[str] = []
    steps: dict[str, Any] = {}

    html_keys = {
        "trust_html",
        "meaning_graph_canonical",
        "meaning_graph_mirror",
        "radar_canonical",
        "radar_mirror",
    }
    for key, url in URLS.items():
        try:
            use_head = key in html_keys
            code, body, headers = _fetch(url, head=use_head)
            if use_head and code != 200:
                code, body, headers = _fetch(url, head=False)
            steps[key] = {"url": url, "http_status": code, "content_type": headers.get("content-type")}
            if code != 200:
                errors.append(f"{key}: expected 200 got {code}")
            elif key == "public_events_latest":
                try:
                    doc = json.loads(body.decode("utf-8"))
                    if doc.get("schema_version") != "public-event.v1":
                        errors.append("public_events_latest: schema_version not public-event.v1")
                    steps["public_events_payload"] = {
                        "event_id": doc.get("event_id"),
                        "system_status": doc.get("system_status"),
                        "public_signal_direction": doc.get("public_signal_direction"),
                    }
                except Exception as e:
                    errors.append(f"public_events_latest parse: {e}")
        except urllib.error.HTTPError as e:
            steps[key] = {"url": url, "http_status": e.code, "error": str(e)}
            errors.append(f"{key}: HTTP {e.code}")
        except Exception as e:
            steps[key] = {"url": url, "error": str(e)}
            errors.append(f"{key}: {e}")

    doc: dict[str, Any] | None = None
    if steps.get("trust_json", {}).get("http_status") == 200:
        try:
            _, body, _ = _fetch(URLS["trust_json"])
            doc = json.loads(body.decode("utf-8"))
            if doc.get("schema") != "showroom_trust_visualization_slice_v0":
                errors.append("trust_json: schema mismatch")
            tv = doc.get("trust_visualization_v0") or {}
            if not isinstance(tv, dict) or not tv.get("final_action"):
                errors.append("trust_json: trust_visualization_v0.final_action missing")
            cg = doc.get("compression_governance_v0") or {}
            steps["trust_json_payload"] = {
                "trust_state": tv.get("state"),
                "final_action": tv.get("final_action"),
                "compression_policy_floor": cg.get("policy_floor"),
            }
        except Exception as e:
            errors.append(f"trust_json parse: {e}")

    html_ok = steps.get("trust_html", {}).get("http_status") == 200
    if html_ok and doc:
        try:
            _, html_body, _ = _fetch(URLS["trust_html"])
            html = html_body.decode("utf-8", errors="replace")
            if "showroom_trust_visualization_slice_v0.json" not in html:
                errors.append("trust_html: missing fetch target for slice JSON")
        except Exception as e:
            errors.append(f"trust_html body: {e}")

    if steps.get("meaning_json_canonical", {}).get("http_status") == 200:
        try:
            _, body, _ = _fetch(URLS["meaning_json_canonical"])
            mg = json.loads(body.decode("utf-8"))
            steps["meaning_json_payload"] = {
                "schema_version": mg.get("schema_version"),
                "node_count": len(mg.get("nodes") or []),
                "edge_count": len(mg.get("edges") or []),
            }
            if mg.get("schema_version") != "showroom_meaning_topology_graph_slice_v1":
                errors.append("meaning_json_canonical: schema_version mismatch")
        except Exception as e:
            errors.append(f"meaning_json_canonical parse: {e}")

    report = {
        "schema": "showroom_trust_viz_public_chain_smoke_v1",
        "checked_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "canonical_host": CANONICAL,
        "api_mirror_host": API_MIRROR,
        "ok": len(errors) == 0,
        "steps": steps,
        "errors": errors,
        "nginx_reload_hint": "JEMAAI_VPS_RELOAD_NGINX=1 + scripts/sync_showroom_to_vps.ps1",
        "snippet_ssot": "projects/bitcoin-trading/ops/windows-rehearsal/jemaai-cloud-mvp/nginx_snippets/jemaai_showroom_ui.conf",
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"ok": report["ok"], "out": str(OUT.relative_to(ROOT)).replace("\\", "/"), "errors": errors}, ensure_ascii=False))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
