#!/usr/bin/env python3
"""Compare local vs prod graph_slice for router verse stub deploy gap.

Exit 0: local has required stubs (workspace ready to deploy).
Exit 1: local missing Jer.31.4 stub (run patch + sync first).

Reproduce:
  py scripts/check_logos_studio_graph_slice_deploy_gap_v1.py
"""

from __future__ import annotations

import json
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
LOCAL_SLICE = ROOT / "projects/no1kmedi/public/data/logos_studio/graph_slice_v1.json"
PROD_SLICE_URL = "https://logos.jema-ai.com/data/logos_studio/graph_slice_v1.json"
REQUIRED_REFS = ("Jer.31.4",)
OUT = ROOT / "reports/logos_studio_graph_slice_deploy_gap_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _jer_nodes(doc: dict[str, Any]) -> int:
    count = 0
    for node in doc.get("nodes") or []:
        blob = f"{node.get('id', '')} {node.get('ref', '')} {node.get('label', '')}"
        if any(ref in blob for ref in REQUIRED_REFS):
            count += 1
    return count


def _fetch_prod() -> dict[str, Any]:
    req = urllib.request.Request(PROD_SLICE_URL, headers={"User-Agent": "MKM-logos-deploy-gap/1.0"})
    with urllib.request.urlopen(req, timeout=45) as resp:
        return json.loads(resp.read().decode("utf-8", errors="replace"))


def main() -> int:
    if not LOCAL_SLICE.is_file():
        print(json.dumps({"ok": False, "error": "local_slice_missing"}, ensure_ascii=False))
        return 1

    local_doc = json.loads(LOCAL_SLICE.read_text(encoding="utf-8-sig"))
    local_jer = _jer_nodes(local_doc)
    prod_jer = 0
    prod_fetch_ok = False
    try:
        prod_doc = _fetch_prod()
        prod_jer = _jer_nodes(prod_doc)
        prod_fetch_ok = True
    except OSError as exc:
        prod_doc = {"error": str(exc)}

    deploy_pending = prod_fetch_ok and local_jer > 0 and prod_jer == 0
    local_ok = local_jer > 0

    doc = {
        "ok": local_ok,
        "schema": "logos_studio_graph_slice_deploy_gap_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "send_gate": "HOLD",
        "local_slice": str(LOCAL_SLICE.relative_to(ROOT)).replace("\\", "/"),
        "prod_slice_url": PROD_SLICE_URL,
        "local_jer_stub_nodes": local_jer,
        "prod_jer_stub_nodes": prod_jer,
        "prod_fetch_ok": prod_fetch_ok,
        "deploy_pending": deploy_pending,
        "solo_next_action": (
            "Deploy projects/no1kmedi (public/data/logos_studio/*) to logos.jema-ai.com"
            if deploy_pending
            else None
        ),
        "reproduce": "py scripts/check_logos_studio_graph_slice_deploy_gap_v1.py",
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": local_ok, "deploy_pending": deploy_pending, "artifact": str(OUT)}, ensure_ascii=False))
    return 0 if local_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
