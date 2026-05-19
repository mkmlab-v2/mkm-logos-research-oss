#!/usr/bin/env python3
"""Aggregate showroom Track C ops status from disk artifacts (Fact-Lock, no network)."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "final" / "artifacts" / "showroom_track_c_ops_status_v1_latest.json"


def _read_json(path: Path) -> dict | None:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def main() -> int:
    smoke = _read_json(ROOT / "reports" / "showroom_trust_viz_public_chain_smoke_latest.json")
    b2b = _read_json(ROOT / "reports" / "track_c_b2b_meeting_pack_readiness_v1_latest.json")
    meaning = _read_json(
        ROOT / "docs" / "final" / "artifacts" / "showroom_meaning_topology_graph_slice_v1_latest.json"
    )
    meta = (meaning or {}).get("meta") or {}
    stats = (meaning or {}).get("stats") or (meaning or {}).get("graph_stats") or {}
    node_count = stats.get("node_count") or (meaning or {}).get("node_count") or meta.get("node_count")
    edge_count = stats.get("edge_count") or (meaning or {}).get("edge_count") or meta.get("edge_count")
    if node_count is None and smoke:
        mp = (smoke.get("steps") or {}).get("meaning_json_payload") or {}
        node_count = mp.get("node_count")
        edge_count = mp.get("edge_count")
    urls = _read_json(ROOT / "docs" / "final" / "artifacts" / "jemaai_showroom_public_urls_v1_latest.json")

    payload = {
        "schema": "showroom_track_c_ops_status_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "dual_host_smoke_ok": bool(smoke and smoke.get("ok")),
        "public_events": (smoke or {}).get("steps", {}).get("public_events_payload"),
        "meaning_slice": {
            "node_count": node_count,
            "edge_count": edge_count,
        },
        "b2b_readiness": {
            "ready_for_internal_meeting": (b2b or {}).get("ready_for_internal_meeting"),
            "ready_for_external_send": (b2b or {}).get("ready_for_external_send"),
        },
        "canonical_urls": urls,
        "health_persona": "Invoke-MkmPersonaHealth_v1.ps1 -Persona ShowroomTrackCHealth",
        "publish_routine": "scripts/Invoke-ShowroomTrackCPublishRoutine_v1.ps1",
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(OUT)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
