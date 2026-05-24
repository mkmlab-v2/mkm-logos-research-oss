#!/usr/bin/env python3
"""Phase 2 — Multi-Lens Matrix View (Saving the News, B-track [HYPO])."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
OUT_JSON = ART / "saving_the_news_phase2_matrix_view_v1_latest.json"
OUT_MD = ART / "saving_the_news_phase2_matrix_view_v1_latest.md"
PRE_NEWS = ART / "pre_news_shadow_input_latest.json"

OFFICIAL_LENSES: list[tuple[str, str, bool]] = [
    ("sasang", "사상", False),
    ("myeongni", "명리", False),
    ("logos", "성경(Logos)", True),
]
STREAM_ROWS: list[tuple[str, str]] = [
    ("news", "뉴스 스트림 (관측)"),
    ("macro", "매크로 스트림 (관측)"),
]
EXTERNAL_CHANNEL_NOTE = (
    "대외 비유 채널(팩트/행정/비판)은 공식 렌즈명이 아님 — 아래 표는 "
    "news/macro 스트림 + 사상/명리/성경 격벽 스냅샷."
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _display_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(path)


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _load_lens(lens_id: str) -> dict[str, Any] | None:
    return _read_json(ART / f"{lens_id}_independent_lens_latest.json")


def _direction_label(score: float | None, *, threshold: float = 0.15) -> str:
    if score is None:
        return "neutral"
    if score > threshold:
        return "bullish_lean"
    if score < -threshold:
        return "bearish_lean"
    return "neutral"


def _headline_anchor() -> dict[str, Any]:
    doc = _read_json(PRE_NEWS) or {}
    rows = doc.get("rows") if isinstance(doc.get("rows"), list) else []
    if not rows:
        return {"headline": "", "timestamp_utc": None, "source": "missing"}
    row = rows[0] if isinstance(rows[0], dict) else {}
    return {
        "headline": str(row.get("headline", "")),
        "timestamp_utc": row.get("timestamp_utc"),
        "source": str(row.get("source", "")),
        "input_path": _display_path(PRE_NEWS),
    }


def _lens_row(
    lens_id: str,
    label_ko: str,
    doc: dict[str, Any] | None,
    *,
    non_gating: bool,
) -> dict[str, Any]:
    scores = (doc or {}).get("scores") or {}
    direction = scores.get("direction_score")
    confidence = scores.get("confidence")
    digest = ""
    if lens_id == "news":
        digest = str(((doc or {}).get("news_stream_outputs") or {}).get("digest", ""))
    elif lens_id == "macro":
        outs = (doc or {}).get("macro_stream_outputs") or {}
        digest = f"snippets={outs.get('snippet_count', 0)}"
    elif lens_id == "logos":
        digest = str((doc or {}).get("narrative_snippet_guarded", ""))[:120]
    elif lens_id == "sasang":
        digest = str(((doc or {}).get("sasang_stream_outputs") or {}).get("regime_hypothesis", ""))
    elif lens_id == "myeongni":
        digest = str(((doc or {}).get("myeongri_stream_outputs") or {}).get("rationale", ""))[:120]

    return {
        "lens_id": lens_id,
        "label_ko": label_ko,
        "non_gating": non_gating,
        "tags": ["[NON_GATING]"] if non_gating else ["[HYPO]"],
        "direction_score": direction,
        "confidence": confidence,
        "direction_label": _direction_label(direction if isinstance(direction, (int, float)) else None),
        "digest": digest,
        "artifact_path": _display_path(ART / f"{lens_id}_independent_lens_latest.json"),
        "present": doc is not None,
    }


def _external_channel_metaphor(matrix_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Pedagogical mapping only — not official lens names."""
    by_id = {r["lens_id"]: r for r in matrix_rows}
    news = by_id.get("news") or {}
    macro = by_id.get("macro") or {}
    sasang = by_id.get("sasang") or {}
    return [
        {
            "channel_id": "fact_channel_metaphor",
            "label_ko": "팩트 채널 (대외 비유)",
            "maps_from": "news",
            "direction_label": news.get("direction_label", "neutral"),
            "note": "Not an official MKM lens name.",
        },
        {
            "channel_id": "admin_channel_metaphor",
            "label_ko": "행정 채널 (대외 비유)",
            "maps_from": "macro",
            "direction_label": macro.get("direction_label", "neutral"),
            "note": "Not an official MKM lens name.",
        },
        {
            "channel_id": "critique_channel_metaphor",
            "label_ko": "비판/체질 채널 (대외 비유)",
            "maps_from": "sasang",
            "direction_label": sasang.get("direction_label", "neutral"),
            "note": "Not an official MKM lens name.",
        },
    ]


def resolve_conflict(matrix_rows: list[dict[str, Any]]) -> dict[str, Any]:
    gating_rows = [r for r in matrix_rows if not r.get("non_gating") and r.get("present")]
    active = [r for r in gating_rows if r.get("direction_label") != "neutral"]
    signs = {r["direction_label"] for r in active}
    conflict = len(signs) > 1
    dominant = "neutral"
    if not conflict and len(signs) == 1:
        dominant = next(iter(signs))
    elif not conflict and not signs:
        dominant = "neutral"
    return {
        "conflict": conflict,
        "gating_lens_count": len(gating_rows),
        "directional_gating_count": len(active),
        "distinct_direction_labels": sorted(signs),
        "dominant_direction_label": dominant,
        "logos_excluded_from_gating": True,
    }


def final_action(conflict: dict[str, Any]) -> dict[str, Any]:
    if conflict.get("conflict"):
        action = "WATCH"
        reason = "Gating lenses disagree on direction lean."
    elif conflict.get("directional_gating_count", 0) == 0:
        action = "HOLD"
        reason = "No directional lean above threshold on gating lenses."
    elif conflict.get("dominant_direction_label") == "bearish_lean":
        action = "REDUCE"
        reason = "Aligned bearish lean on gating lenses (exposure posture, not sell order)."
    else:
        action = "WATCH"
        reason = "Partial or bullish lean — observation only; no trade instruction."
    return {
        "action": action,
        "reason": reason,
        "research_only": True,
        "not_investment_advice": True,
    }


def build_matrix(*, field_regime: str = "observation_btrack") -> dict[str, Any]:
    matrix_rows: list[dict[str, Any]] = []
    for lens_id, label_ko, non_gating in OFFICIAL_LENSES:
        matrix_rows.append(_lens_row(lens_id, label_ko, _load_lens(lens_id), non_gating=non_gating))
    for lens_id, label_ko in STREAM_ROWS:
        matrix_rows.append(_lens_row(lens_id, label_ko, _load_lens(lens_id), non_gating=False))

    conflict = resolve_conflict(matrix_rows)
    action = final_action(conflict)
    anchor = _headline_anchor()

    return {
        "schema": "saving_the_news_phase2_matrix_view_v1",
        "phase": "Phase 2 — Multi-Lens Matrix View",
        "lane": "research_only",
        "hypothesis_tier": "B",
        "ready_for_external_send": False,
        "generated_at_utc": _utc_now(),
        "field": {
            "regime_id": field_regime,
            "note": "1차 실물 regime_map 주도·본 스냅샷은 B-track 관측 [HYPO]",
        },
        "headline_anchor": anchor,
        "matrix_rows": matrix_rows,
        "external_channel_metaphor": _external_channel_metaphor(matrix_rows),
        "external_channel_disclaimer": EXTERNAL_CHANNEL_NOTE,
        "conflict_resolver": conflict,
        "final_action": action,
        "output_order": ["Field", "Lens(official+streams)", "Conflict", "Final Action"],
        "refs": {
            "phase1_status": "docs/final/artifacts/saving_the_news_phase1_poc_status_v1_latest.json",
            "blueprint": "docs/research/saving_the_news_blueprint_v1.md",
            "track_c_onepager": "docs/final/artifacts/track_c_saving_the_news_offer_onepager_v1_latest.md",
            "showroom_topology": "docs/final/artifacts/showroom_topology_radar_snapshot_v1_latest.json",
        },
    }


def _render_md(doc: dict[str, Any]) -> str:
    lines = [
        "# Saving the News — Phase 2 Matrix View (DRAFT)",
        "",
        f"- **generated_at_utc:** `{doc['generated_at_utc']}`",
        f"- **lane:** `{doc['lane']}` · **ready_for_external_send:** `{doc['ready_for_external_send']}`",
        "",
        "## Headline anchor",
        "",
        f"> {doc.get('headline_anchor', {}).get('headline', '(none)')}",
        "",
        EXTERNAL_CHANNEL_NOTE,
        "",
        "## Matrix",
        "",
        "| 렌즈 | 방향 lean | confidence | digest |",
        "|------|-----------|------------|--------|",
    ]
    for row in doc.get("matrix_rows") or []:
        tags = ",".join(row.get("tags") or [])
        lines.append(
            f"| {row.get('label_ko')} `{row.get('lens_id')}` {tags} "
            f"| {row.get('direction_label')} | {row.get('confidence')} "
            f"| {(row.get('digest') or '')[:80]} |"
        )
    fa = doc.get("final_action") or {}
    cr = doc.get("conflict_resolver") or {}
    lines.extend(
        [
            "",
            "## Conflict",
            "",
            f"- conflict: `{cr.get('conflict')}`",
            f"- distinct: `{cr.get('distinct_direction_labels')}`",
            "",
            "## Final Action",
            "",
            f"**{fa.get('action')}** — {fa.get('reason')}",
            "",
            "*Not investment advice. Not a buy/sell instruction.*",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description="Build Phase 2 matrix view")
    ap.add_argument("--field-regime", default="observation_btrack")
    ap.add_argument("--no-md", action="store_true")
    args = ap.parse_args()

    doc = build_matrix(field_regime=args.field_regime)
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if not args.no_md:
        OUT_MD.write_text(_render_md(doc), encoding="utf-8")

    print(
        f"Wrote {_display_path(OUT_JSON)} "
        f"action={doc['final_action']['action']} conflict={doc['conflict_resolver']['conflict']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
