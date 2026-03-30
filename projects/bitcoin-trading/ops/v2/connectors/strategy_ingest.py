from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()


def ingest_strategy(project_root: Path) -> dict:
    candidates = [
        project_root / "ops" / "v2" / "policies" / "STRATEGY.md",
        project_root / "STRATEGY.md",
        project_root.parent.parent / "docs" / "final" / "CONSTITUTION_COMMERCIALIZATION_PLAN_2026-03-22.md",
    ]

    for p in candidates:
        if p.exists():
            text = p.read_text(encoding="utf-8", errors="ignore")
            return {
                "strategy_path": str(p),
                "strategy_hash": _sha256(text),
                "strategy_preview": "\n".join(text.splitlines()[:12]),
                "strategy_loaded": True,
                "loaded_at_utc": datetime.now(timezone.utc).isoformat(),
            }

    return {
        "strategy_path": None,
        "strategy_hash": None,
        "strategy_preview": "",
        "strategy_loaded": False,
        "loaded_at_utc": datetime.now(timezone.utc).isoformat(),
        "note": "No strategy source file found",
    }
