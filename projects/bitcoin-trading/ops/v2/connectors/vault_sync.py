from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


def build_vault_sync_manifest(project_root: Path) -> dict:
    memory_dir = project_root / "memory"
    outputs = [
        memory_dir / "kpi" / "latest_kpi.json",
        memory_dir / "brain_sync" / "latest.md",
        memory_dir / "v2" / "latest_state.json",
        memory_dir / "orchestrator" / "mvp_three_bots_latest.json",
    ]

    items = []
    for p in outputs:
        items.append(
            {
                "path": str(p),
                "exists": p.exists(),
                "mtime": datetime.fromtimestamp(p.stat().st_mtime, tz=timezone.utc).isoformat() if p.exists() else None,
            }
        )

    manifest = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "sync_mode": "headless-knowledge-base",
        "items": items,
        "next_step": "use memory/brain_sync/latest.md as NotebookLM daily source",
    }
    return manifest


def save_manifest(project_root: Path) -> Path:
    manifest = build_vault_sync_manifest(project_root)
    out = project_root / "memory" / "v2" / "vault_sync_manifest.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    return out
