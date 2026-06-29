#!/usr/bin/env python3
"""Deterministic 3-lens conflict one-liner from independent lens JSON + shadow gate."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports" / "lens_conflict_narrative_v1_latest.json"


def _read(path: Path) -> Dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return {}
    return raw if isinstance(raw, dict) else {}


def _sign(score: Any, *, heat: Any = None) -> str:
    if heat is not None:
        try:
            h = float(heat)
            if h >= 0.55:
                return "bull"
            if h <= 0.35:
                return "bear"
        except (TypeError, ValueError):
            pass
    try:
        x = float(score)
        if x > 0.08:
            return "bull"
        if x < -0.08:
            return "bear"
        return "flat"
    except (TypeError, ValueError):
        return "unknown"


def build_lens_conflict_narrative(workspace: Path | None = None) -> Dict[str, Any]:
    ws = (workspace or ROOT).resolve()
    art = ws / "docs" / "final" / "artifacts"
    my = _read(art / "myeongni_independent_lens_latest.json")
    lo = _read(art / "logos_independent_lens_latest.json")
    sa = _read(art / "sasang_independent_lens_latest.json")
    gate = _read(art / "independent_lens_shadow_gate_latest.json")

    my_s = (my.get("scores") or {}).get("direction_score")
    lo_s = (lo.get("scores") or {}).get("direction_score")
    sa_s = (sa.get("scores") or {}).get("direction_score")
    sa_out = sa.get("sasang_stream_outputs") if isinstance(sa.get("sasang_stream_outputs"), dict) else {}
    heat = (sa_out.get("machine_readables") or {}).get("heat_proxy")

    signs = {
        "myeongni": _sign(my_s),
        "logos": _sign(lo_s),
        "sasang": _sign(sa_s, heat=heat),
    }
    uniq = {v for v in signs.values() if v != "unknown"}
    agreement = 1.0 if len(uniq) <= 1 else (2 / 3.0 if len(uniq) == 2 else 0.0)
    minority = (gate.get("latest_conflict_snapshot") or {}).get("minority_lens_ids") or []

    parts = [
        f"명리 {signs['myeongni']}",
        f"성경 {signs['logos']}[NON_GATING]",
        f"사상 heat={heat}→{signs['sasang']}",
    ]
    if len(uniq) >= 2:
        narrative_ko = (
            f"{' · '.join(parts)} — 합의 약함(관측만, agreement~{agreement:.0%})"
        )
    else:
        narrative_ko = f"{' · '.join(parts)} — 3축 방향 근접(관측만)"

    return {
        "schema": "lens_conflict_narrative_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "hypothesis_tier": "B",
        "research_only": True,
        "lens_signs": signs,
        "agreement_rate_estimate": round(agreement, 4),
        "shadow_minority_lens_ids": minority,
        "narrative_ko": narrative_ko,
        "telegram_one_liner_ko": narrative_ko,
    }


def write_conflict_narrative(workspace: Path | None = None) -> Path:
    ws = (workspace or ROOT).resolve()
    doc = build_lens_conflict_narrative(ws)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return OUT


def main() -> int:
    p = write_conflict_narrative()
    doc = json.loads(p.read_text(encoding="utf-8"))
    print(doc["narrative_ko"])
    print(f"WROTE: {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
