#!/usr/bin/env python3
"""Human-visible hot-reload operator board — open this file after run [HYPO]."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"
OUT_DEFAULT = REPORTS / "logos_hot_reload_operator_board_v1_latest.md"


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (json.JSONDecodeError, OSError):
        return {}


def build() -> str:
    hot = _load(REPORTS / "logos_track_b_hot_reload_v1_latest.json")
    completion = _load(REPORTS / "logos_phase_o_completion_gate_v1_latest.json")
    phase_o = _load(REPORTS / "logos_track_b_phase_o_v1_latest.json")
    closure = _load(REPORTS / "logos_track_b_integration_closure_v1_latest.json")

    lines = [
        "# Logos Track B — Hot-Reload Operator Board",
        "",
        "> **이 파일을 연다** — 핫리로드는 Cursor UI에 자동 팝업되지 않습니다.",
        "",
        f"생성: `{datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}`",
        "",
        "## 한눈 요약",
        "",
        f"| 항목 | 값 |",
        f"|------|-----|",
        f"| hot_reload ok | **{hot.get('ok')}** |",
        f"| iterations | **{hot.get('iterations_run')}** / max {hot.get('max_iterations', 3)} |",
        f"| completion score | **{hot.get('final_completion_score')}** |",
        f"| phase_o ok | **{phase_o.get('ok')}** |",
        f"| integration_closure | **{closure.get('ok')}** |",
        f"| track_a_bridge | **{(closure.get('gates') or {}).get('track_a_bridge', False)}** |",
        "",
        "## 열 파일 (순서)",
        "",
        "1. `reports/logos_phase_o_digest_v1_latest.md` — Phase O 통찰 요약",
        "2. `docs/final/artifacts/logos_neuro_symbolic_b2b_public_one_pager_ko_v1.md` — **대외·제안서용 1p**",
        "3. `reports/logos_hot_reload_operator_board_v1_latest.md` — **본 파일 (운영 보드)**",
        "3. `reports/logos_track_b_hot_reload_v1_latest.json` — 머신 manifest",
        "4. `reports/logos_phase_o_completion_gate_v1_latest.json` — 9항목 점수",
        "5. `reports/logos_track_b_commander_dual_theme_digest_latest.md` — Commander (별도 L/N 체인)",
        "",
        "## Completion checks",
        "",
    ]
    for chk in completion.get("checks") or []:
        mark = "PASS" if chk.get("pass") else "FAIL"
        lines.append(f"- [{mark}] `{chk.get('check_id')}` — {chk.get('note', '')}")

    failed = (completion.get("summary") or {}).get("failed_checks") or []
    if failed:
        lines.extend(["", f"**실패 항목:** {', '.join(failed)}", ""])

    lines.extend(
        [
            "## Hot-reload iterations",
            "",
        ]
    )
    for it in hot.get("iterations") or []:
        lines.append(
            f"- iter **{it.get('iteration')}**: score={it.get('completion_score')} ok={it.get('ok')}"
        )

    lex_audit = _load(REPORTS / "logos_41k_4d_reclassification_audit_v1_latest.json")
    cov = lex_audit.get("phase_pb_lexicon_coverage") or {}
    shadow = lex_audit.get("phase_pc_path_four_d_shadow") or {}
    if cov or shadow:
        lines.extend(
            [
                "",
                "## Lexicon 4D shadow (Phase P · NON_GATING)",
                "",
                f"| 지표 | 값 |",
                f"|------|-----|",
                f"| lexicon_4d_coverage | **{cov.get('lexicon_4d_coverage_rate')}** ({cov.get('lexicon_4d_row_count')}/{cov.get('codebook_atom_count')}) |",
                f"| mean_four_d_coherence | **{shadow.get('mean_four_d_coherence')}** |",
                f"| human_review_hint | **{shadow.get('human_review_hint_count')}** units (&lt;0.8) |",
                f"| gate_pass 영향 | **없음** (shadow only) |",
                "",
            ]
        )
        hints = [u for u in (shadow.get("units") or []) if u.get("human_review_hint")]
        if hints:
            lines.append("**HITL 검토 후보 (자동 락 없음):**")
            lines.append("")
            for u in hints[:8]:
                lines.append(
                    f"- `{u.get('unit_id')}` coherence={u.get('four_d_coherence')} · v_score={u.get('v_score_primary')}"
                )
            lines.append("")

    opt = _load(REPORTS / "optimization_impact_v1_latest.json")
    if opt:
        d = opt.get("delta_shadow_minus_raw") or {}
        lines.extend(
            [
                "## Track A compression shadow impact (NON_GATING)",
                "",
                f"| 지표 | delta(shadow-raw) |",
                f"|------|-------------------:|",
                f"| token_saving_rate | **{d.get('global_token_saving_rate')}** |",
                f"| jaccard | **{d.get('avg_reconstruction_fidelity_jaccard')}** |",
                f"| sensitive_integrity | **{d.get('avg_sensitive_integrity')}** |",
                "",
                "- production policy unchanged · Track A direct bridge 금지",
                "",
            ]
        )

    q = _load(REPORTS / "shadow_postits_quality_gate_v1_latest.json")
    s = _load(REPORTS / "tracka_shadow_sweep_v1_latest.json")
    preset = _load(REPORTS / "tracka_shadow_default_preset_v1_latest.json")
    if q or s or preset:
        lines.extend(
            [
                "## Shadow quality & sweep",
                "",
                f"- postit_quality_ok: **{(q.get('summary') or {}).get('overall_ok')}**",
                f"- term_rows / verse_rows: **{(q.get('summary') or {}).get('term_rows')} / {(q.get('summary') or {}).get('verse_rows')}**",
                f"- sweep pareto candidates: **{len(s.get('pareto_top5') or [])}**",
                f"- shadow preset terms: **{preset.get('selected_terms_count')}**",
                f"- preset delta jaccard: **{(preset.get('delta_shadow_minus_raw') or {}).get('avg_reconstruction_fidelity_jaccard')}**",
                "",
            ]
        )

    lines.extend(
        [
            "",
            "## 재현",
            "",
            "```powershell",
            "py scripts/run_logos_track_b_hot_reload_v1.py --verbose",
            "```",
            "",
            "[TRACK B / HYPO] · NON_GATING · MS 헤드라인 합산 금지",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    ap.add_argument("--print", dest="print_board", action="store_true", help="Also print board to stdout")
    args = ap.parse_args()
    md = build()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(md, encoding="utf-8")
    if args.print_board:
        print(md)
    else:
        print(json.dumps({"ok": True, "board": str(args.out), "chars": len(md)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
