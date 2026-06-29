#!/usr/bin/env python3
"""Build four separate Telegram reports: 명리 · 성경(Logos) · 사상 · 종합.

B-track [HYPO] · [NON_GATING] for Logos · no live trading triggers.
"""

from __future__ import annotations

import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
KST = ZoneInfo("Asia/Seoul")
TELEGRAM_MAX = 4096

DEFAULT_PATHS = {
    "myeongni": "docs/final/artifacts/myeongni_independent_lens_from_chain_latest.json",
    "logos_md": "reports/logos_2026_market_news_prophecy_graphrag_v1_latest.md",
    "sasang_md": "reports/sasang_rule_based_response_v1_latest.md",
}


def _read_json(path: Path) -> Dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return {}
    return raw if isinstance(raw, dict) else {}


def _resolve_path(workspace: Path, key: str, default_rel: str) -> Path:
    env_key = f"MKM_TELEGRAM_{key.upper()}_REPORT_PATH"
    env = os.getenv(env_key, "").strip()
    if env:
        p = Path(env)
        return p if p.is_absolute() else workspace / p
    return workspace / default_rel


def _extract_md_section(md: str, heading_prefix: str) -> str:
    lines = md.splitlines()
    start = None
    for i, line in enumerate(lines):
        if line.strip().startswith("##") and heading_prefix in line:
            start = i + 1
            break
    if start is None:
        return ""
    out: List[str] = []
    for line in lines[start:]:
        if line.startswith("## "):
            break
        if line.strip() in ("", "---"):
            continue
        s = line.strip()
        if s.startswith("|") and not set(s.replace("|", "").strip()) <= {"-"}:
            cells = [c.strip() for c in s.split("|") if c.strip()]
            out.append(" · ".join(cells[:5]))
            continue
        if s.startswith("```"):
            continue
        out.append(s.lstrip("#").strip())
    return "\n".join(x for x in out if x).strip()


def _ko_dir(score: Any) -> str:
    try:
        x = float(score)
        if x > 0.08:
            return "상승(중기)"
        if x < -0.08:
            return "하락(중기)"
        return "횡보(중기)"
    except (TypeError, ValueError):
        return "—"


def _commander_life_oracle_prefix(workspace: Path) -> str:
    if os.getenv("MKM_TELEGRAM_INCLUDE_COMMANDER_LIFE_ORACLE", "1").strip().lower() in (
        "0",
        "false",
        "no",
        "off",
    ):
        return ""
    fortune_path = workspace / "reports" / "commander_daily_fortune_latest.json"
    if not fortune_path.is_file():
        return ""
    doc = _read_json(fortune_path)
    if doc.get("schema") not in ("commander_daily_fortune_v1", "commander_daily_fortune_v1_1"):
        return ""
    oracle = doc.get("life_oracle") if isinstance(doc.get("life_oracle"), dict) else {}
    compact = oracle.get("telegram_compact_lines") or []
    if compact:
        return "\n".join(ln for ln in compact if ln).strip() + "\n\n"
    block: List[str] = []
    for ln in doc.get("telegram_append_lines") or []:
        if not ln:
            continue
        if ln.startswith("▸ 하루 예언") or (
            block and ln.startswith("  ") and not ln.startswith("  ▸")
        ):
            block.append(ln)
        if ln.startswith("  경계:") and "임상" in ln:
            block.append(ln)
            break
    return ("\n".join(block).strip() + "\n\n") if block else ""


def build_myeongni_report(workspace: Path) -> str:
    personal = _commander_life_oracle_prefix(workspace)
    path = _resolve_path(workspace, "myeongni", DEFAULT_PATHS["myeongni"])
    doc = _read_json(path)
    gate = _read_json(workspace / "docs/final/artifacts/independent_lens_shadow_gate_latest.json")
    scores = doc.get("scores") if isinstance(doc.get("scores"), dict) else {}
    adv = doc.get("advanced") if isinstance(doc.get("advanced"), dict) else {}
    inp = adv.get("input_summary") if isinstance(adv.get("input_summary"), dict) else {}
    pillars = inp.get("pillars") if isinstance(inp.get("pillars"), dict) else {}
    coord = adv.get("coordinator") if isinstance(adv.get("coordinator"), dict) else {}
    math = coord.get("mkm_myeongni_math") if isinstance(coord.get("mkm_myeongni_math"), dict) else {}
    now = datetime.now(KST).strftime("%Y-%m-%d %H:%M KST")
    lines = [
        f"📘 MKM 명리 보고서 · {now}",
        "[HYPO] B-track · 만세력 결정론 · 실매매 트리거 아님",
        "",
        "━━ 사주(四柱) ━━",
        f"  년 {pillars.get('year','—')} · 월 {pillars.get('month','—')} · 일 {pillars.get('day','—')} · 시 {pillars.get('hour','—')}",
        "",
        "━━ 중기 방향(독립 렌즈) ━━",
        f"  direction_score={scores.get('direction_score','—')} → {_ko_dir(scores.get('direction_score'))}",
        f"  confidence={scores.get('confidence','—')} · state_id={doc.get('myeongri_stream_outputs',{}).get('state_id','—') if isinstance(doc.get('myeongri_stream_outputs'),dict) else '—'}",
    ]
    if math.get("status") == "ok":
        lines.extend(
            [
                "",
                "━━ 오행·십신(고도화 스텁) ━━",
                f"  일간 {math.get('day_master_stem','—')} · surface 십신 {math.get('surface_ten_god_counts',{})}",
            ]
        )
    schools = inp.get("school_blend") if isinstance(inp.get("school_blend"), dict) else {}
    if schools:
        lines.append(f"  학파 blend dir={schools.get('direction_score','—')} conf={schools.get('confidence','—')}")
    dec = (gate.get("decision") or gate.get("promotion_decision") or "—") if gate else "—"
    obs = _read_json(workspace / "reports" / "myeongni_lens_observation_report_v1_latest.json")
    lines.extend(
        [
            "",
            "━━ 주간 게이트 ━━",
            f"  shadow_gate={dec} · A-track 자동합선 금지",
        ]
    )
    if obs.get("separation_contract_ok"):
        snaps = obs.get("snapshots") if isinstance(obs.get("snapshots"), dict) else {}
        lines.append(
            f"  관측: chain={snaps.get('chain_direction_ko','—')} · market={snaps.get('market_direction_ko','—')} (분리·적중단정 아님)"
        )
    lines.append(f"SSOT: {path.name}")
    text = personal + "\n".join(lines)
    return text[:TELEGRAM_MAX]


def build_logos_report(workspace: Path) -> str:
    path = _resolve_path(workspace, "logos_md", DEFAULT_PATHS["logos_md"])
    logos_lens = _read_json(workspace / "docs/final/artifacts/logos_independent_lens_latest.json")
    now = datetime.now(KST).strftime("%Y-%m-%d %H:%M KST")
    if not path.is_file():
        return f"📜 MKM 성경(Logos) 보고서 · {now}\n(없음: {path.name})"
    md = path.read_text(encoding="utf-8-sig")
    s0 = _extract_md_section(md, "0. 해석")
    s1 = _extract_md_section(md, "1. Field")
    risk = _extract_md_section(md, "2.1")
    lines = [
        f"📜 MKM 성경(Logos) 보고서 · {now}",
        "[HYPO][NON_GATING] · GraphRAG 서사 · 매매 트리거 아님",
        "",
        "━━ 한 줄 ━━",
        (s0.split("\n")[0] if s0 else "상징·서사 추적만")[:400],
        "",
        "━━ Field→Lens→Conflict ━━",
    ]
    for ln in (s1 or "").split("\n")[:14]:
        lines.append(f"  {ln[:220]}")
    ls = logos_lens.get("scores") if isinstance(logos_lens.get("scores"), dict) else {}
    lines.extend(
        [
            "",
            "━━ 독립 렌즈 수치(보조) ━━",
            f"  direction_score={ls.get('direction_score','—')} conf={ls.get('confidence','—')}",
        ]
    )
    if risk:
        lines.extend(["", "━━ risk-off 앵커(발췌) ━━", f"  {risk.split(chr(10))[0][:220]}"])
    oos = _read_json(workspace / "docs/final/artifacts/prophecy_logos_revalidation_oos_gate_latest.json")
    om = oos.get("oos_metrics") if isinstance(oos.get("oos_metrics"), dict) else {}
    if om.get("directional_hit_rate_active") is not None:
        lines.extend(
            [
                "",
                "━━ OOS D(SSOT·[NON_GATING]) ━━",
                f"  hit={om.get('directional_hit_rate_active')} n_active={om.get('n_active_days')} "
                f"(golden sparse KOSPI · 승격 아님)",
            ]
        )
    cmp = _read_json(workspace / "reports/logos_oos_sidecar_variant_compare_v1_latest.json")
    for v in cmp.get("variants") or []:
        if not isinstance(v, dict) or v.get("missing"):
            continue
        lab = str(v.get("label") or "")
        if lab in ("hybrid_ext", "birth_sw025", "birth_sw025_band006") and v.get("oos_hit") is not None:
            lines.append(
                f"  [HYPO] {lab}: hit={v.get('oos_hit')} n={v.get('oos_n_active')} (연구·미승격)"
            )
    lines.append(f"\nSSOT: {path.name}")
    return "\n".join(lines)[:TELEGRAM_MAX]


def build_sasang_report(workspace: Path) -> str:
    path = _resolve_path(workspace, "sasang_md", DEFAULT_PATHS["sasang_md"])
    sasang_lens = _read_json(workspace / "docs/final/artifacts/sasang_independent_lens_latest.json")
    now = datetime.now(KST).strftime("%Y-%m-%d %H:%M KST")
    if not path.is_file():
        return f"🌡 MKM 사상 보고서 · {now}\n(없음: {path.name})"
    md = path.read_text(encoding="utf-8-sig")
    conclusion = _extract_md_section(md, "5) 결론") or _extract_md_section(md, "5.")
    lines = [
        f"🌡 MKM 사상 보고서 · {now}",
        "[HYPO] · 단기 강도·열 proxy · 임상·매매 합선 금지",
        "",
        "━━ 4상·열 proxy ━━",
    ]
    for ln in md.splitlines():
        if ln.strip().startswith("- top_axis") or ln.strip().startswith("- fused_axis"):
            lines.append(f"  {ln.strip()}")
    out = sasang_lens.get("sasang_stream_outputs") if isinstance(sasang_lens.get("sasang_stream_outputs"), dict) else {}
    mr = out.get("machine_readables") if isinstance(out.get("machine_readables"), dict) else {}
    if mr:
        lines.append(
            f"  heat={mr.get('heat_proxy','—')} cold={mr.get('cold_proxy','—')} "
            f"vol_rare={mr.get('volatility_rarefaction_proxy','—')}"
        )
    sc = sasang_lens.get("scores") if isinstance(sasang_lens.get("scores"), dict) else {}
    lines.extend(
        [
            "",
            "━━ 단기 강도 ━━",
            f"  direction_score={sc.get('direction_score','—')} · regime={out.get('regime_hypothesis','—')}",
            "",
            "━━ 결론(발췌) ━━",
        ]
    )
    for ln in (conclusion or "WATCH_CONFIRMATION").split("\n")[:6]:
        lines.append(f"  {ln[:200]}")
    obs = _read_json(workspace / "reports" / "sasang_lens_observation_report_v1_latest.json")
    if obs.get("separation_contract_ok"):
        sh = obs.get("shadow_price_hit") if isinstance(obs.get("shadow_price_hit"), dict) else {}
        lines.append(
            f"  shadow hit(counterfactual)={sh.get('price_directional_hit_rate','—')} n={sh.get('n_evaluated','—')}"
        )
    lines.append(f"\nSSOT: {path.name}")
    return "\n".join(lines)[:TELEGRAM_MAX]


def _maturity_telegram_block(workspace: Path) -> str:
    path = workspace / "reports" / "lens_maturity_self_score_v1_latest.json"
    if not path.is_file():
        try:
            from build_lens_maturity_self_score_v1 import write_lens_maturity_self_score  # noqa: WPS433

            write_lens_maturity_self_score(workspace)
        except Exception:
            return ""
    doc = _read_json(path)
    block = doc.get("telegram_synthesis_block_ko")
    return str(block).strip() if block else ""


def _predictability_one_liner(workspace: Path) -> str:
    path = workspace / "reports" / "btrack_predictability_harness_v1_latest.json"
    doc = _read_json(path)
    metrics = doc.get("metrics") if isinstance(doc.get("metrics"), dict) else {}
    if not doc or not (doc.get("harness_pass") or doc.get("harness_ok")):
        return ""
    brier = (
        doc.get("mean_brier")
        or metrics.get("mean_brier_score")
        or doc.get("mean_brier_score")
        or doc.get("brier_mean")
    )
    n = doc.get("resolved_rows") or metrics.get("n_evaluated") or doc.get("n_resolved")
    if brier is None:
        return ""
    return f"  B-track predictability: mean_brier={brier} resolved={n} (general_prophecy · [HYPO])"


def _conflict_one_liner(workspace: Path) -> str:
    path = workspace / "reports" / "lens_conflict_narrative_v1_latest.json"
    doc = _read_json(path)
    line = doc.get("telegram_one_liner_ko") or doc.get("narrative_ko")
    return f"  {line}" if line else ""


def build_synthesis_report(workspace: Path) -> str:
    overnight = _read_json(workspace / "docs/final/artifacts/global_market_overnight_signals_v1_latest.json")
    hypo = _read_json(workspace / "docs/final/artifacts/btrack_hypothesis_prophecy_latest.json")
    go = _read_json(workspace / "docs/final/artifacts/trading_go_no_go_latest.json")
    my = _read_json(workspace / "docs/final/artifacts/myeongni_independent_lens_latest.json")
    lo = _read_json(workspace / "docs/final/artifacts/logos_independent_lens_latest.json")
    sa = _read_json(workspace / "docs/final/artifacts/sasang_independent_lens_latest.json")
    gate = _read_json(workspace / "docs/final/artifacts/independent_lens_shadow_gate_latest.json")
    now = datetime.now(KST).strftime("%Y-%m-%d %H:%M KST")
    pred = hypo.get("prediction") if isinstance(hypo.get("prediction"), dict) else {}
    lines = [
        f"📊 MKM 종합 보고서 · {now}",
        "Field → Lens(3) → Conflict → Final · [HYPO] · 주문 없음",
        "",
        "━━ Field(실물+overnight) ━━",
        f"  overnight={overnight.get('composite_tilt','—')}",
        f"  B-track 1d={pred.get('instrument','—')} {pred.get('direction','—')} conf={pred.get('confidence','—')}",
        "",
        "━━ Lens 3축 ━━",
        f"  명리 {_ko_dir((my.get('scores') or {}).get('direction_score'))} (score={(my.get('scores') or {}).get('direction_score','—')})",
        f"  성경 {_ko_dir((lo.get('scores') or {}).get('direction_score'))} [NON_GATING] (score={(lo.get('scores') or {}).get('direction_score','—')})",
        f"  사상 heat={(sa.get('sasang_stream_outputs') or {}).get('machine_readables',{}).get('heat_proxy','—') if isinstance(sa.get('sasang_stream_outputs'),dict) else '—'} "
        f"dir={(sa.get('scores') or {}).get('direction_score','—')}",
        "",
        "━━ Conflict ━━",
    ]
    conflict = _conflict_one_liner(workspace)
    if conflict:
        lines.append(conflict)
    else:
        lines.extend(
            [
                "  Logos bear 보조 vs 사상 heat↑ vs 명리 횡보 — 합의 약함(관측만)",
                f"  fusion shadow minority={gate.get('latest_conflict_snapshot',{}).get('minority_lens_ids',[]) if isinstance(gate.get('latest_conflict_snapshot'),dict) else []}",
            ]
        )
    pred = _predictability_one_liner(workspace)
    if pred:
        lines.extend(["", "━━ Predictability (B-track) ━━", pred])
    lines.extend(
        [
            "",
            "━━ Final Action ━━",
            "  **WATCH** — sizing·방향·추가진입 단정 금지",
            f"  운영 go_no_go={go.get('go_no_go','—')} risk={go.get('risk_mode','—')} (기계추가진입 정당화 약함)",
            "",
            "격벽: 3렌즈→실매매 자동합선 없음 · 1차 Field+운영게이트가 주",
        ]
    )
    mat = _maturity_telegram_block(workspace)
    if mat:
        lines.extend(["", mat])
    lines.append(f"\nSSOT: lens_maturity_self_score_v1_latest.json")
    return "\n".join(lines)[:TELEGRAM_MAX]


def build_four_lens_reports(workspace: Path | None = None) -> Dict[str, str]:
    ws = (workspace or ROOT).resolve()
    return {
        "myeongni": build_myeongni_report(ws),
        "logos": build_logos_report(ws),
        "sasang": build_sasang_report(ws),
        "synthesis": build_synthesis_report(ws),
    }


def main() -> int:
    import argparse

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--workspace-root", type=Path, default=ROOT)
    ap.add_argument("--out-dir", type=Path, default=ROOT / "reports" / "telegram_four_lens_preview")
    args = ap.parse_args()
    reports = build_four_lens_reports(args.workspace_root.resolve())
    args.out_dir.mkdir(parents=True, exist_ok=True)
    for key, text in reports.items():
        p = args.out_dir / f"{key}_latest.txt"
        p.write_text(text + "\n", encoding="utf-8")
        print(f"=== {key} ({len(text)} chars) ===")
        print(text)
        print()
    print(f"WROTE: {args.out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
