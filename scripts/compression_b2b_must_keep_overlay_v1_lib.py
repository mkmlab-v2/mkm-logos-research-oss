"""B2B must_keep overlay helpers for stateless V2 API wiring. [HYPO]"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def overlay_path_for_external_sku(external_sku: str, *, workspace_root: Path = ROOT) -> Path:
    slug = external_sku.lower().replace("mkm-", "")
    return workspace_root / f"docs/final/artifacts/b2b_sku_{slug}_must_keep_overlay_v1.json"


def load_overlay_terms(path: Path) -> list[str]:
    doc = json.loads(path.read_text(encoding="utf-8-sig"))
    terms: list[str] = []
    seen: set[str] = set()
    for key in ("must_keep_hard_terms", "must_keep_soft_terms"):
        for t in doc.get(key) or []:
            if isinstance(t, str) and t.strip() and t.strip() not in seen:
                seen.add(t.strip())
                terms.append(t.strip())
    return terms
