#!/usr/bin/env python3
"""Render clinic lifestyle management print HTML from v2 JSON instance.

Patient-facing copy uses modern clinical language only (format_spec v2).
Myeongni / internal_reference is never included in print output.
"""
from __future__ import annotations

import argparse
import html
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SPEC = ROOT / "docs/final/artifacts/clinic_lifestyle_management_format_spec_v2.json"


def _esc(s: str) -> str:
    return html.escape(s, quote=True)


def _ul(items: list[str]) -> str:
    if not items:
        return "<p class=\"muted\">—</p>"
    return "<ul>\n" + "\n".join(f"  <li>{_esc(x)}</li>" for x in items) + "\n</ul>"


def _load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def _section_num(n: int, title: str) -> str:
    return f"<h2>{n}. {_esc(title)}</h2>"


def render_html(data: dict[str, Any], spec: dict[str, Any]) -> str:
    schema = data.get("schema", "")
    if schema not in ("clinic_lifestyle_management_v2",):
        raise ValueError(
            f"Expected schema clinic_lifestyle_management_v2, got {schema!r}. "
            "Migrate instance or use v2 fixture."
        )

    enc = data.get("encounter") or {}
    doc = data.get("document") or {}
    ctx = data.get("clinical_context") or {}
    sec = data.get("sections_patient_facing") or {}
    footnote = (spec.get("language_policy") or {}).get("footnote_required_ko", "")

    name = _esc(str(enc.get("patient_display_name_ko") or ""))
    written = _esc(str(enc.get("written_at_local") or enc.get("written_at_utc") or ""))
    physician = _esc(str(enc.get("physician_label_ko") or "담당의"))
    phase = _esc(str(ctx.get("phase_label_patient_ko") or ctx.get("phase_code") or ""))

    title = _esc(str(doc.get("title_ko") or spec.get("print_title_ko") or "회복·생활관리 안내서"))
    subtitle = _esc(str(doc.get("protocol_version") or spec.get("print_subtitle_ko") or ""))

    gates = ctx.get("clinical_gates_ko") or []
    gate_html = _ul(gates) if gates else ""

    nutrition = sec.get("nutrition") or {}
    activity = sec.get("physical_activity") or {}
    sleep_env = sec.get("sleep_circulation_environment") or {}
    comfort = sec.get("comfort_routine_optional") or {}
    preg = sec.get("pregnancy_planning") or {}
    assessment = data.get("functional_assessment") or {}
    protocols = data.get("recovery_protocols") or []
    routine_rows = data.get("daily_routine_table") or []

    verdict_rows = ""
    for row in nutrition.get("protocol_verdict") or []:
        verdict_rows += (
            f"<tr><td>{_esc(str(row.get('name_ko', '')))}</td>"
            f"<td class=\"no\">{_esc(str(row.get('verdict_ko', '')))}</td>"
            f"<td>{_esc(str(row.get('reason_ko', '')))}</td></tr>\n"
        )

    preg_rows = ""
    for w in preg.get("windows") or []:
        preg_rows += (
            f"<tr><td>{_esc(str(w.get('label_ko', w.get('rank', ''))))}</td>"
            f"<td>{_esc(str(w.get('calendar_ko', '')))}</td>"
            f"<td>{_esc(str(w.get('precondition_ko', '')))}</td></tr>\n"
        )

    routine_html = ""
    for r in routine_rows:
        routine_html += (
            f"<tr><td>{_esc(str(r.get('time_slot_ko', '')))}</td>"
            f"<td>{_esc(str(r.get('action_ko', '')))}</td>"
            f"<td>{_esc(str(r.get('expected_effect_ko', '')))}</td></tr>\n"
        )

    checks = data.get("weekly_self_check_ko") or []
    checks_html = '<ul class="checks">\n' + "\n".join(
        f"  <li>{_esc(c)}</li>" for c in checks
    ) + "\n</ul>"

    metrics = doc.get("key_metrics_ko") or []
    metrics_html = _ul(list(metrics)) if metrics else ""

    n = 1
    sections: list[str] = []

    sections.append(
        _section_num(n, "의학적 우선 확인")
        + "<div class=\"gate\"><strong>산부인과·검사·증상</strong>이 아래 프로토콜보다 "
        "항상 우선합니다. 통증·출혈·어지럼·발열 시 즉시 담당 의료기관에 연락하세요.</div>"
        + gate_html
    )
    n += 1

    if assessment:
        sections.append(
            _section_num(n, str(assessment.get("headline_ko") or "종합 평가 및 회복 방향"))
            + (f"<p>{_esc(str(assessment.get('summary_ko', '')))}</p>" if assessment.get("summary_ko") else "")
            + "<h3>핵심 관리 지표</h3>"
            + _ul(list(assessment.get("target_indicators_ko") or []))
        )
        n += 1
    else:
        pattern = ctx.get("pattern_summary_patient_ko") or ""
        constitution = ctx.get("constitution_label_patient_ko") or ""
        sections.append(
            _section_num(n, "회복 요약")
            + f"<p><strong>현재 단계:</strong> {phase}</p>"
            + (f"<p><strong>임상 관찰:</strong> {_esc(constitution)}</p>" if constitution else "")
            + (f"<p>{_esc(pattern)}</p>" if pattern else "")
        )
        n += 1

    if protocols:
        proto_body = ""
        for i, p in enumerate(protocols, 1):
            proto_body += f"<h3>{i}. {_esc(str(p.get('headline_ko', '')))}</h3>"
            if p.get("summary_ko"):
                proto_body += f"<p>{_esc(str(p['summary_ko']))}</p>"
            for sub in p.get("subsections") or []:
                proto_body += f"<p><strong>{_esc(str(sub.get('title_ko', '')))}</strong></p>"
                proto_body += _ul(list(sub.get("items_ko") or []))
        sections.append(_section_num(n, "3대 핵심 회복 프로토콜") + proto_body)
        n += 1

    sections.append(
        _section_num(n, str(nutrition.get("headline_ko") or "영양 · 식사 패턴"))
        + (f"<p><strong>기본 패턴:</strong> {_esc(str(nutrition.get('pattern_ko', '')))}</p>" if nutrition.get("pattern_ko") else "")
        + '<div class="grid-2"><div><h3 class="ok">권장</h3>'
        + _ul(list(nutrition.get("recommended_ko") or []))
        + '</div><div><h3 class="no">제한</h3>'
        + _ul(list(nutrition.get("limit_ko") or []))
        + "</div></div>"
        + ("<table><tr><th>식이법</th><th>판정</th><th>근거</th></tr>" + verdict_rows + "</table>" if verdict_rows else "")
    )
    n += 1

    if not protocols and activity:
        sections.append(
            _section_num(n, str(activity.get("headline_ko") or "활동 · 운동"))
            + "<h3 class=\"ok\">권장</h3>"
            + _ul(list(activity.get("allowed_ko") or []))
            + "<h3 class=\"no\">피할 활동</h3>"
            + _ul(list(activity.get("avoid_ko") or []))
            + (f"<p><strong>기립성 어지럼:</strong> {_esc(str(activity.get('orthostatic_note_ko', '')))}</p>" if activity.get("orthostatic_note_ko") else "")
        )
        n += 1
    elif protocols and activity:
        sections.append(
            _section_num(n, str(activity.get("headline_ko") or "활동 · 운동"))
            + "<h3 class=\"ok\">권장</h3>"
            + _ul(list(activity.get("allowed_ko") or []))
            + "<h3 class=\"no\">피할 활동</h3>"
            + _ul(list(activity.get("avoid_ko") or []))
            + (f"<p><strong>기립성 어지럼:</strong> {_esc(str(activity.get('orthostatic_note_ko', '')))}</p>" if activity.get("orthostatic_note_ko") else "")
        )
        n += 1

    if comfort and (comfort.get("suggest_ko") or comfort.get("color_profile_ko") or comfort.get("note_ko")):
        body = _section_num(n, str(comfort.get("headline_ko") or "편안감 루틴 (선택)"))
        if comfort.get("note_ko"):
            body += f"<p class=\"muted\">{_esc(str(comfort['note_ko']))}</p>"
        cp = comfort.get("color_profile_ko") or {}
        if isinstance(cp, dict) and cp:
            if cp.get("summary_ko"):
                body += f"<p>{_esc(str(cp['summary_ko']))}</p>"
            if cp.get("recommended_ko"):
                body += "<h3 class=\"ok\">추천</h3>" + _ul(list(cp.get("recommended_ko") or []))
            if cp.get("limit_ko"):
                body += "<h3 class=\"no\">피하기</h3>" + _ul(list(cp.get("limit_ko") or []))
            if cp.get("environment_ko"):
                body += "<h3>환경</h3>" + _ul(list(cp.get("environment_ko") or []))
        elif comfort.get("suggest_ko"):
            body += f"<p><strong>권장:</strong> {_esc(str(comfort['suggest_ko']))}</p>"
        if comfort.get("limit_ko") and not isinstance(comfort.get("color_profile_ko"), dict):
            body += f"<p><strong>제한:</strong> {_esc(str(comfort['limit_ko']))}</p>"
        integ = comfort.get("integration_with_lifestyle_ko") or {}
        if isinstance(integ, dict):
            for label, key in (
                ("식이 연계", "nutrition_ko"),
                ("운동 연계", "exercise_ko"),
                ("일과 연계", "daily_routine_ko"),
            ):
                items = integ.get(key) or []
                if items:
                    body += f"<h3>{label}</h3>" + _ul(list(items))
        sections.append(body)
        n += 1

    if routine_html:
        sections.append(
            _section_num(n, "일과 기준 생활 행동 가이드")
            + "<table><tr><th>시간대</th><th>핵심 행동</th><th>기대 효과</th></tr>"
            + routine_html
            + "</table>"
        )
        n += 1

    habits = data.get("lifestyle_habits_stress") or {}
    if habits and habits.get("subsections"):
        body = _section_num(n, str(habits.get("headline_ko") or "라이프스타일 · 스트레스"))
        for sub in habits.get("subsections") or []:
            body += f"<p><strong>{_esc(str(sub.get('title_ko', '')))}</strong></p>"
            body += _ul(list(sub.get("items_ko") or []))
        sections.append(body)
        n += 1

    if sleep_env and not protocols:
        sections.append(
            _section_num(n, str(sleep_env.get("headline_ko") or "수면 · 순환 · 환경"))
            + _ul(list(sleep_env.get("items_ko") or []))
        )
        n += 1

    couple = data.get("couple_coordination_optional") or {}
    if couple and (
        couple.get("compatibility_summary_ko")
        or couple.get("contrast_table_ko")
        or couple.get("shared_routines_ko")
        or couple.get("relationship_maintenance_ko")
    ):
        partner = _esc(str(couple.get("partner_display_name_ko") or ""))
        body = _section_num(
            n,
            str(couple.get("headline_ko") or "부부 생활·관계 조율 (참고)"),
        )
        if couple.get("disclaimer_ko"):
            body += f"<p class=\"muted\">{_esc(str(couple['disclaimer_ko']))}</p>"
        if partner:
            body += f"<p><strong>배우자:</strong> {partner}</p>"
        if couple.get("compatibility_summary_ko"):
            body += f"<p>{_esc(str(couple['compatibility_summary_ko']))}</p>"
        contrast = couple.get("contrast_table_ko") or []
        if contrast:
            rows = ""
            for row in contrast:
                rows += (
                    f"<tr><td>{_esc(str(row.get('axis_ko', '')))}</td>"
                    f"<td>{_esc(str(row.get('patient_ko', '')))}</td>"
                    f"<td>{_esc(str(row.get('partner_ko', '')))}</td>"
                    f"<td>{_esc(str(row.get('coordination_ko', '')))}</td></tr>\n"
                )
            body += (
                "<h3>생활 패턴 대비 · 조율 포인트</h3>"
                "<table><tr><th>축</th><th>본인</th><th>배우자</th><th>함께 맞추기</th></tr>"
                + rows
                + "</table>"
            )
        if couple.get("shared_routines_ko"):
            body += "<h3 class=\"ok\">함께 하면 유리한 루틴</h3>"
            body += _ul(list(couple.get("shared_routines_ko") or []))
        if couple.get("relationship_maintenance_ko"):
            body += "<h3>부부 관계·스트레스 관리</h3>"
            body += _ul(list(couple.get("relationship_maintenance_ko") or []))
        sections.append(body)
        n += 1

    if preg and (
        preg.get("windows")
        or preg.get("medical_first_ko")
        or preg.get("medical_clearance_steps_ko")
    ):
        body = _section_num(n, str(preg.get("headline_ko") or "재임신 검토"))
        if preg.get("medical_first_ko"):
            body += f"<p>{_esc(str(preg['medical_first_ko']))}</p>"
        steps = preg.get("medical_clearance_steps_ko") or []
        if steps:
            steps_label = _esc(str(preg.get("clearance_steps_label_ko") or "Medical Clearance 체크리스트"))
            body += f"<h3>{steps_label}</h3>" + _ul(list(steps))
        if preg.get("hold_ko"):
            body += f"<p class=\"no\"><strong>현재 보류:</strong> {_esc(str(preg['hold_ko']))}</p>"
        if preg_rows:
            body += (
                "<h3>일정 검토 (참고)</h3>"
                "<table><tr><th>구분</th><th>달력</th><th>전제</th></tr>"
                + preg_rows
                + "</table>"
            )
        if preg.get("disclaimer_ko"):
            body += f"<p class=\"muted\">{_esc(str(preg['disclaimer_ko']))}</p>"
        sections.append(body)
        n += 1

    sections.append(_section_num(n, "이번 주 자가 점검") + checks_html)
    n += 1

    follow = data.get("follow_up_ko") or ""
    if follow:
        sections.append(_section_num(n, "재내원") + f"<p>{_esc(follow)}</p>")
        n += 1

    phys_msg = data.get("physician_message_ko") or ""
    if phys_msg:
        sections.append(
            _section_num(n, "담당 의료진 메시지")
            + f'<div class="one-liner">{_esc(phys_msg)}</div>'
        )

    msg = data.get("patient_message_ko") or ""
    if msg:
        sections.append(
            f'<div class="one-liner"><strong>한 줄 요약:</strong> {_esc(msg)}</div>'
        )

    body = "\n".join(sections)

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{title}</title>
  <style>
    :root {{
      --ink: #1a1a1a;
      --muted: #555;
      --line: #c8c8c8;
      --accent: #2c5282;
      --warn: #8b0000;
      --ok: #2d5016;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      font-family: "Malgun Gothic", "Apple SD Gothic Neo", sans-serif;
      font-size: 10.5pt;
      line-height: 1.5;
      color: var(--ink);
      margin: 0;
      padding: 10mm 12mm;
      max-width: 210mm;
    }}
    h1 {{ font-size: 16pt; margin: 0 0 4px; font-weight: 700; }}
    h2 {{
      font-size: 11pt;
      margin: 16px 0 8px;
      padding-bottom: 4px;
      border-bottom: 2px solid var(--accent);
      page-break-after: avoid;
    }}
    h3 {{ font-size: 10pt; margin: 8px 0 4px; }}
    h3.ok {{ color: var(--ok); }}
    h3.no {{ color: var(--warn); }}
    .sub {{ color: var(--muted); font-size: 9pt; margin-bottom: 12px; }}
    .gate {{
      border: 2px solid var(--accent);
      padding: 10px 12px;
      font-size: 9.5pt;
      margin-bottom: 12px;
      background: #f7fafc;
    }}
    .grid-2 {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 8px 16px;
      margin-bottom: 10px;
    }}
    .field {{ display: flex; align-items: baseline; gap: 8px; font-size: 9.5pt; margin-bottom: 4px; }}
    .field label {{ font-weight: 600; min-width: 4.5em; }}
    .field .val {{ flex: 1; border-bottom: 1px solid var(--ink); min-height: 1.3em; }}
    ul {{ margin: 4px 0 10px; padding-left: 1.25em; }}
    li {{ margin-bottom: 4px; }}
    table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 9pt;
      margin: 8px 0 12px;
    }}
    th, td {{ border: 1px solid var(--line); padding: 6px 8px; vertical-align: top; }}
    th {{ background: #edf2f7; font-weight: 600; }}
    td.no, .no {{ color: var(--warn); font-weight: 600; }}
    .muted {{ font-size: 8.5pt; color: var(--muted); }}
    .one-liner {{
      border-left: 4px solid var(--accent);
      padding: 10px 12px;
      margin: 14px 0;
      background: #f7fafc;
      font-size: 10pt;
    }}
    .checks {{ list-style: none; padding-left: 0; }}
    .checks li::before {{ content: "☐ "; }}
    .foot {{
      font-size: 8pt;
      color: var(--muted);
      margin-top: 16px;
      border-top: 1px solid var(--line);
      padding-top: 10px;
    }}
    .no-print {{ margin-bottom: 12px; }}
    @media print {{
      .no-print {{ display: none; }}
      body {{ padding: 8mm 10mm; }}
      h2 {{ page-break-after: avoid; }}
      table, .gate, .one-liner {{ page-break-inside: avoid; }}
    }}
  </style>
</head>
<body>
  <p class="no-print">
    <button type="button" onclick="window.print()">인쇄 / PDF 저장</button>
    · MKM clinic_lifestyle_management_v2
  </p>

  <h1>{title}</h1>
  <p class="sub">대상: {name} · {subtitle}</p>
  {f'<div class="gate"><strong>핵심 관리 지표</strong>{metrics_html}</div>' if metrics else ''}

  <div class="grid-2">
    <div class="field"><label>환자명</label><span class="val">{name or "&nbsp;"}</span></div>
    <div class="field"><label>작성일</label><span class="val">{written or "&nbsp;"}</span></div>
    <div class="field"><label>담당의</label><span class="val">{physician}</span></div>
    <div class="field"><label>회복 단계</label><span class="val">{phase or "&nbsp;"}</span></div>
  </div>

{body}

  <p class="foot">
    MKM · clinic_lifestyle_management_v2 · physician_gold · {_esc(footnote)}
  </p>
</body>
</html>
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Render lifestyle management print HTML (v2).")
    parser.add_argument("--input-json", type=Path, required=True, help="v2 instance JSON")
    parser.add_argument("--out-html", type=Path, required=True, help="Output HTML path")
    parser.add_argument(
        "--format-spec",
        type=Path,
        default=DEFAULT_SPEC,
        help="Format spec JSON (default: format_spec_v2)",
    )
    args = parser.parse_args()

    if not args.input_json.is_file():
        print(f"Missing input: {args.input_json}", file=sys.stderr)
        return 1

    data = _load_json(args.input_json)
    spec = _load_json(args.format_spec) if args.format_spec.is_file() else {}

    html_out = render_html(data, spec)
    args.out_html.parent.mkdir(parents=True, exist_ok=True)
    args.out_html.write_text(html_out, encoding="utf-8")
    print(str(args.out_html))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
