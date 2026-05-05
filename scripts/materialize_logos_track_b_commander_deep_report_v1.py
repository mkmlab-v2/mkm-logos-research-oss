#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""logos_track_b_commander_deep_report_latest.json → 지휘관용 Markdown (결정론, LLM 없음)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

DEFAULT_IN = ROOT / "docs" / "final" / "artifacts" / "logos_track_b_commander_deep_report_latest.json"
DEFAULT_OUT = ROOT / "reports" / "logos_track_b_commander_deep_report_latest.md"


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return obj if isinstance(obj, dict) else None


def build_markdown(doc: dict[str, Any], *, input_path: str) -> str:
    lines: list[str] = []
    lines.append("# Logos Track B — 지휘관 심층 리포트 (자동 골격)")
    lines.append("")
    lines.append(
        "**AUTO:** `scripts/materialize_logos_track_b_commander_deep_report_v1.py` — "
        "입력 JSON만 렌더링; LLM 없음; 최종 판단은 지휘관."
    )
    lines.append("")
    gate = doc.get("human_commander_gate_v1") if isinstance(doc.get("human_commander_gate_v1"), dict) else {}
    if gate.get("banner_ko"):
        lines.append(f"> **{gate['banner_ko']}**")
        lines.append("")
    labels = doc.get("labels")
    if isinstance(labels, list) and labels:
        lines.append(f"- **labels:** `{', '.join(str(x) for x in labels)}`")
        lines.append("")
    env = doc.get("envelope") if isinstance(doc.get("envelope"), dict) else {}
    if env.get("disclaimer_ko"):
        lines.append("## 면책·경계")
        lines.append("")
        lines.append(str(env["disclaimer_ko"]))
        lines.append("")
    lines.append("## 메타")
    lines.append("")
    lines.append(f"- source JSON: `{input_path}`")
    lines.append(f"- schema: `{doc.get('schema')}` version `{doc.get('version')}`")
    lines.append(f"- ts_utc: `{doc.get('ts_utc')}`")
    lines.append("")
    if doc.get("machine_role_ko"):
        lines.append("## 기계 역할")
        lines.append("")
        lines.append(str(doc["machine_role_ko"]))
        lines.append("")
    axes = doc.get("report_axes_v1")
    if isinstance(axes, dict):
        lines.append("## 5축 스텁 (결정론 템플릿)")
        lines.append("")
        for key in sorted(axes.keys()):
            ax = axes[key]
            if not isinstance(ax, dict):
                continue
            title = ax.get("title_ko") or key
            lines.append(f"### {title}")
            lines.append("")
            stub = ax.get("deterministic_stub_ko")
            if isinstance(stub, str) and stub.strip():
                lines.append(stub.strip())
                lines.append("")
            ev = ax.get("evidence_verse_ids")
            if isinstance(ev, list) and ev:
                lines.append(f"*verse_id 앵커:* {', '.join(str(x) for x in ev)}")
                lines.append("")
    lines.append("---")
    lines.append("*끝 — 장문 해석·외부 검색은 Track B 후속(지휘관 승인 하).*")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input", type=Path, default=DEFAULT_IN)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    doc = _read_json(args.input)
    if not doc or doc.get("schema") != "logos_track_b_commander_deep_report_v1":
        print(f"missing or invalid report json: {args.input}")
        return 2

    md = build_markdown(doc, input_path=str(args.input.resolve()))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(md, encoding="utf-8")
    print(f"WROTE: {args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
