#!/usr/bin/env python3
"""Render Logos Track B commander deep report JSON → Markdown (internal)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_IN = ROOT / "docs/final/artifacts/logos_track_b_commander_deep_report_latest.json"
DEFAULT_DISTILL = ROOT / "docs/final/artifacts/logos_deep_research_distill_latest.json"
DEFAULT_OUT = ROOT / "reports/logos_track_b_commander_deep_report_latest.md"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def render(
    report: dict,
    distill: dict | None,
    *,
    distill_path: str | None = None,
    reproduce_cmd: str = "py scripts/run_logos_track_b_deep_push_v1.py",
) -> str:
    env = report.get("envelope") or {}
    banners = ["[TRACK B / HYPO]", "[연구용: 최종 판단은 지휘관 대기]"]
    lines = [
        "# Logos Track B — 지휘관 심층 리포트",
        "",
        " · ".join(banners),
        "",
        f"> {env.get('disclaimer_ko', '')}",
        "",
        "## 메타",
        f"- 생성: `{report.get('ts_utc')}` · schema `{report.get('schema')}`",
        f"- **NON_GATING** · A-track 자동 트리거 **금지**",
        "",
    ]

    axes = (report.get("report_axes_v1") or {})
    for key in sorted(axes.keys()):
        ax = axes[key]
        if not isinstance(ax, dict):
            continue
        title = ax.get("title_ko") or key
        lines += [f"## {title}", "", str(ax.get("deterministic_stub_ko") or ""), ""]
        vids = ax.get("evidence_verse_ids") or ax.get("graph_path_sample_verse_ids")
        if vids:
            lines.append(f"- 앵커 verse_id: {', '.join(vids[:12])}")
            lines.append("")

    gp = report.get("graph_paths_sample") or []
    if gp:
        lines += ["## 그래프 경로 샘플 (증류 연동)", ""]
        for p in gp[:8]:
            if not isinstance(p, dict):
                continue
            vids = " → ".join(p.get("verse_ids") or [])
            lines.append(
                f"- `{p.get('path_id')}` **{p.get('edge_type')}** {vids} "
                f"(w={p.get('weight')})"
            )
        lines.append("")

    if distill:
        stub = distill.get("mkm_interpretation_stub_ko") or {}
        narr = distill.get("distill_narrative_stub_ko") or {}
        if narr.get("body_ko"):
            lines += [
                "## 증류 서술 (citation-lock)",
                "",
                str(narr.get("body_ko")),
                "",
                f"- llm_invoked: `{narr.get('llm_invoked')}` · citation_valid: `{narr.get('citation_valid')}`",
                "",
            ]
        lines += [
            "## MKM 세계관 프레임 [HYPO]",
            "",
            str(stub.get("frame_ko") or ""),
            "",
            f"- graph_paths: **{len(distill.get('graph_paths') or [])}**",
            f"- evidence_refs: **{len(distill.get('evidence_refs') or [])}**",
            f"- epistemic_uncertainty: `{distill.get('epistemic_uncertainty')}`",
            f"- review_gate: `{(distill.get('review_gate') or {}).get('status')}`",
            "",
            f"증류 SSOT: `{distill_path or 'docs/final/artifacts/logos_deep_research_distill_latest.json'}`",
            "",
        ]

    lines += [
        "---",
        f"재현: `{reproduce_cmd}`",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input", type=Path, default=DEFAULT_IN)
    ap.add_argument("--distill", type=Path, default=DEFAULT_DISTILL)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--reproduce-cmd", type=str, default="")
    args = ap.parse_args()

    def _resolve(p: Path) -> Path:
        return p if p.is_absolute() else (ROOT / p)

    in_path = _resolve(args.input)
    distill_path = _resolve(args.distill)
    out_path = _resolve(args.output)

    if not in_path.is_file():
        raise SystemExit(f"missing report: {in_path}")
    report = _load(in_path)
    distill = _load(distill_path) if distill_path.is_file() else None
    repro = args.reproduce_cmd.strip() or "py scripts/run_logos_track_b_deep_push_v1.py"
    distill_rel = (
        str(distill_path.relative_to(ROOT)).replace("\\", "/") if distill_path.is_file() else None
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        render(report, distill, distill_path=distill_rel, reproduce_cmd=repro),
        encoding="utf-8",
    )
    print(json.dumps({"ok": True, "out": str(out_path.relative_to(ROOT))}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
