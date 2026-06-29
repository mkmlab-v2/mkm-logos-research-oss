#!/usr/bin/env python3
"""Build Logos Research mobile shell hypo artifact (Capacitor-ready pointer)."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "docs/final/artifacts/logos_research_mobile_shell_hypo_v1_latest.json"


def build_doc() -> dict:
    return {
        "schema": "logos_research_mobile_shell_hypo_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "hypothesis_tier": "B",
        "research_only": True,
        "send_gate": "HOLD",
        "boundary_ack": "PWA v0 + native shell contract only; no App Store claim; curated presets not open LLM.",
        "server_url": "https://logos.jema-ai.com",
        "start_path": "/logos-research/studio",
        "home_path": "/logos-research",
        "app_id": "com.jemaai.logos.research",
        "app_name": "Logos Studio",
        "push_enabled": False,
        "screen_time_bridge": "not_wired",
        "offline_ingest_queue_schema": None,
        "manifest_path": "/logos-research/manifest.webmanifest",
        "capacitor_shell_dir": "projects/no1kmedi/logos-research-native-hypo-v1",
        "embedding_sidecar": {
            "script": "scripts/logos_studio_embedding_sidecar_v1.py",
            "default_port": 18765,
            "env_keys": [
                "LOGOS_STUDIO_EMBEDDING_SIDECAR",
                "LOGOS_STUDIO_EMBEDDING_SIDECAR_HOST",
                "LOGOS_STUDIO_EMBEDDING_SIDECAR_PORT",
            ],
        },
        "app_functions": [
            {"id": "studio_query", "label_ko": "그래프 Q&A", "intent_kind": "preset_router"},
            {"id": "conflict_sidecar", "label_ko": "학파 갈등면", "intent_kind": "bigset_sidecar"},
            {"id": "insight_lattice", "label_ko": "인사이트 격자", "intent_kind": "era_lattice"},
        ],
        "reproduce": "py scripts/build_logos_research_mobile_shell_hypo_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()
    doc = build_doc()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(args.out)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
