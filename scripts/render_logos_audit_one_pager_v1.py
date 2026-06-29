#!/usr/bin/env python3
"""Render B2B RAG integrity audit one-pager from Fact-Lock artifacts [HYPO]."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SMOKE = ROOT / "docs/final/artifacts/compression_open_bench_logos_audit_smoke_v1_latest.json"
SOURCE_KO = ROOT / "docs/final/artifacts/logos_neuro_symbolic_b2b_public_one_pager_ko_v1.md"
OUT_KO_DEFAULT = ROOT / "docs/final/artifacts/logos_rag_integrity_audit_one_pager_b2b_v1_latest.md"
OUT_EN_DEFAULT = ROOT / "docs/final/artifacts/logos_rag_integrity_audit_one_pager_b2b_en_v1_latest.md"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (json.JSONDecodeError, OSError):
        return {}


def _pct(v: Any, digits: int = 1) -> str:
    try:
        f = float(v)
        if f <= 1.0:
            return f"{f * 100:.{digits}f}%"
        return f"{f:.{digits}f}"
    except (TypeError, ValueError):
        return "n/a"


def render_ko(smoke: dict[str, Any], *, hide_theology: bool) -> str:
    m = smoke.get("metrics") or {}
    orphan = smoke.get("orphan_citation_audit") or {}
    lines = [
        "# RAG Integrity Audit — Raw Corpus to Reproducible Anchors",
        "",
        "**상태:** `[HYPO]` · `research_only` · **SEND_GATE: HOLD** · 법무 검토 전",
        "",
        "**정렬:** `TRACK_C_IP_BUSINESS_PLAN_2026-04-17.md` §3.1.8 · `PUBLIC_FACING_SECURITY_AND_IP_COPY_CHECKLIST_V1.md`",
        "",
        "---",
        "",
        "## 한 줄 가치",
        "",
        "장문 고전·계약·말뭉치 RAG에 대해 **인용 잠금·그래프 경로·exit code** 로 무결성을 **재현 가능하게 감사**한다.",
        "성경 해석 앱·목회 조언·신학 카피 **아님**.",
        "",
        "---",
        "",
        "## Fact-Lock 지표 (내부 PoC 스냅샷)",
        "",
        f"| 지표 | 값 |",
        f"|------|-----|",
        f"| citation_valid themes | **{m.get('citation_valid_themes')}/{m.get('theme_preset_count')}** |",
        f"| GraphRAG seed (organic) | `{m.get('graphrag_seed_organic')}` |",
        f"| thematic_hit@1 | `{_pct(m.get('thematic_hit_at_1'))}` |",
        f"| key-verse shadow v2 rows | `{m.get('key_verse_v2_rows')}` |",
        f"| canon book heatmap | `{m.get('canon_book_count')}` books |",
        f"| MACULA proxy edges | `{m.get('macula_edges_built')}` |",
        f"| orphan citations (LLM stub) | `{orphan.get('orphan_citation_count', 0)}` |",
        f"| commercial finish tier | `{m.get('finish_tier')}` |",
        "",
        "---",
        "",
        "## 무엇을 하지 않는가",
        "",
        "- 「성경 AI」·교리 조언·투자 수익 보장",
        "- MS 압축 헤드라인과 **단일 KPI 합산** (FAIL-COMP-004)",
        "- Track A 승격 · 실매매 · 자동 대외 송출",
        "",
        "---",
        "",
        "## 본선–부록 결속 (a-codeai open-bench)",
        "",
        "- **본선:** 압축 오픈벤치 (`a-codeai-compression-reproduce`)",
        "- **부록:** `logos-audit-smoke` — 위 표 지표만; theology merge 금지",
        "",
        "```powershell",
        "py scripts/sync_compression_bench_to_audit_smoke_v1.py --attach-smoke",
        "py scripts/build_logos_commercial_finish_closure_gate_v1.py",
        "```",
        "",
        "---",
        "",
        "## GTM",
        "",
        "- **§3.1.7** GitHub·a-codeai 본선",
        "- **§3.1.8** B2B 인바운드 부록·파일럿 설명만",
        "- jemaai.cloud: `[NON_GATING]` topology·trust 관측",
        "",
    ]
    if not hide_theology:
        lines += [
            "---",
            "",
            "## Neuro-Symbolic topology (참고)",
            "",
            "상세: `docs/final/artifacts/logos_neuro_symbolic_b2b_public_one_pager_ko_v1.md`",
            "",
        ]
    lines += [f"*생성 `{_utc()}` · Track B `[HYPO]`*", ""]
    return "\n".join(lines)


def render_en(smoke: dict[str, Any]) -> str:
    m = smoke.get("metrics") or {}
    orphan = smoke.get("orphan_citation_audit") or {}
    return "\n".join(
        [
            "# RAG Integrity Audit — Raw Corpus to Reproducible Anchors",
            "",
            "`[HYPO]` · `research_only` · **SEND_GATE: HOLD**",
            "",
            "## Value",
            "",
            "Reproducible audit of long-document RAG: citation lock, graph paths, exit codes.",
            "Not a Bible app, pastoral advice, or theology product.",
            "",
            "## Metrics",
            "",
            f"- citation_valid themes: **{m.get('citation_valid_themes')}/{m.get('theme_preset_count')}**",
            f"- GraphRAG seed organic: `{m.get('graphrag_seed_organic')}`",
            f"- thematic_hit@1: `{_pct(m.get('thematic_hit_at_1'))}`",
            f"- orphan citations (stub): `{orphan.get('orphan_citation_count', 0)}`",
            f"- finish tier: `{m.get('finish_tier')}`",
            "",
            "## Reproduce",
            "",
            "```bash",
            "py scripts/sync_compression_bench_to_audit_smoke_v1.py --attach-smoke",
            "py scripts/build_logos_commercial_finish_closure_gate_v1.py",
            "```",
            "",
            f"*Generated `{_utc()}`*",
            "",
        ]
    )


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--style", default="b2b_sales", choices=["b2b_sales"])
    ap.add_argument("--hide-theology", action="store_true", default=True)
    ap.add_argument("--out-ko", type=Path, default=OUT_KO_DEFAULT)
    ap.add_argument("--out-en", type=Path, default=OUT_EN_DEFAULT)
    ap.add_argument("--also-update-legacy", action="store_true", help="Write metrics block pointer to legacy neuro-symbolic one-pager footer")
    args = ap.parse_args()

    smoke = _load(SMOKE)
    if not smoke:
        raise SystemExit(f"missing smoke artifact: {SMOKE} — run sync_compression_bench_to_audit_smoke_v1.py first")

    ko = render_ko(smoke, hide_theology=args.hide_theology)
    en = render_en(smoke)
    args.out_ko.parent.mkdir(parents=True, exist_ok=True)
    args.out_ko.write_text(ko, encoding="utf-8")
    args.out_en.write_text(en, encoding="utf-8")

    if args.also_update_legacy and SOURCE_KO.is_file():
        legacy = SOURCE_KO.read_text(encoding="utf-8")
        marker = "## Fact-Lock 근거 (내부·재현)"
        if marker in legacy:
            footer = (
                f"\n\n---\n\n## Audit smoke pointer (auto)\n\n"
                f"Latest B2B sales one-pager: `{args.out_ko.relative_to(ROOT)}`\n"
                f"Smoke artifact: `{SMOKE.relative_to(ROOT)}`\n"
            )
            if "Audit smoke pointer" not in legacy:
                SOURCE_KO.write_text(legacy.rstrip() + footer, encoding="utf-8")

    print(
        json.dumps(
            {
                "ok": True,
                "out_ko": str(args.out_ko.relative_to(ROOT)),
                "out_en": str(args.out_en.relative_to(ROOT)),
                "citation_valid": (smoke.get("metrics") or {}).get("citation_valid_themes"),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
