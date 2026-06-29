#!/usr/bin/env python3
"""Phase O MD digest — Psi + simplicial + B2B chain + path gate [HYPO]."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"
OUT_DEFAULT = REPORTS / "logos_phase_o_digest_v1_latest.md"


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (json.JSONDecodeError, OSError):
        return {}


def build() -> str:
    refs = _load(ROOT / "docs/final/artifacts/logos_bible_ai_research_refs_v1.json")
    psi = _load(REPORTS / "logos_psi_logic_extraction_v1_latest.json")
    simplicial = _load(REPORTS / "logos_causal_simplicial_snapshot_v1_latest.json")
    chain = _load(REPORTS / "logos_b2b_deterministic_chain_v1_latest.json")
    completion = _load(REPORTS / "logos_phase_o_completion_gate_v1_latest.json")
    path_gate = _load(REPORTS / "logos_path_verification_gate_v1_latest.json")
    ledger = _load(REPORTS / "logos_track_b_research_v1_latest.json")

    lines = [
        "# Logos Track B — Phase O (Ψ Logic Transplant + Simplicial Ledger)",
        "",
        "[TRACK B / HYPO] · [연구용 · NON_GATING · MS 헤드라인 합산 금지]",
        "",
        f"> 생성 `{datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}`",
        "",
        "## Content ↔ Logic 격벽 (Ψ)",
        "",
        f"- theology tokens filtered: **{(psi.get('logic_graph') or {}).get('psi_metadata', {}).get('theology_tokens_filtered', 0)}**",
        f"- logic nodes: **{len((psi.get('logic_graph') or {}).get('nodes') or [])}**",
        f"- structure_transplant_only: **{psi.get('structure_transplant_only')}**",
        "",
        "## Simplicial dependency ledger (DEMOCRITUS-inspired)",
        "",
        f"- hub triangles seeded: **{simplicial.get('hub_triangles_seeded', 0)}**",
        f"- engine nodes/edges/triangles: **{(simplicial.get('engine_snapshot') or {}).get('node_count', 0)}** / "
        f"**{(simplicial.get('engine_snapshot') or {}).get('edge_count', 0)}** / "
        f"**{(simplicial.get('engine_snapshot') or {}).get('triangle_count', 0)}**",
        f"- ledger records: **{ledger.get('record_count', len(ledger.get('records') or []))}**",
        "",
    ]
    for ev in simplicial.get("evaluations") or []:
        q = ev.get("query") or {}
        e = ev.get("evaluation") or {}
        lines.append(
            f"  - path `{q.get('start')}` → `{q.get('end')}`: "
            f"found={e.get('path_found')} type={e.get('path_type')}"
        )

    lines.extend(
        [
            "",
            "## B2B 3-stage deterministic chain",
            "",
            f"- coherence_ok: **{(chain.get('summary') or {}).get('coherence_ok')}**",
            f"- beta_resolved: **{(chain.get('summary') or {}).get('beta_resolved')}**",
            f"- hot_reload_iterations: **{(chain.get('summary') or {}).get('hot_reload_iterations', 0)}**",
            f"- HITL checkpoints: **{(chain.get('summary') or {}).get('hitl_checkpoint_count', 0)}**",
        ]
    )
    s2 = (chain.get("stages") or {}).get("stage2_intertextual_conflict") or {}
    for v in s2.get("violations") or []:
        lines.append(f"  - violation `{v.get('rule')}`: {v.get('issue')}")

    cg = completion.get("summary") or {}
    lines.extend(
        [
            "",
            "## Completion gate (hot-reload)",
            "",
            f"- score: **{completion.get('completion_score', 0)}** / target **{completion.get('completion_target', 90)}**",
            f"- pass: **{completion.get('completion_pass')}**",
        ]
    )
    if cg.get("failed_checks"):
        lines.append(f"- failed: {', '.join(cg['failed_checks'])}")

    pg = path_gate.get("summary") or {}
    lines.extend(
        [
            "",
            "## Path verification V(S_i)",
            "",
            f"- units checked: **{pg.get('units_checked', 0)}**",
            f"- pass_rate: **{pg.get('pass_rate', 0)}** (threshold {pg.get('gate_threshold', 0.85)})",
            f"- gate_pass: **{pg.get('gate_pass')}**",
            "",
            "## Extended Bible AI / classical refs",
            "",
        ]
    )
    for ref in refs.get("refs") or []:
        if ref.get("ref_id", "").startswith(("democritus", "tsk_", "semantic", "imkg", "four_histories")):
            lines.append(f"- **{ref.get('ref_id')}**: {ref.get('title')}")

    lines.extend(
        [
            "",
            "---",
            "재현: `py scripts/run_logos_track_b_hot_reload_v1.py --verbose`",
            "핫리로드 보드: `reports/logos_hot_reload_operator_board_v1_latest.md`",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    args = ap.parse_args()
    md = build()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(md, encoding="utf-8")
    print(json.dumps({"ok": True, "chars": len(md), "out": str(args.out)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
