#!/usr/bin/env python3
"""Build Logos bridge sidecar from YouTube media ingest artifacts [HYPO]."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.ollama_shallow_router_nsm_v1 import infer_nsm_prime_tags


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _segment_clip(row: dict[str, Any], *, full_text: str | None = None) -> dict[str, Any]:
    text = full_text or str(row.get("text_preview") or row.get("text") or "")
    return {
        "segment_id": row.get("id") or row.get("segment_id"),
        "start": row.get("start"),
        "end": row.get("end"),
        "v0_score": row.get("v0_score"),
        "provenance_hint": row.get("provenance_hint"),
        "nsm_prime_tags": infer_nsm_prime_tags(text)[:6],
        "text_preview": text[:240],
    }


def build_bridge_sidecar(
    *,
    diff_report: dict[str, Any],
    stt_doc: dict[str, Any] | None,
    ssot: dict[str, Any],
    handoff_markdown: str | None,
) -> dict[str, Any]:
    ingest = diff_report.get("ingest") or {}
    seg_map = {str(s.get("id")): s for s in (stt_doc or {}).get("segments") or []}

    def _enrich(row: dict[str, Any]) -> dict[str, Any]:
        sid = str(row.get("id") or row.get("segment_id") or "")
        full = seg_map.get(sid)
        text = str((full or {}).get("text") or row.get("text_preview") or "")
        return _segment_clip(row, full_text=text)

    scholarly = [_enrich(r) for r in ingest.get("scholarly_top3") or []]
    multilens = [_enrich(r) for r in ingest.get("multilens_top3") or []]

    query_id = str(ssot.get("logos_query_id") or "media_youtube_macro")
    artifacts = ssot.get("artifacts") or {}
    return {
        "schema": "media_youtube_logos_bridge_sidecar_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc_now(),
        "hypothesis_class": "HYPO",
        "research_only": True,
        "non_gating": True,
        "send_gate": "HOLD",
        "track_a_blocked": True,
        "query_id": query_id,
        "query_ko": str(ssot.get("title") or "YouTube media ingest bridge"),
        "youtube_url": ssot.get("youtube_url"),
        "video_id": ssot.get("video_id"),
        "domain": str(ssot.get("logos_domain") or "macro_regime"),
        "lens_note_ko": str(
            ssot.get("lens_note_ko")
            or "거시·운영 레이어 해설 — Logos 성경 렌즈와 격벽, Track A 승격 금지"
        ),
        "sources": {
            "fixture_transcript": ssot.get("fixture_transcript"),
            "diff_report": artifacts.get("diff_report") or "reports/media_youtube_ingest_diff_v0_latest.json",
            "stt_json": artifacts.get("stt_json") or "reports/forensics/stt_transcription_v1_latest.json",
            "handoff_markdown": handoff_markdown,
        },
        "provenance_counts": ingest.get("provenance_counts") or {},
        "scholarly_top3": scholarly,
        "multilens_top3": multilens,
        "layer_c_mdl_poc": diff_report.get("layer_c_mdl_poc"),
        "topology_ingest_pointer": (
            f"data/logos/topology_sidecar_{query_id}_hypo_v1.seed.json"
        ),
        "intentional_causal_gap": {
            "why_question_assembled": False,
            "note_ko": "미디어 클립→Logos topology 자동 결선 금지 — bridge만 [HYPO]",
        },
        "reproduce": str(
            ssot.get("reproduce") or "py scripts/run_media_youtube_macro_ingest_chain_v1.py"
        ),
    }


def build_topology_seed(
    bridge: dict[str, Any],
    *,
    ssot: dict[str, Any],
) -> dict[str, Any]:
    query_id = str(bridge.get("query_id") or "media_youtube_macro")
    discourse = str(
        ssot.get("topology_discourse_paradigm_ko") or "매크로·통화정책 해설 (미디어 클립)"
    )
    stages: list[dict[str, Any]] = []
    for idx, clip in enumerate(bridge.get("scholarly_top3") or [], 1):
        stages.append(
            {
                "stage_id": f"media_scholarly_{idx}",
                "order": idx,
                "label_ko": str(clip.get("text_preview") or "")[:80],
                "discourse_paradigm_ko": discourse,
                "bottleneck_ko": f"provenance={clip.get('provenance_hint')} · start={clip.get('start')}",
                "verse_refs": [],
                "utterance_class": "unknown_gap",
            }
        )
    default_nodes = [
        {
            "node_id": "fed_inflation_gate",
            "label_ko": "연준 물가 게이트",
            "closed_system_ko": "2% 목표·금리 인상으로 물가 억제.",
            "open_system_ko": "정치·관세·지정학 shock — 일시적 vs 고착화 논쟁.",
            "verse_refs": [],
            "utterance_class": "unknown_gap",
        },
        {
            "node_id": "ai_productivity_bet",
            "label_ko": "AI 생산성 베팅",
            "closed_system_ko": "그린스폰 IT 서사 — 성장↑ 물가↓.",
            "open_system_ko": "칩플레이션·버블·구슬리 경고 — 단기 vs 장기.",
            "verse_refs": [],
            "utterance_class": "unknown_gap",
        },
        {
            "node_id": "debt_gdp_ratio",
            "label_ko": "부채/GDP 비율",
            "closed_system_ko": "부채 총량 축소 — 일본형 디플레이션 위험.",
            "open_system_ko": "성장으로 비율 희석 — 홍길동 비유.",
            "verse_refs": [],
            "utterance_class": "unknown_gap",
        },
    ]
    nodes = list(ssot.get("topology_nodes") or default_nodes)
    top1 = (bridge.get("scholarly_top3") or [{}])[0]
    media_ref = "Media.0.0"
    return {
        "schema": "logos_topology_sidecar_hypo_v1",
        "hypothesis_class": "HYPO",
        "research_only": True,
        "non_gating": True,
        "send_gate": "HOLD",
        "track_a_blocked": True,
        "materialize_canon": False,
        "query_id": query_id,
        "query_ko": str(ssot.get("title") or bridge.get("query_ko") or ""),
        "anchor_ref": media_ref,
        "external_source": {
            "kind": "other",
            "label_ko": f"YouTube 미디어 ingest — {ssot.get('video_id') or 'macro'}",
            "ingest_mode": "topology_sidecar",
        },
        "anchor_matrix": nodes,
        "narrative_route": stages or [
            {
                "stage_id": "media_fallback",
                "order": 1,
                "label_ko": "미디어 클립 fallback",
                "discourse_paradigm_ko": "매크로 해설",
                "bottleneck_ko": "scholarly_top3 empty",
                "verse_refs": [],
                "utterance_class": "unknown_gap",
            }
        ],
        "bridge_pivot": {
            "verse_ref": media_ref,
            "label_ko": "미디어→Logos bridge pivot",
            "reading_ko": str(top1.get("text_preview") or "")[:200],
            "utterance_class": "unknown_gap",
        },
        "reading_pack": [
            {
                "pack_id": str(ssot.get("reading_pack_id") or "media_handoff"),
                "label_ko": "CapCut handoff 클립",
                "summary_ko": str(
                    ssot.get("reading_pack_summary_ko")
                    or "YouTube media ingest ranked clips — non-gating [HYPO]"
                ),
                "utterance_class": "unknown_gap",
                "deep_synthesis_md_path": bridge.get("sources", {}).get("handoff_markdown"),
            }
        ],
        "intentional_causal_gap": bridge.get("intentional_causal_gap") or {},
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--diff-report",
        type=Path,
        default=ROOT / "reports/media_youtube_ingest_diff_v0_latest.json",
    )
    ap.add_argument(
        "--stt-json",
        type=Path,
        default=ROOT / "reports/forensics/stt_transcription_v1_latest.json",
    )
    ap.add_argument(
        "--ssot",
        type=Path,
        default=ROOT / "tests/fixtures/media_youtube_macro_trump_fed_ssot_v1.json",
    )
    ap.add_argument("--handoff-md", type=Path, default=None)
    ap.add_argument(
        "--out-bridge",
        type=Path,
        default=ROOT / "docs/final/artifacts/media_youtube_logos_bridge_v1_latest.json",
    )
    ap.add_argument("--write-topology-seed", action="store_true")
    ap.add_argument("--ingest-topology", action="store_true")
    args = ap.parse_args()

    diff_path = args.diff_report if args.diff_report.is_absolute() else ROOT / args.diff_report
    stt_path = args.stt_json if args.stt_json.is_absolute() else ROOT / args.stt_json
    ssot_path = args.ssot if args.ssot.is_absolute() else ROOT / args.ssot

    if not diff_path.is_file() or not ssot_path.is_file():
        print(json.dumps({"ok": False, "error": "missing_input"}), file=sys.stderr)
        return 1

    diff_report = _read_json(diff_path)
    ssot = _read_json(ssot_path)
    stt_doc = _read_json(stt_path) if stt_path.is_file() else None

    task_id = str(ssot.get("default_task_id") or "MEDIA-MACRO")
    handoff_default = ROOT / f"reports/handoff_workers/HW-{task_id}-LOGOS_CLIP.md"
    handoff_path = args.handoff_md or handoff_default
    handoff_rel = _rel(handoff_path) if handoff_path.is_file() else None

    bridge = build_bridge_sidecar(
        diff_report=diff_report,
        stt_doc=stt_doc,
        ssot=ssot,
        handoff_markdown=handoff_rel,
    )

    out_bridge = args.out_bridge if args.out_bridge.is_absolute() else ROOT / args.out_bridge
    out_bridge.parent.mkdir(parents=True, exist_ok=True)
    out_bridge.write_text(json.dumps(bridge, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    seed_path: Path | None = None
    ingest_ok: bool | None = None
    if args.write_topology_seed or args.ingest_topology:
        seed = build_topology_seed(bridge, ssot=ssot)
        query_id = str(seed.get("query_id") or "media_youtube_macro")
        seed_path = ROOT / f"data/logos/topology_sidecar_{query_id}_hypo_v1.seed.json"
        seed_path.parent.mkdir(parents=True, exist_ok=True)
        seed_path.write_text(json.dumps(seed, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        bridge["topology_seed"] = _rel(seed_path)
        out_bridge.write_text(json.dumps(bridge, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if args.ingest_topology and seed_path and seed_path.is_file():
        import subprocess

        proc = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts/ingest_logos_topology_sidecar_hypo_v1.py"),
                "--input",
                str(seed_path),
            ],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
        )
        ingest_ok = proc.returncode == 0
        if proc.returncode != 0:
            print(proc.stderr or proc.stdout, file=sys.stderr)
            print(
                json.dumps(
                    {
                        "ok": False,
                        "bridge": _rel(out_bridge),
                        "topology_seed": _rel(seed_path),
                        "topology_ingest_ok": False,
                    },
                    ensure_ascii=False,
                )
            )
            return 2

    print(
        json.dumps(
            {
                "ok": True,
                "bridge": _rel(out_bridge),
                "topology_seed": _rel(seed_path) if seed_path else None,
                "topology_ingest_ok": ingest_ok,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
