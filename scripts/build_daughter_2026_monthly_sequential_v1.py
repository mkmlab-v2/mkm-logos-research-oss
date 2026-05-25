#!/usr/bin/env python3
"""Build 2026 daughter monthly guide as 12 x 4 sequential layers (no 3-lens cell merge).

Reads: v4-minimal, hyo synthesis, myeongni full report monthly_fortune, pair contracts.
Emits: daughter_2026_monthly_sequential_v1_latest.json (+ optional MD).
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

DEFAULT_V4 = ROOT / "docs/final/artifacts/daughter_2026_integrated_guide_v4_minimal_latest.json"
DEFAULT_HYO = ROOT / "docs/final/artifacts/daughter_2026_romance_wealth_hyo_v1_latest.json"
DEFAULT_MYEONGNI = ROOT / "reports/tmp_daughter_myeongni_full_v1.json"
DEFAULT_CONTRACTS = ROOT / "docs/final/artifacts/daughter_2026_lens_pair_contracts_v1_latest.json"
DEFAULT_OUT = ROOT / "docs/final/artifacts/daughter_2026_monthly_sequential_v1_latest.json"
DEFAULT_MD = ROOT / "reports/daughter_2026_monthly_sequential_ko_v1_latest.md"
DEFAULT_ANCHOR = ROOT / "docs/final/artifacts/family_anchor_lived_calibration_our_daughter_v1_latest.json"
SCHEMA_PATH = ROOT / "docs/final/schemas/daughter_2026_monthly_sequential_v1.schema.json"
MKMLIFE_PUBLIC = ROOT / "projects/mkm/mkm-life/public/data"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def _read(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise SystemExit(f"missing: {path}")
    doc = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(doc, dict):
        raise SystemExit(f"invalid json object: {path}")
    return doc


def _index_guardrails(v4: dict[str, Any]) -> dict[int, dict[str, Any]]:
    out: dict[int, dict[str, Any]] = {}
    for row in v4.get("peak_month_guardrail_index") or []:
        if isinstance(row, dict) and row.get("month"):
            out[int(row["month"])] = row
    return out


def _wealth_hyo_by_month(hyo: dict[str, Any]) -> dict[int, str]:
    out: dict[int, str] = {}
    for row in (hyo.get("wealth_axis") or {}).get("peak_months") or []:
        if isinstance(row, dict) and row.get("month"):
            out[int(row["month"])] = str(row.get("hyo_ko") or "")
    return out


def _romance_hyo_by_month(hyo: dict[str, Any]) -> dict[int, str]:
    out: dict[int, str] = {}
    for row in (hyo.get("romance_peer_axis") or {}).get("peak_months") or []:
        if isinstance(row, dict) and row.get("month"):
            out[int(row["month"])] = str(row.get("hyo_ko") or "")
    return out


def _monthly_rows(myeongni: dict[str, Any], year: int = 2026) -> dict[int, dict[str, Any]]:
    out: dict[int, dict[str, Any]] = {}
    mf = myeongni.get("monthly_fortune") or {}
    for row in mf.get("rows") or []:
        if not isinstance(row, dict):
            continue
        if int(row.get("year", 0)) != year:
            continue
        m = int(row.get("month", 0))
        if 1 <= m <= 12:
            out[m] = row
    return out


def _pick_sasang_trigger(guard: dict[str, Any] | None, month: int, contracts: dict[str, Any]) -> tuple[str, str]:
    triggers = contracts.get("pairs", {}).get("myeongni_to_sasang", {}).get("junction_triggers") or {}
    if guard:
        for field in ("sasang", "wealth", "romance_peer"):
            raw = guard.get(field)
            if raw:
                key = str(raw)
                if key in triggers:
                    return key, str(triggers[key])
    if month in (8, 9):
        return "quiet_mentor_study", str(triggers.get("quiet_mentor_study", triggers.get("default_routine", "")))
    return "default_routine", str(triggers.get("default_routine", ""))


def _pick_logos_trigger(guard: dict[str, Any] | None, month: int, contracts: dict[str, Any]) -> tuple[str, str]:
    triggers = contracts.get("pairs", {}).get("myeongni_to_logos", {}).get("junction_triggers") or {}
    if guard and guard.get("logos"):
        key = str(guard["logos"])
        if key in triggers:
            return key, str(triggers[key])
    if month in (8, 9):
        return "quiet_mentor_study", str(triggers.get("quiet_mentor_study", triggers.get("default_logos", "")))
    return "default_logos", str(triggers.get("default_logos", ""))


def _split_fact_inference(body_ko: str) -> tuple[str, str]:
    """Split layer body into FACT (engine/lived) vs inference (HYPO / parenting read)."""
    fact_parts: list[str] = []
    infer_parts: list[str] = []
    for line in body_ko.splitlines():
        s = line.strip()
        if not s:
            continue
        if s.startswith("[FACT]") or (s.startswith("- ") and "[HYPO" not in s):
            fact_parts.append(s)
        else:
            infer_parts.append(s)
    return "\n".join(fact_parts), "\n".join(infer_parts)


def _layer_with_lines(
    layer: dict[str, Any],
    *,
    sasang_lived_note: str = "",
) -> dict[str, Any]:
    body = str(layer.get("body_ko") or "")
    fact_line, inference_line = _split_fact_inference(body)
    if layer.get("layer_id") == "sasang" and sasang_lived_note:
        inference_line = (
            f"{inference_line}\n\n[HYPO · lived] {sasang_lived_note}".strip()
            if inference_line
            else f"[HYPO · lived] {sasang_lived_note}"
        )
    out = dict(layer)
    out["fact_line_ko"] = fact_line
    out["inference_line_ko"] = inference_line
    return out


def _sasang_lived_note_from_anchor(anchor_path: Path) -> str:
    if not anchor_path.is_file():
        return ""
    anchor = _read(anchor_path)
    for block in anchor.get("supplementary_axes") or []:
        if not isinstance(block, dict) or block.get("axis") != "sasang_lifestyle":
            continue
        resp = block.get("responses") or {}
        if isinstance(resp, dict):
            return str(resp.get("dance_next_day_qualifier_ko") or "").strip()
    return ""


def _core_body(v4: dict[str, Any], month: int) -> str:
    b1 = v4.get("block_1_core_v3_lived") or {}
    lines = list(b1.get("school_teacher") or []) + list(b1.get("study_engine") or [])
    if month == 5:
        lines.append("[FACT lived] 5월: 담임 neutral · 학교 피곤·바쁨 (fact-check 정합).")
    return "\n".join(f"- {x}" for x in lines if x)


def _myeongni_body(
    month: int,
    row: dict[str, Any],
    v4: dict[str, Any],
    wealth_hyo: dict[int, str],
    romance_hyo: dict[int, str],
    hyo: dict[str, Any],
) -> str:
    b2 = v4.get("block_2_myeongni_peaks_2026") or {}
    parts = [
        "[FACT] "
        f"{month}월 월운 {row.get('wolwoon_pillar')} · 십신 {row.get('wolwoon_stem_ten_god')} "
        f"(15일 스냅 보조값 — 날짜 단정 없음).",
    ]
    sewoon = b2.get("annual_sewoon_fact") or {}
    if month == 1:
        parts.append(f"[FACT] 2026 연운 {sewoon.get('pillar')} ({sewoon.get('stem_ten_god')}) — 멘토·학원 축.")
    if month in wealth_hyo:
        parts.append(f"[HYPO parenting] 재물·용돈: {wealth_hyo[month]}")
    elif month in romance_hyo:
        parts.append(f"[HYPO parenting] 또래·호감: {romance_hyo[month]}")
    elif month in (8, 9):
        parts.append(f"[HYPO] {(hyo.get('wealth_axis') or {}).get('quiet_months_note_ko', '')}")
        if month == 9:
            parts.append(f"[HYPO] {(hyo.get('romance_peer_axis') or {}).get('quiet_months_note_ko', '')}")
    elif month == 10:
        parts.append("[HYPO] 비견월 — 또래 리듬·루틴 유지; 피크월 아님.")
    elif month == 12:
        parts.append("[HYPO] 식신월 — 연말 교류·다정함; 성인 연애·연인 단정 금지.")
    return "\n".join(parts)


def build_monthly_sequential(
    v4: dict[str, Any],
    hyo: dict[str, Any],
    myeongni: dict[str, Any],
    contracts: dict[str, Any],
    *,
    contracts_ref: str,
    md_ref: str | None = None,
) -> dict[str, Any]:
    year = int(v4.get("calendar_year") or 2026)
    guard_idx = _index_guardrails(v4)
    wealth_hyo = _wealth_hyo_by_month(hyo)
    romance_hyo = _romance_hyo_by_month(hyo)
    monthly = _monthly_rows(myeongni, year=year)
    wealth_peaks = set(v4.get("block_2_myeongni_peaks_2026", {}).get("wealth_peak_months") or [])
    romance_peaks = set(v4.get("block_2_myeongni_peaks_2026", {}).get("romance_peer_peak_months") or [])
    sasang_lived_note = _sasang_lived_note_from_anchor(DEFAULT_ANCHOR)

    months_out: list[dict[str, Any]] = []
    for m in range(1, 13):
        row = monthly.get(m)
        if not row:
            raise SystemExit(f"missing monthly_fortune row for {year}-{m:02d}")
        guard = guard_idx.get(m)
        sasang_tid, sasang_body = _pick_sasang_trigger(guard, m, contracts)
        logos_tid, logos_body = _pick_logos_trigger(guard, m, contracts)

        layers = [
            {
                "layer_id": "core",
                "label_ko": "CORE [FACT lived + v3]",
                "body_ko": _core_body(v4, m),
                "tags": ["FACT", "lived"],
            },
            {
                "layer_id": "myeongni",
                "label_ko": "명리 [FACT engine + HYPO parenting]",
                "body_ko": _myeongni_body(m, row, v4, wealth_hyo, romance_hyo, hyo),
                "tags": ["FACT", "HYPO"],
            },
            {
                "layer_id": "sasang",
                "label_ko": "사상·생활 [HYPO — not clinical]",
                "body_ko": sasang_body,
                "tags": ["HYPO", "lifestyle"],
                "junction_trigger_id": sasang_tid,
            },
            {
                "layer_id": "logos",
                "label_ko": "Logos [NON_GATING]",
                "body_ko": logos_body,
                "tags": ["NON_GATING", "HYPO"],
                "junction_trigger_id": logos_tid,
            },
        ]
        months_out.append(
            {
                "month": m,
                "wolwoon_fact": {
                    "pillar": row.get("wolwoon_pillar"),
                    "stem_ten_god": row.get("wolwoon_stem_ten_god"),
                    "main_element": row.get("wolwoon_main_element"),
                    "note": row.get("wolwoon_note"),
                },
                "peak_flags": {
                    "wealth_peak": m in wealth_peaks,
                    "romance_peer_peak": m in romance_peaks,
                    "quiet_mentor_study": m in (8, 9),
                },
                "layers": [_layer_with_lines(ly, sasang_lived_note=sasang_lived_note) for ly in layers],
            }
        )

    doc: dict[str, Any] = {
        "schema": "daughter_2026_monthly_sequential_v1",
        "version": "1.1.0",
        "anchor_id": v4.get("anchor_id") or "family_anchor_our_daughter_v1",
        "calendar_year": year,
        "generated_at_utc": _now(),
        "hypothesis_tier": "B",
        "research_only": True,
        "auto_apply": "none",
        "fusion_mode": "sequential_blocks_not_monthly_parallel_merge",
        "rag_graph_runtime": False,
        "pair_contracts_ref": contracts_ref,
        "upstream_refs": {
            "v4_minimal": _rel(DEFAULT_V4),
            "hyo_synthesis": _rel(DEFAULT_HYO),
            "myeongni_full_report": _rel(DEFAULT_MYEONGNI),
        },
        "months": months_out,
    }
    if md_ref:
        doc["report_md_ref"] = md_ref
    return doc


def render_markdown(doc: dict[str, Any]) -> str:
    lines = [
        f"# 딸 {doc.get('calendar_year')} 월별 양육 가이드 — 순차 4층 [B-track]",
        "",
        "**읽는 순서 (매월):** CORE → 명리 → 사상 → Logos — **3렌즈 합선·GraphRAG 육아 융합 없음.**",
        "",
        f"*SSOT: `daughter_2026_monthly_sequential_v1_latest.json` · pair contracts `{doc.get('pair_contracts_ref')}`*",
        "",
    ]
    for block in doc.get("months") or []:
        m = block.get("month")
        lines.append(f"## {m}월")
        wf = block.get("wolwoon_fact") or {}
        lines.append(
            f"*월운 FACT: {wf.get('pillar')} · {wf.get('stem_ten_god')} · {wf.get('main_element')}*"
        )
        flags = block.get("peak_flags") or {}
        tag_bits = []
        if flags.get("wealth_peak"):
            tag_bits.append("재물 피크")
        if flags.get("romance_peer_peak"):
            tag_bits.append("또래 피크")
        if flags.get("quiet_mentor_study"):
            tag_bits.append("멘토·학습 조용")
        if tag_bits:
            lines.append(f"*플래그: {', '.join(tag_bits)}*")
        lines.append("")
        for layer in block.get("layers") or []:
            lines.append(f"### {layer.get('label_ko')}")
            if layer.get("fact_line_ko"):
                lines.append("**FACT**")
                lines.append(str(layer.get("fact_line_ko") or ""))
            if layer.get("inference_line_ko"):
                lines.append("**예상 [HYPO]**")
                lines.append(str(layer.get("inference_line_ko") or ""))
            if not layer.get("fact_line_ko") and not layer.get("inference_line_ko"):
                lines.append(str(layer.get("body_ko") or ""))
            lines.append("")
    lines.append("---")
    lines.append("[HYPO][research_only] Track A·실매매·임상·연인 단정 없음.")
    return "\n".join(lines)


def _validate(doc: dict[str, Any], strict: bool) -> list[str]:
    if not strict or not SCHEMA_PATH.is_file():
        return []
    try:
        import jsonschema

        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        jsonschema.validate(doc, schema)
        return []
    except ImportError:
        return []
    except Exception as exc:
        return [str(exc)]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--v4-json", type=Path, default=DEFAULT_V4)
    ap.add_argument("--hyo-json", type=Path, default=DEFAULT_HYO)
    ap.add_argument("--myeongni-json", type=Path, default=DEFAULT_MYEONGNI)
    ap.add_argument("--contracts-json", type=Path, default=DEFAULT_CONTRACTS)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--md-out", type=Path, default=DEFAULT_MD)
    ap.add_argument("--skip-md", action="store_true")
    ap.add_argument("--copy-mkmlife-public", action="store_true")
    ap.add_argument("--strict-schema", action="store_true")
    args = ap.parse_args()

    v4 = _read(args.v4_json if args.v4_json.is_absolute() else ROOT / args.v4_json)
    hyo = _read(args.hyo_json if args.hyo_json.is_absolute() else ROOT / args.hyo_json)
    myeongni = _read(args.myeongni_json if args.myeongni_json.is_absolute() else ROOT / args.myeongni_json)
    contracts = _read(args.contracts_json if args.contracts_json.is_absolute() else ROOT / args.contracts_json)

    out_path = args.out_json if args.out_json.is_absolute() else ROOT / args.out_json
    md_path = args.md_out if args.md_out.is_absolute() else ROOT / args.md_out
    contracts_ref = _rel(args.contracts_json if args.contracts_json.is_absolute() else ROOT / args.contracts_json)

    md_ref = None if args.skip_md else _rel(md_path)
    doc = build_monthly_sequential(
        v4, hyo, myeongni, contracts, contracts_ref=contracts_ref, md_ref=md_ref
    )

    errs = _validate(doc, args.strict_schema)
    if errs:
        raise SystemExit(f"schema validation failed: {errs}")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {_rel(out_path)}")

    if not args.skip_md:
        md_path.parent.mkdir(parents=True, exist_ok=True)
        md_path.write_text(render_markdown(doc), encoding="utf-8")
        print(f"Wrote {_rel(md_path)}")

    if not args.skip_md:
        import subprocess
        import sys

        companion = ROOT / "scripts/build_daughter_2026_monthly_companion_reports_v1.py"
        if companion.is_file():
            r = subprocess.run(
                [sys.executable, str(companion), "--json", str(out_path)],
                cwd=ROOT,
            )
            if r.returncode != 0:
                raise SystemExit(f"companion reports failed exit {r.returncode}")
        annual = ROOT / "scripts/build_daughter_2026_annual_report_for_daughter_v1.py"
        if annual.is_file():
            r2 = subprocess.run(
                [sys.executable, str(annual), "--json", str(out_path)],
                cwd=ROOT,
            )
            if r2.returncode != 0:
                raise SystemExit(f"annual daughter report failed exit {r2.returncode}")

    if args.copy_mkmlife_public:
        MKMLIFE_PUBLIC.mkdir(parents=True, exist_ok=True)
        dest = MKMLIFE_PUBLIC / "daughter_2026_monthly_sequential_v1.json"
        dest.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"Wrote {_rel(dest)}")
        annual_md = ROOT / "reports/daughter_2026_annual_report_for_daughter_ko_v1_latest.md"
        if annual_md.is_file():
            annual_dest = MKMLIFE_PUBLIC / "daughter_2026_annual_report_ko_v1.md"
            annual_dest.write_text(annual_md.read_text(encoding="utf-8"), encoding="utf-8")
            print(f"Wrote {_rel(annual_dest)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
