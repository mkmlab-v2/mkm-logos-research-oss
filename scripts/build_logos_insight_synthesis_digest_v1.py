#!/usr/bin/env python3
"""Rich MD digest — dialectical + cross-theme + multi-insight + Bible AI refs [HYPO]."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"
ART = ROOT / "docs/final/artifacts"
OUT_DEFAULT = REPORTS / "logos_insight_synthesis_digest_v1_latest.md"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (json.JSONDecodeError, OSError):
        return None


def build_md() -> str:
    bridge = _load(REPORTS / "logos_cross_theme_invariant_bridge_v1_latest.json") or {}
    dialectical = _load(REPORTS / "logos_dialectical_insight_layers_v1_latest.json") or {}
    multi = _load(REPORTS / "logos_multi_insight_synthesis_v1_latest.json") or {}
    gaps = _load(REPORTS / "logos_insight_gap_audit_v1_latest.json") or {}
    mapping = _load(REPORTS / "logos_b2b_logic_mapping_audit_v1_latest.json") or {}
    refs = _load(ART / "logos_bible_ai_research_refs_v1.json") or {}

    lines = [
        "# Logos Track B — Advanced Insight Synthesis (Phase N)",
        "",
        "[TRACK B / HYPO] · [연구용 · NON_GATING · MS 헤드라인 합산 금지]",
        "",
        f"> 생성 `{_utc()}`",
        "",
        "## Bible AI 연구 참조 (엔지니어링만)",
        "",
    ]
    for ref in refs.get("refs") or []:
        lines.append(f"- **{ref.get('ref_id')}**: {ref.get('title')} — `{ref.get('adopted_technique')}`")
        lines.append(f"  - MKM mapping: {ref.get('mkm_mapping')}")
    lines.extend(["", "## Cross-Dimensional Bridge", ""])
    sm = bridge.get("summary") or {}
    lines.append(f"- shared hubs: **{sm.get('shared_hub_count')}** · invariants: **{sm.get('semantic_invariant_tags')}**")
    for hub in (bridge.get("shared_hubs") or [])[:5]:
        lines.append(f"  - hub `{hub.get('hub_verse_id')}` score={hub.get('bridge_score')}")
    for inv in bridge.get("semantic_invariants") or []:
        lines.append(f"  - invariant `{inv.get('invariant_id')}` dan={len(inv.get('dan_verse_ids') or [])} john={len(inv.get('john_verse_ids') or [])}")

    lines.extend(["", "## Dialectical Layers", ""])
    for theme in dialectical.get("themes") or []:
        lines.append(f"### {theme.get('theme_title_ko')} (`{theme.get('theme_id')}`)")
        for layer in theme.get("layers") or []:
            body = str(layer.get("body_ko") or "")[:500]
            valid = layer.get("citation_valid")
            lines.append(f"- **{layer.get('layer')}** · llm={layer.get('llm_invoked')} · valid={valid}")
            lines.append(f"  {body}")

    lines.extend(["", "## Multi-Insight Units", ""])
    msum = multi.get("summary") or {}
    lines.append(f"- units: **{msum.get('unit_count')}** · llm: **{msum.get('llm_units')}**")
    for unit in multi.get("insight_units") or []:
        body = str(unit.get("body_ko") or "")[:400]
        lines.append(f"- `{unit.get('insight_id')}` valid={unit.get('citation_valid')}")
        lines.append(f"  {body}")

    lines.extend(["", "## Gap Audit (Relink-style repair targets)", ""])
    gsum = gaps.get("summary") or {}
    lines.append(f"- hop gap pairs: **{gsum.get('hop_gap_pairs')}**")

    lines.extend(["", "## B2B Structure Mapping (not theology copy)", ""])
    mmap = mapping.get("summary") or {}
    lines.append(f"- verdict: **{mmap.get('verdict')}** · pass: `{mmap.get('mapping_pass')}`")
    for row in mapping.get("mappings") or []:
        lines.append(f"- `{row.get('dimension_id')}`: {row.get('mapping_possible')} — {row.get('note')}")

    lines.extend(["", "---", "재현: `py scripts/run_logos_track_b_phase_n_v1.py`", ""])
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    args = ap.parse_args()
    md = build_md()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(md, encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(args.out), "chars": len(md)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
