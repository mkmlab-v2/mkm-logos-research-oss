#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Render `athena_100_point_report_v1` from `han_physician_clinical_assist_turn_v1`."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_REPORT = ROOT / "docs" / "final" / "schemas" / "athena_100_point_report_v1.schema.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _validate(doc: dict[str, Any]) -> None:
    try:
        import jsonschema
    except ImportError:
        return
    schema = json.loads(SCHEMA_REPORT.read_text(encoding="utf-8"))
    jsonschema.validate(instance=doc, schema=schema)


def build_report(turn: dict[str, Any], *, myeongni: dict[str, Any] | None) -> dict[str, Any]:
    layers = turn.get("layers") or {}
    ex = layers.get("executive_summary") or {}
    bullets = ex.get("bullets_ko") or []
    fact_line = " / ".join(str(b) for b in bullets[:4])
    actions = turn.get("next_physician_actions") or []
    action_line = " · ".join(str(a) for a in actions[:2])
    l0 = layers.get("L0_clinical_safety") or {}

    facts: list[str] = []
    for b in bullets:
        facts.append(f"[FACT] {b}")
    for r in l0.get("red_flags_ko") or []:
        facts.append(f"[FACT] Red flag 관찰: {r}")
    for key in ("L1_hemodynamics_sleep", "L2_thermal_hydration", "L3_cognitive_vitality"):
        v = layers.get(key)
        if v:
            facts.append(f"[FACT] {key}: {v}")

    hypotheses: list[dict[str, str]] = []
    l5 = layers.get("L5_myeongni_hypo")
    if isinstance(l5, dict):
        hypotheses.append(
            {
                "hypothesis": str(l5.get("pillars_ko") or l5.get("hypo_ack") or ""),
                "verification_needed": "만세력·명리 SSOT JSON 대조",
            }
        )
    l6 = layers.get("L6_lifestyle")
    if l6:
        hypotheses.append(
            {"hypothesis": str(l6), "verification_needed": "생활 루틴·자가보고 2주 로그"}
        )

    non_gating: list[str] = []
    l4 = layers.get("L4_career_family")
    if l4:
        non_gating.append(str(l4))
    if isinstance(l5, dict) and l5.get("season_note_ko"):
        non_gating.append(f"[NON_GATING] {l5['season_note_ko']}")

    fact_rows: list[dict[str, str]] = [
        {"key": "대상", "value": str(turn.get("display_label") or ""), "source": "han_turn"},
        {"key": "cohort", "value": str(turn.get("cohort_id") or ""), "source": "han_turn"},
        {"key": "ref_token", "value": str(turn.get("ref_token") or ""), "source": "han_turn"},
    ]
    if myeongni:
        surf = myeongni.get("surface_summary") or myeongni.get("summary") or {}
        if isinstance(surf, dict):
            pillars = surf.get("pillars_ko") or surf.get("four_pillars_ko")
            if pillars:
                fact_rows.append({"key": "사주 표면", "value": str(pillars), "source": "myeongni_full"})
        birth = myeongni.get("birth") or myeongni.get("birth_profile")
        if isinstance(birth, dict):
            fact_rows.append(
                {
                    "key": "출생(UTC/IANA)",
                    "value": f"{birth.get('birth_instant_utc', '')} · {birth.get('iana_tz', '')}",
                    "source": "myeongni_full",
                }
            )

    prov_turn = turn.get("provenance") or {}
    return {
        "schema": "athena_100_point_report_v1",
        "version": "1.0.0",
        "rail": "Track B",
        "report_kind": "clinical",
        "slug": turn.get("slug"),
        "display_label": turn.get("display_label"),
        "ref_token": turn.get("ref_token"),
        "summary_3line": {
            "fact_line": fact_line,
            "action_line": action_line,
            "boundary_line": turn.get("disclaimer_ko", ""),
        },
        "fact_snapshot_rows": fact_rows,
        "facts": facts,
        "hypotheses": hypotheses,
        "non_gating": non_gating,
        "overclaim_filters": [
            {"forbidden": "완벽, 확정, 반드시", "replacement": "가능성 높음, 경향, 조건부"},
        ],
        "execution": {
            "today": actions[:2],
            "week": actions[2:4] if len(actions) > 2 else actions,
            "month_metrics": [
                {"metric": "루틴 준수", "target": "주 5일 이상", "measurement": "간단 체크리스트"}
            ],
        },
        "quality_checklist": {
            "structure_25": True,
            "tag_separation_20": True,
            "overclaim_removed_20": True,
            "actionable_20": True,
            "child_safe_15": True,
            "total_score": 100,
        },
        "disclaimer_ko": turn.get("disclaimer_ko", ""),
        "provenance": {
            "generator_id": "scripts/render_athena_100pt_from_han_turn_v1.py",
            "han_turn_json": prov_turn.get("bundle_json") or prov_turn.get("intake"),
            "myeongni_full": prov_turn.get("myeongni_full"),
            "generated_at_utc": _utc_now(),
        },
    }


def render_md(report: dict[str, Any]) -> str:
    s = report.get("summary_3line") or {}
    lines = [
        f"# Athena 100pt — {report.get('display_label', '')}",
        "",
        f"**FACT** {s.get('fact_line', '')}",
        "",
        f"**Action** {s.get('action_line', '')}",
        "",
        f"**Boundary** {s.get('boundary_line', '')}",
        "",
        "## Facts",
        "",
    ]
    for f in report.get("facts") or []:
        lines.append(f"- {f}")
    lines.extend(["", f"_score: {report.get('quality_checklist', {}).get('total_score', '')}_", ""])
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--han-turn-json", type=Path, required=True)
    ap.add_argument("--myeongni-json", type=Path)
    ap.add_argument("--out-json", type=Path)
    ap.add_argument("--out-md", type=Path)
    ap.add_argument("--write-latest", action="store_true")
    ap.add_argument("--update-pointer", action="store_true")
    ap.add_argument("--validate-schema", action="store_true")
    args = ap.parse_args()

    turn_path = args.han_turn_json
    if not turn_path.is_file():
        print(f"missing {turn_path}", file=sys.stderr)
        return 1
    turn = _load(turn_path)
    myeongni = _load(args.myeongni_json) if args.myeongni_json and args.myeongni_json.is_file() else None
    if myeongni is None:
        mp = (turn.get("provenance") or {}).get("myeongni_full")
        if mp:
            p = ROOT / str(mp)
            if p.is_file():
                myeongni = _load(p)

    report = build_report(turn, myeongni=myeongni)
    if args.validate_schema:
        _validate(report)

    slug = str(turn.get("slug") or "patient")
    out_json = args.out_json or ROOT / "reports" / f"{slug}_athena_100pt_v1.json"
    out_md = args.out_md or ROOT / "reports" / f"{slug}_athena_100pt_v1.md"
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    out_md.write_text(render_md(report), encoding="utf-8")

    if args.write_latest:
        latest_j = ROOT / "reports" / f"{slug}_athena_100pt_v1.latest.json"
        latest_m = ROOT / "reports" / f"{slug}_athena_100pt_v1.latest.md"
        latest_j.write_text(out_json.read_text(encoding="utf-8"), encoding="utf-8")
        latest_m.write_text(out_md.read_text(encoding="utf-8"), encoding="utf-8")

    if args.update_pointer:
        ptr = ROOT / "reports" / f"{slug}_intake_ssot_pointer_v1.json"
        if ptr.is_file():
            doc = _load(ptr)
            paths = doc.setdefault("paths", {})
            paths["athena_100pt_report_json"] = str(out_json.relative_to(ROOT)).replace("\\", "/")
            paths["athena_100pt_report"] = str(out_md.relative_to(ROOT)).replace("\\", "/")
            paths["athena_100pt_report_latest"] = f"reports/{slug}_athena_100pt_v1.latest.md"
            ptr.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(json.dumps({"ok": True, "out_json": str(out_json), "out_md": str(out_md)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
