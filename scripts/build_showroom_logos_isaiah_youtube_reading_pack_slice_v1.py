#!/usr/bin/env python3
"""Build Isaiah YouTube 16-chapter Logos reading pack slice [HYPO].

Reproduce:
  py scripts/build_showroom_logos_isaiah_youtube_reading_pack_slice_v1.py
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.showroom_public_export_guard_v1 import scan_forbidden  # noqa: E402

DEFAULT_BRIDGE = ROOT / "reports/isaiah_youtube_16chapter_mkm_bridge_map_v1_latest.json"
DEFAULT_SCHEMA = ROOT / "docs/final/schemas/showroom_logos_isaiah_youtube_reading_pack_slice_v1.schema.json"
DEFAULT_OUT = ROOT / "docs/final/artifacts/showroom_logos_isaiah_youtube_reading_pack_slice_v1_latest.json"
DEFAULT_MVP = (
    ROOT
    / "projects/bitcoin-trading/ops/windows-rehearsal/jemaai-cloud-mvp"
    / "showroom_logos_isaiah_youtube_reading_pack_slice_v1.json"
)

HIGHLIGHT_PRESET_SPECS: list[tuple[str, str, list[str]]] = [
    ("isaiah_youtube_spine_v1", "Spine 5앵커", ["spine", "5앵커", "전체"]),
    ("ch01", "ch01 · 66=66 압축", ["66", "압축"]),
    ("ch09", "ch09 · 위로하라 40장", ["40", "위로"]),
    ("ch11", "ch11 · 53장 고난의 종", ["53", "고난"]),
    ("ch14", "ch14 · 휘장·성취", ["휘장", "성취"]),
    ("ch15", "ch15 · 새 하늘·새 땅", ["65", "계시록"]),
]

INTERNAL_PATH_RE = re.compile(r"`?docs/[a-zA-Z0-9_./\\-]+`?", re.I)


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _stale() -> str:
    return (datetime.now(timezone.utc) + timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sanitize(text: str) -> str:
    text = INTERNAL_PATH_RE.sub("[internal-ssot]", text)
    text = re.sub(r"reports/[a-zA-Z0-9_./\\-]+\.json", "[internal-artifact]", text, flags=re.I)
    return text


def _pack_excerpt_spine(spine: list[str], overclaim: list[str]) -> str:
    lines = [
        "**Pack:** `studio_spine_five_anchors` · **[HYPO][NON_GATING]** · `send_gate: HOLD`",
        "",
        "MKM 권장 독해 spine — 유튜브 16챕터를 5앵커로 압축합니다.",
        "",
        "경로: " + " → ".join(spine),
        "",
        "· **Isa.6.8** — 소명(내가 여기 있나이다)",
        "· **Isa.40.1** — 심판 후 위로 전환",
        "· **Isa.53.5** — 고난·대속",
        "· **Isa.65.17** — 새 하늘·새 땅",
        "· **Rev.21.2** — 새 예루살렘 수렴",
    ]
    if overclaim:
        lines.append("")
        lines.append("과장 플래그(보류): " + ", ".join(overclaim))
    return _sanitize("\n".join(lines))


def _pack_excerpt_chapters(chapters: list[dict[str, Any]]) -> str:
    lines = [
        "**Pack:** `chapter_route_sixteen` · **[HYPO][NON_GATING]**",
        "",
        "유튜브 강해 16챕터를 MKM bridge 판정과 함께 순서대로 따라갑니다.",
        "",
    ]
    for ch in chapters[:8]:
        cid = ch.get("chapter_id", "")
        verdict = ch.get("mkm_verdict", "?")
        title = (ch.get("title_ko") or "")[:48]
        lines.append(f"· **{cid}** [{verdict}] {title}")
    if len(chapters) > 8:
        lines.append(f"· … 외 {len(chapters) - 8}챕터 (타임라인 참조)")
    return _sanitize("\n".join(lines))


def _pack_excerpt_canonical() -> str:
    return _sanitize(
        "**Pack:** `canonical_citations_only` · **literal_path**\n\n"
        "신약이 **직접 인용**하거나 정경이 병렬하는 구절만 열거합니다.\n"
        "66장=66권 1:1 압축 지도 주장은 **의도적으로 제외**합니다.\n\n"
        "· Isa.7.14 ↔ Matt.1.23 (임마누엘)\n"
        "· Isa.40.3 ↔ Matt.3.3 (광야 외침)\n"
        "· Isa.53.5 ↔ Acts.8.32 (고난의 종)\n"
        "· Luke.4.18 ↔ Isa.61 (회당 낭독)\n"
        "· Isa.65.17 ↔ Rev.21.2 (새 창조)"
    )


def _highlight_presets(chapters: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_id = {str(c.get("chapter_id")): c for c in chapters}
    out: list[dict[str, Any]] = []
    for preset_id, label, keywords in HIGHLIGHT_PRESET_SPECS:
        if preset_id == "isaiah_youtube_spine_v1":
            studio_id = "isaiah_youtube_spine_v1"
            stage_ids = [str(c.get("chapter_id")) for c in chapters]
            pack_ids = ["studio_spine_five_anchors", "chapter_route_sixteen"]
        else:
            studio_id = f"isaiah_yt_{preset_id}"
            stage_ids = [preset_id] if preset_id in by_id else []
            pack_ids = ["chapter_route_sixteen", "canonical_citations_only"]
        out.append(
            {
                "preset_id": studio_id,
                "label_ko": label,
                "keywords_ko": keywords,
                "pack_ids": pack_ids,
                "narrative_stage_ids": stage_ids,
            }
        )
    return out


def build_slice(bridge_doc: dict[str, Any]) -> dict[str, Any]:
    chapters = bridge_doc.get("chapters") or []
    spine = bridge_doc.get("summary", {}).get("recommended_studio_spine") or [
        "Isa.6.8",
        "Isa.40.1",
        "Isa.53.5",
        "Isa.65.17",
        "Rev.21.2",
    ]
    narrative_route: list[dict[str, Any]] = []
    for i, ch in enumerate(chapters, start=1):
        refs = list(ch.get("anchor_verse_ids") or [])[:6]
        narrative_route.append(
            {
                "stage_id": ch.get("chapter_id") or f"ch{i:02d}",
                "order": i,
                "label_ko": ch.get("title_ko") or "",
                "bottleneck_ko": ch.get("video_claim_ko") or "",
                "mkm_verdict": ch.get("mkm_verdict"),
                "verse_refs": refs,
            }
        )

    overclaim_unique = list(
        dict.fromkeys(flag for ch in chapters for flag in (ch.get("overclaim_flags") or []))
    )

    return {
        "schema_version": "showroom_logos_isaiah_youtube_reading_pack_slice_v1",
        "generated_at_utc": _now(),
        "stale_after_utc": _stale(),
        "research_only": True,
        "hypothesis_tier": "B",
        "send_gate": "HOLD",
        "why_question_assembled": False,
        "disclaimer": {
            "evidence_tier": "hypo_research_only",
            "gating_status": "NON_GATING",
            "no_trade_signals": True,
            "note_ko": (
                "이사야 유튜브 16챕터 MKM Logos reading pack입니다. "
                "66=66 압축·메시아 예언 독해는 연구 서사이며 Track A·실매매·예측 게이트가 아닙니다."
            ),
        },
        "query_id": "isaiah_youtube_16chapter",
        "query_ko": "이사야서 66장 — MKM Logos 16챕터 spine",
        "anchor_ref": spine[0] if spine else "Isa.6.8",
        "bridge_map_id": "isaiah_youtube_16chapter_mkm_bridge_v1",
        "export_gate": {
            "bridge_map_ok": bool(chapters),
            "topology_send_gate": "HOLD",
        },
        "reading_packs": [
            {
                "pack_id": "canonical_citations_only",
                "label_ko": "정경 인용만 (보수)",
                "summary_ko": "신약 직접 인용·정경 병렬만 — 66=66 1:1 압축 주장 제외.",
                "utterance_class": "literal_path",
                "card_excerpt_ko": _pack_excerpt_canonical(),
                "verse_refs": [
                    "Isa.7.14",
                    "Matt.1.23",
                    "Isa.40.3",
                    "Matt.3.3",
                    "Isa.53.5",
                    "Acts.8.32",
                    "Luke.4.18",
                    "Isa.65.17",
                    "Rev.21.2",
                ],
            },
            {
                "pack_id": "studio_spine_five_anchors",
                "label_ko": "스튜디오 spine 5앵커",
                "summary_ko": "6:8 소명 → 40:1 위로 → 53:5 대속 → 65:17 새 창조 → Rev.21.2 완성.",
                "utterance_class": "imagination_path",
                "card_excerpt_ko": _pack_excerpt_spine(spine, overclaim_unique),
                "verse_refs": spine,
            },
            {
                "pack_id": "chapter_route_sixteen",
                "label_ko": "유튜브 16챕터 경로",
                "summary_ko": "챕터별 MKM bridge·앵커·판정을 순서대로 따라감.",
                "utterance_class": "imagination_path",
                "card_excerpt_ko": _pack_excerpt_chapters(chapters),
                "chapter_ids": [c.get("chapter_id") for c in chapters],
            },
        ],
        "narrative_route_public": narrative_route,
        "highlight_presets": _highlight_presets(chapters),
        "overclaim_flags_union": overclaim_unique,
    }


def _validate(doc: dict[str, Any], schema_path: Path) -> None:
    jsonschema = __import__("jsonschema")
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    jsonschema.Draft7Validator(schema).validate(doc)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--bridge", type=Path, default=DEFAULT_BRIDGE)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--mvp", type=Path, default=DEFAULT_MVP)
    ap.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA)
    ap.add_argument("--skip-mvp", action="store_true")
    ap.add_argument("--no-mirror-artifact", action="store_true", help="Skip writing docs/final artifact")
    ap.add_argument("--skip-validate", action="store_true")
    args = ap.parse_args()
    if not args.bridge.is_file():
        print(f"missing bridge: {args.bridge}", file=sys.stderr)
        return 1
    bridge_doc = json.loads(args.bridge.read_text(encoding="utf-8"))
    doc = build_slice(bridge_doc)
    violations = scan_forbidden(doc)
    if violations:
        print(f"export_guard violations: {violations}", file=sys.stderr)
        return 2
    if not args.skip_validate and args.schema.is_file():
        _validate(doc, args.schema)
    text = json.dumps(doc, ensure_ascii=False, indent=2) + "\n"
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(text, encoding="utf-8")
    print(f"wrote {args.out_json} stages={len(doc.get('narrative_route_public') or [])}")
    if not args.no_mirror_artifact and args.out_json != DEFAULT_OUT:
        DEFAULT_OUT.parent.mkdir(parents=True, exist_ok=True)
        DEFAULT_OUT.write_text(text, encoding="utf-8")
        print(f"mirrored {DEFAULT_OUT}")
    elif not args.no_mirror_artifact and args.out_json == DEFAULT_OUT:
        pass
    if not args.skip_mvp:
        args.mvp.parent.mkdir(parents=True, exist_ok=True)
        args.mvp.write_text(text, encoding="utf-8")
        print(f"copied mvp {args.mvp}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
