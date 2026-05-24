#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Emit Track C B2B Logos verse-4D showroom appendix MD (NON_GATING, research only)."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SLICE = ROOT / "docs/final/artifacts/logos_verse_4d_showroom_slice_v1_latest.json"
DEFAULT_CROSS_BRIDGE = ROOT / "docs/final/artifacts/logos_verse_myeongri_cross_bridge_v1_latest.json"
DEFAULT_CROSS_BRIDGE_MATRIX = (
    ROOT / "docs/final/artifacts/logos_verse_myeongri_cross_bridge_matrix_v1_latest.json"
)
DEFAULT_OUT = ROOT / "docs/final/artifacts/track_c_b2b_logos_verse_4d_appendix_v1_latest.md"
SLICE_BUILDER = "scripts/build_logos_verse_4d_showroom_slice_v1.py"
CROSS_BRIDGE_CMD = "scripts/build_logos_verse_myeongri_cross_bridge_v1.py"
MATRIX_CMD = "scripts/build_logos_verse_myeongri_cross_bridge_matrix_v1.py"

BOUNDARY_KO = (
    "본 부록은 B-track 연구 스냅샷이며 `[NON_GATING]`·`ready_for_external_send: false`입니다. "
    "실물 레짐·운영 게이트·Track A 주문·임상 판단과 자동 합선되지 않습니다."
)
BOUNDARY_EN = (
    "This appendix is a B-track research snapshot only (`[NON_GATING]`, "
    "`ready_for_external_send: false`). It does not gate trading, clinical decisions, "
    "or Track A execution."
)

DISCLAIMER_KO = (
    "4D·게마트리아·그래프 지표는 분포·구조 관측용 `[HYPO]` 레시피 산출이며, "
    "「우주 OS」·신학적 진리·시장 예측·무손실·실시간 무지연을 증명하지 않습니다. "
    "법무 Sign-off 전 대외 발송 금지."
)
DISCLAIMER_EN = (
    "4D, gematria, and graph metrics are `[HYPO]` distributional observations under fixed "
    "recipes; they are not proof of a \"cosmic OS\", theological truth, market forecasts, "
    "zero-loss, or real-time latency-free operation. Do not send externally before legal sign-off."
)


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _as_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, dict):
        ko = _as_text(value.get("ko") or value.get("line_ko"))
        en = _as_text(value.get("en") or value.get("line_en"))
        if ko and en:
            return f"{ko} / {en}"
        return ko or en
    return str(value).strip()


def _medoids_top3(slice_doc: dict[str, Any]) -> list[dict[str, Any]]:
    if isinstance(slice_doc.get("medoids_top3"), list):
        return list(slice_doc["medoids_top3"])[:3]
    findings = slice_doc.get("sample_findings")
    if isinstance(findings, dict) and isinstance(findings.get("top_medoids"), list):
        return list(findings["top_medoids"])[:3]
    global_medoids = slice_doc.get("global_medoids")
    if isinstance(global_medoids, list):
        return list(global_medoids)[:3]
    medoids = slice_doc.get("medoids")
    if isinstance(medoids, dict) and isinstance(medoids.get("global_top3"), list):
        return list(medoids["global_top3"])[:3]
    return []


def _phase4_summary(slice_doc: dict[str, Any]) -> dict[str, Any]:
    raw = slice_doc.get("phase4_delta_summary")
    if isinstance(raw, dict):
        return raw
    findings = slice_doc.get("sample_findings")
    if isinstance(findings, dict):
        p4 = findings.get("phase4_null_vs_canon")
        if isinstance(p4, dict):
            summary = p4.get("summary") if isinstance(p4.get("summary"), dict) else {}
            src = slice_doc.get("source_artifacts")
            source_artifact = (
                src.get("os_compare")
                if isinstance(src, dict)
                else "docs/final/artifacts/logos_verse_4d_os_compare_v1_latest.json"
            )
            return {
                "source_artifact": source_artifact,
                "deltas_vs_canon": p4.get("deltas_vs_canon") or {},
                "interpretation_note": summary.get("interpretation_note") or p4.get("sample_size_small_note"),
            }
    compare = slice_doc.get("phase4_os_compare")
    if isinstance(compare, dict):
        return {
            "source_artifact": compare.get("source_artifact") or compare.get("path"),
            "deltas_vs_canon": compare.get("deltas_vs_canon") or {},
            "interpretation_note": compare.get("interpretation_note"),
        }
    return {}


def _format_delta_rows(deltas: dict[str, Any]) -> str:
    if not deltas:
        return "_No phase-4 delta block in slice._"
    lines: list[str] = []
    for null_label, metrics in sorted(deltas.items()):
        if not isinstance(metrics, dict):
            lines.append(f"- **{null_label}:** `{metrics}`")
            continue
        parts = ", ".join(f"`{k}`={v}" for k, v in sorted(metrics.items()))
        lines.append(f"- **{null_label}:** {parts}")
    return "\n".join(lines)


def _format_medoid_rows(medoids: list[dict[str, Any]]) -> str:
    if not medoids:
        return "_No medoid rows in slice._"
    rows: list[str] = []
    for m in medoids:
        rank = m.get("rank", "?")
        verse_id = m.get("verse_id", "?")
        centrality = m.get("centrality", "?")
        rows.append(f"| {rank} | `{verse_id}` | {centrality} |")
    return "\n".join(rows)


def _format_matrix_table(matrix: dict[str, Any]) -> str:
    rows = matrix.get("rows") or []
    if not rows:
        return "_No matrix rows._"
    profiles = matrix.get("human_profiles") or []
    pids = [str(p.get("profile_id", "?")) for p in profiles if isinstance(p, dict)]
    if not pids and rows and isinstance(rows[0].get("geometry_by_profile"), dict):
        pids = list(rows[0]["geometry_by_profile"].keys())

    header = "| rank | verse_id | " + " | ".join(f"L2 `{p}`" for p in pids) + " |"
    sep = "|------|----------|" + "|".join("---" for _ in pids) + "|"
    lines = [header, sep]
    for r in rows:
        geo = r.get("geometry_by_profile") or {}
        if not geo and r.get("l2_os_human") is not None:
            geo = {"_legacy": {"l2_os_human": r.get("l2_os_human"), "cosine_os_human": r.get("cosine_os_human")}}
            pids = ["_legacy"]
        cells = []
        for pid in pids:
            g = geo.get(pid) or {}
            cells.append(str(g.get("l2_os_human", "—")))
        lines.append(f"| {r.get('rank', '?')} | `{r.get('verse_id', '?')}` | " + " | ".join(cells) + " |")
    summary = matrix.get("summary") or {}
    note = ""
    if summary.get("unique_verse_vector_4d_count") is not None:
        note = (
            f"\n\n_unique verse vector_4d in top-N: {summary.get('unique_verse_vector_4d_count')} "
            f"(of {summary.get('medoid_count', len(rows))} medoid rows)._"
        )
    return "\n".join(lines) + note


def _cross_bridge_section(cross: dict[str, Any] | None) -> str:
    if not cross:
        return (
            f"_Cross-Bridge report missing — run `py {CROSS_BRIDGE_CMD}` first._"
        )
    geom = cross.get("geometry") or {}
    verse = cross.get("verse_os") or {}
    human = cross.get("human_terminal") or {}
    return f"""## Cross-Bridge v0 (우주 OS ↔ 인간 단말기 · `[HYPO]`)

- **verse (gematria 4D):** `{verse.get('verse_id', '?')}` · recipe `{verse.get('mapping_recipe_id', '?')}`
- **human (Myeongri 4D):** `{human.get('profile_id', '?')}` · `{human.get('birth_instant_utc', '?')}` `{human.get('iana_tz', '?')}`
- **L2:** `{geom.get('l2_os_human', '?')}` · **cosine:** `{geom.get('cosine_os_human', '?')}`
- **note:** {cross.get('interpretation_note', '')}

_서로 다른 측정기(게마트리아 브리지 vs 명리 융합). 치유·매매·신학적 정답 증명 아님._
"""


def _matrix_section(matrix: dict[str, Any] | None) -> str:
    if not matrix:
        return f"_Matrix missing — run `py {MATRIX_CMD}` first._"
    profiles = matrix.get("human_profiles") or []
    pid_list = ", ".join(f"`{p.get('profile_id')}`" for p in profiles if isinstance(p, dict))
    return f"""## Cross-Bridge matrix (top medoids × human profiles)

_profiles: {pid_list or 'golden only'} · observational geometry only._

{_format_matrix_table(matrix)}
"""


def build_appendix_from_slice(
    *,
    slice_doc: dict[str, Any],
    slice_path: Path,
    generated_at: str,
    cross_bridge: dict[str, Any] | None = None,
    cross_bridge_matrix: dict[str, Any] | None = None,
) -> str:
    boundary = slice_doc.get("boundary") if isinstance(slice_doc.get("boundary"), dict) else {}
    boundary_ko = (
        _as_text(boundary.get("line_ko"))
        or _as_text(slice_doc.get("boundary_sentence_ko"))
        or _as_text(slice_doc.get("boundary_line_ko"))
        or BOUNDARY_KO
    )
    boundary_en = (
        _as_text(boundary.get("line_en"))
        or _as_text(slice_doc.get("boundary_sentence_en"))
        or _as_text(slice_doc.get("boundary_line_en"))
        or BOUNDARY_EN
    )

    factory_demo = slice_doc.get("factory_demo")
    factory_cmd = (
        factory_demo.get("one_line_reproduce_cmd")
        if isinstance(factory_demo, dict)
        else None
    )
    factory = (
        _as_text(slice_doc.get("factory_one_liner"))
        or _as_text(slice_doc.get("factory"))
        or (
            f"Reproduce: `{factory_cmd}` — verse 4D corpus, kNN graph, lexicon back-projection, null compare."
            if factory_cmd
            else (
                "Verse units projected to normalized 4D vectors; kNN graph medoids summarize hub density "
                "under fixed Track B recipes — observational only."
            )
        )
    )

    medoids = _medoids_top3(slice_doc)
    phase4 = _phase4_summary(slice_doc)
    deltas = phase4.get("deltas_vs_canon") if isinstance(phase4.get("deltas_vs_canon"), dict) else {}
    phase4_source = _as_text(phase4.get("source_artifact")) or "`docs/final/artifacts/logos_verse_4d_os_compare_v1_latest.json`"
    phase4_note = _as_text(phase4.get("interpretation_note") or phase4.get("summary"))

    track_wall = slice_doc.get("track_wall") if isinstance(slice_doc.get("track_wall"), dict) else {}
    disclaimer = slice_doc.get("disclaimer") if isinstance(slice_doc.get("disclaimer"), dict) else {}
    rfe = disclaimer.get("ready_for_external_send", track_wall.get("ready_for_external_send", False))

    slice_ts = _as_text(slice_doc.get("generated_at_utc") or slice_doc.get("ts_utc"))

    return f"""# [DRAFT] B2B — 부록: Logos verse 4D 쇼룸 슬라이스 (Track B)

- **generated_at_utc:** `{generated_at}`
- **schema:** `track_c_b2b_logos_verse_4d_appendix_v1`
- **status:** `DRAFT_AUTO` — `ready_for_external_send: {str(rfe).lower()}` (legal sign-off before external send)
- **slice_source:** `{slice_path.as_posix()}`{f" · slice_ts `{slice_ts}`" if slice_ts else ""}

**본문 SSOT:** `docs/final/artifacts/track_c_b2b_logos_lens_appendix_v1_latest.md` · `track_c_b2b_macro_alert_offer_onepager_latest.md`  
**역할:** 엔터프라이즈 매크로·리스크 본체 **대체 아님** · `[NON_GATING]` · 아티팩트 근거형 스냅샷만.

---

## Boundary (KO · EN)

- **KO:** {boundary_ko}
- **EN:** {boundary_en}

---

## Factory one-liner (research rail)

{factory}

---

## Global medoids (top 3 · from slice)

| rank | verse_id | centrality |
|------|----------|------------|
{_format_medoid_rows(medoids)}

---

{_cross_bridge_section(cross_bridge)}

---

{_matrix_section(cross_bridge_matrix)}

---

## Phase 4 — canon vs null delta summary

- **source:** {phase4_source}
{f"- **note:** {phase4_note}" if phase4_note else ""}

{deltas and _format_delta_rows(deltas) or "_No deltas_vs_canon in slice; run Phase 4 compare chain._"}

---

## Disclaimers (PUBLIC_FACING-aligned)

- **KO:** {DISCLAIMER_KO}
- **EN:** {DISCLAIMER_EN}
- **Track wall:** `hypothesis_tier=B` · `a_track_auto_promotion=false` · `live_trading_trigger=false`
- **금지 문구:** cosmic OS 완성·무조건 예측·실매매 트리거·종교적 정답 단정

---

## Regenerate

```powershell
py {SLICE_BUILDER}
py {CROSS_BRIDGE_CMD}
py {MATRIX_CMD}
py scripts/build_logos_b2b_verse_4d_appendix_v1.py
```
"""


def build_missing_slice_appendix(*, generated_at: str) -> str:
    return f"""# [DRAFT] B2B — 부록: Logos verse 4D 쇼룸 슬라이스 (Track B)

- **generated_at_utc:** `{generated_at}`
- **schema:** `track_c_b2b_logos_verse_4d_appendix_v1`
- **status:** `DRAFT_AUTO` — `ready_for_external_send: false`

**Slice missing:** run `py {SLICE_BUILDER}` first to emit `{DEFAULT_SLICE.as_posix()}`.

---

## Boundary (KO · EN)

- **KO:** {BOUNDARY_KO}
- **EN:** {BOUNDARY_EN}

---

## Disclaimers

- **KO:** {DISCLAIMER_KO}
- **EN:** {DISCLAIMER_EN}

---

## Regenerate

```powershell
py {SLICE_BUILDER}
py {CROSS_BRIDGE_CMD}
py {MATRIX_CMD}
py scripts/build_logos_b2b_verse_4d_appendix_v1.py
```
"""


def main() -> int:
    ap = argparse.ArgumentParser(description="Build Track C B2B Logos verse-4D appendix MD")
    ap.add_argument("--slice-json", type=Path, default=DEFAULT_SLICE)
    ap.add_argument("--cross-bridge-json", type=Path, default=DEFAULT_CROSS_BRIDGE)
    ap.add_argument("--cross-bridge-matrix-json", type=Path, default=DEFAULT_CROSS_BRIDGE_MATRIX)
    ap.add_argument("--out-md", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    generated_at = datetime.now(timezone.utc).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")
    slice_path = args.slice_json if args.slice_json.is_absolute() else ROOT / args.slice_json

    if slice_path.is_file():
        try:
            slice_doc = _load(slice_path)
        except (json.JSONDecodeError, OSError) as exc:
            print(f"slice read failed: {exc}", file=sys.stderr)
            return 1
        try:
            rel_slice = slice_path.relative_to(ROOT)
        except ValueError:
            rel_slice = slice_path
        cb_path = args.cross_bridge_json if args.cross_bridge_json.is_absolute() else ROOT / args.cross_bridge_json
        mx_path = (
            args.cross_bridge_matrix_json
            if args.cross_bridge_matrix_json.is_absolute()
            else ROOT / args.cross_bridge_matrix_json
        )
        cross_doc = _load(cb_path) if cb_path.is_file() else None
        matrix_doc = _load(mx_path) if mx_path.is_file() else None
        md = build_appendix_from_slice(
            slice_doc=slice_doc,
            slice_path=rel_slice,
            generated_at=generated_at,
            cross_bridge=cross_doc,
            cross_bridge_matrix=matrix_doc,
        )
    else:
        md = build_missing_slice_appendix(generated_at=generated_at)

    out_path = args.out_md if args.out_md.is_absolute() else ROOT / args.out_md
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(md, encoding="utf-8")
    print(f"Wrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
