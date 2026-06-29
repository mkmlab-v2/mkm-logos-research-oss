#!/usr/bin/env python3
"""Build CapCut/AntiGravity handoff markdown from ranked STT segments [HYPO]."""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.infer_media_segment_provenance_v0 import enrich_segments_provenance_v0
from scripts.media_segment_mdl_compress_v0 import compress_media_text_mdl_v0
from scripts.ollama_shallow_router_nsm_v1 import infer_nsm_prime_tags
from scripts.rank_media_segments_v0 import (
    compute_multilens_rank_v0,
    compute_scholarly_rank_v0,
)

DEFAULT_SOURCE = ROOT / "tests/fixtures/media_stt_transcription_v1.example.json"
DEFAULT_TEMPLATE = ROOT / "scripts/templates/media_handoff_worker_v1.md.template"
DEFAULT_OUT_DIR = ROOT / "reports/handoff_workers"
TRANSCRIPTION_SCHEMA = ROOT / "docs/final/schemas/media_stt_transcription_v1.schema.json"
REPORT_SCHEMA = ROOT / "docs/final/schemas/media_handoff_worker_report_v1.schema.json"
CLOUD_SKIP_POINTER = ROOT / "reports/ollama_shallow_oracle_gap_stress_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _validate_optional(doc: dict[str, Any], schema_path: Path) -> None:
    try:
        import jsonschema
    except ImportError:
        return
    schema = json.loads(schema_path.read_text(encoding="utf-8-sig"))
    jsonschema.Draft7Validator(schema).validate(doc)


def _cloud_skip_pointer_line() -> str:
    if not CLOUD_SKIP_POINTER.is_file():
        return "reports/ollama_shallow_oracle_gap_stress_v1_latest.json (missing — run shallow stress chain)"
    try:
        doc = _read_json(CLOUD_SKIP_POINTER)
        raw = doc.get("raw") if isinstance(doc.get("raw"), dict) else doc
        ratio = raw.get("cloud_skip_ratio")
        if ratio is not None:
            return f"{_rel(CLOUD_SKIP_POINTER)} · cloud_skip_ratio={ratio}"
    except json.JSONDecodeError:
        pass
    return _rel(CLOUD_SKIP_POINTER)


def _timeline_table(segments: list[dict[str, Any]]) -> str:
    lines = [
        "| Index | Start | End | Score | Text |",
        "| :--- | :--- | :--- | ---: | :--- |",
    ]
    for idx, seg in enumerate(segments, 1):
        text = str(seg.get("text") or "").replace("|", "\\|").replace("\n", " ")
        lines.append(
            f"| **#{idx:02d}** | {seg.get('start', '')} | {seg.get('end', '')} | "
            f"{seg.get('v0_score', '')} | \"{text}\" |"
        )
    return "\n".join(lines) + "\n"


def _mdl_preview(text: str, limit: int = 160) -> str:
    cleaned = re.sub(r"\s+", " ", str(text or "")).strip()
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 1] + "…"


def _mdl_row_from_segment(
    seg: dict[str, Any],
    *,
    anchor_keywords: list[str],
) -> dict[str, Any]:
    mdl = compress_media_text_mdl_v0(str(seg.get("text") or ""), anchor_keywords=anchor_keywords)
    return {
        "segment_id": seg.get("id"),
        "start": seg.get("start"),
        "provenance_hint": seg.get("provenance_hint"),
        **mdl,
    }


def _resolve_mdl_lanes(
    *,
    top_clips: list[dict[str, Any]],
    multilens_clips: list[dict[str, Any]],
    theme_keywords: list[str],
    multilens_keywords: list[str],
    mdl_artifact: Path | None,
) -> dict[str, Any]:
    if mdl_artifact and mdl_artifact.is_file():
        doc = _read_json(mdl_artifact)
        lanes = doc.get("lanes")
        if isinstance(lanes, dict):
            return lanes

    scholarly_top1 = None
    if top_clips:
        scholarly_top1 = _mdl_row_from_segment(top_clips[0], anchor_keywords=theme_keywords)

    multilens_top3: list[dict[str, Any]] = []
    if multilens_keywords:
        for seg in multilens_clips:
            multilens_top3.append(
                _mdl_row_from_segment(seg, anchor_keywords=multilens_keywords),
            )

    return {"scholarly_top1": scholarly_top1, "multilens_top3": multilens_top3}


def _layer_c_mdl_section(lanes: dict[str, Any], *, mdl_artifact: str | None) -> str:
    scholarly = lanes.get("scholarly_top1")
    multilens = list(lanes.get("multilens_top3") or [])
    if not scholarly and not multilens:
        return ""

    lines = [
        "\n---\n",
        "## 2c. Layer C MDL compression [HYPO · NON_GATING]\n",
        "Anchor-filtered clip summaries for subtitle trim / CapCut reference only.\n",
    ]
    if mdl_artifact:
        lines.append(f"- MDL artifact: `{mdl_artifact}`\n")

    if isinstance(scholarly, dict) and scholarly.get("segment_id"):
        saving = float(scholarly.get("char_saving_rate") or 0.0)
        lines.extend(
            [
                "\n### Scholarly Top-1\n",
                f"- Segment: `{scholarly.get('segment_id')}` · {scholarly.get('start', '')}\n",
                f"- Provenance: `{scholarly.get('provenance_hint', 'unknown')}`\n",
                f"- Saving: **{saving * 100:.1f}%** "
                f"({scholarly.get('raw_chars')} → {scholarly.get('compressed_chars')} chars)\n",
                f"- Preview: \"{_mdl_preview(str(scholarly.get('compressed_text') or ''))}\"\n",
            ]
        )

    if multilens:
        lines.extend(
            [
                "\n### Multilens Top clips\n",
                "| # | Segment | Start | Saving | Preview |",
                "| :--- | :--- | :--- | ---: | :--- |",
            ]
        )
        for idx, row in enumerate(multilens, 1):
            saving = float(row.get("char_saving_rate") or 0.0)
            lines.append(
                f"| **#{idx:02d}** | `{row.get('segment_id', '')}` | {row.get('start', '')} | "
                f"{saving * 100:.1f}% | \"{_mdl_preview(str(row.get('compressed_text') or ''), 100)}\" |"
            )
        lines.append("")

    return "\n".join(lines)


def _multilens_section(segments: list[dict[str, Any]], top_k: int) -> str:
    if not segments:
        return ""
    return (
        "\n---\n\n"
        f"## 2b. Multilens lane (Top-{top_k} · [NON_GATING])\n\n"
        "Logos comparative / non-gating interpretive clips only.\n\n"
        f"{_timeline_table(segments)}"
    )


def _diffusion_prompt(nsm_hints: list[str], theme: str) -> str:
    tags = ", ".join(nsm_hints) if nsm_hints else "none"
    return (
        f"Professional minimalist workspace, subtle telemetry grid overlay, cinematic lighting, "
        f"16:9, theme: {theme} --tags {tags}"
    )


def _render_template(template: str, mapping: dict[str, str]) -> str:
    out = template
    for key, val in mapping.items():
        out = out.replace(f"{{{{{key}}}}}", val)
    return out


def build_handoff_report(
    data: dict[str, Any],
    *,
    task_id: str,
    source_json: Path,
    top_k: int = 3,
    multilens_top_k: int = 2,
    mdl_artifact: Path | None = None,
) -> tuple[dict[str, Any], str]:
    if data.get("schema") != "media_stt_transcription_v1":
        raise ValueError("source schema must be media_stt_transcription_v1")

    theme_keywords = list(data.get("theme_keywords") or [])
    negative_keywords = list(data.get("negative_keywords") or [])
    multilens_keywords = list(data.get("multilens_keywords") or [])
    segments = [s for s in (data.get("segments") or []) if isinstance(s, dict)]
    if not segments:
        raise ValueError("segments empty")

    segments = enrich_segments_provenance_v0(
        segments,
        theme_keywords=theme_keywords,
        negative_keywords=negative_keywords or None,
    )

    ranked = compute_scholarly_rank_v0(
        segments,
        theme_keywords,
        negative_keywords=negative_keywords or None,
    )
    top_clips = ranked[: max(1, top_k)]

    multilens_clips: list[dict[str, Any]] = []
    if multilens_keywords:
        multilens_clips = compute_multilens_rank_v0(
            segments,
            multilens_keywords,
            top_k=max(1, multilens_top_k),
        )

    combined_text = " ".join(str(c.get("text") or "") for c in top_clips)
    nsm_hints = infer_nsm_prime_tags("design", combined_text)

    theme = str(data.get("theme") or "")
    target_suite = str(data.get("target_suite") or "CapCut & AntiGravity")
    diffusion = _diffusion_prompt(nsm_hints, theme)

    mdl_lanes = _resolve_mdl_lanes(
        top_clips=top_clips,
        multilens_clips=multilens_clips,
        theme_keywords=theme_keywords,
        multilens_keywords=multilens_keywords,
        mdl_artifact=mdl_artifact,
    )
    mdl_artifact_rel = _rel(mdl_artifact) if mdl_artifact and mdl_artifact.is_file() else None

    report: dict[str, Any] = {
        "schema": "media_handoff_worker_report_v1",
        "generated_at_utc": _utc_now(),
        "task_id": task_id,
        "research_only": True,
        "send_gate": "HOLD",
        "hypothesis_class": "HYPO",
        "source_json": _rel(source_json),
        "markdown_path": "",
        "rank_engine": "rank_media_segments_v0+dual_lane",
        "top_k": top_k,
        "top_segments": top_clips,
        "multilens_top_k": multilens_top_k if multilens_clips else 0,
        "multilens_top_segments": multilens_clips,
        "layer_c_mdl": mdl_lanes,
        "layer_c_mdl_artifact": mdl_artifact_rel,
        "nsm_prompt_hints": nsm_hints,
        "cloud_skip_pointer": _cloud_skip_pointer_line(),
        "reproduce": f"py scripts/build_media_handoff_worker_v1.py --task-id {task_id} --source {_rel(source_json)}",
    }

    if not DEFAULT_TEMPLATE.is_file():
        raise FileNotFoundError(f"template missing: {DEFAULT_TEMPLATE}")

    template = DEFAULT_TEMPLATE.read_text(encoding="utf-8")
    md = _render_template(
        template,
        {
            "TASK_ID": task_id,
            "GENERATED_AT": report["generated_at_utc"],
            "RANK_ENGINE": report["rank_engine"],
            "CLOUD_SKIP_POINTER": report["cloud_skip_pointer"],
            "TARGET_SUITE": target_suite,
            "WAV_SOURCE": str(data.get("wav_source") or ""),
            "SOURCE_JSON": _rel(source_json),
            "THEME": theme,
            "TOP_K": str(top_k),
            "TIMELINE_TABLE": _timeline_table(top_clips),
            "MULTILENS_SECTION": _multilens_section(multilens_clips, multilens_top_k),
            "LAYER_C_MDL_SECTION": _layer_c_mdl_section(mdl_lanes, mdl_artifact=mdl_artifact_rel),
            "NSM_HINTS": ", ".join(nsm_hints) if nsm_hints else "none",
            "DIFFUSION_PROMPT": diffusion,
        },
    )
    return report, md


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--task-id", default="20260621-HQ01")
    ap.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    ap.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    ap.add_argument("--top-k", type=int, default=3)
    ap.add_argument("--multilens-top-k", type=int, default=2)
    ap.add_argument("--mdl-artifact", type=Path, default=None)
    ap.add_argument("--strict-schema", action="store_true")
    args = ap.parse_args()

    source = args.source if args.source.is_absolute() else ROOT / args.source
    if not source.is_file():
        print(json.dumps({"ok": False, "error": "source_missing", "path": str(source)}), file=sys.stderr)
        return 1

    data = _read_json(source)
    if args.strict_schema:
        _validate_optional(data, TRANSCRIPTION_SCHEMA)

    mdl_path = None
    if args.mdl_artifact:
        mdl_path = args.mdl_artifact if args.mdl_artifact.is_absolute() else ROOT / args.mdl_artifact

    try:
        report, md = build_handoff_report(
            data,
            task_id=args.task_id,
            source_json=source,
            top_k=args.top_k,
            multilens_top_k=args.multilens_top_k,
            mdl_artifact=mdl_path,
        )
    except ValueError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}), file=sys.stderr)
        return 1

    out_dir = args.out_dir if args.out_dir.is_absolute() else ROOT / args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    md_path = out_dir / f"HW-{args.task_id}-LOGOS_CLIP.md"
    json_path = out_dir / f"HW-{args.task_id}-report.json"
    report["markdown_path"] = _rel(md_path)
    md_path.write_text(md, encoding="utf-8")
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if args.strict_schema:
        _validate_optional(report, REPORT_SCHEMA)

    print(
        json.dumps(
            {
                "ok": True,
                "markdown_path": report["markdown_path"],
                "report_json": _rel(json_path),
                "top_segment_ids": [s.get("id") for s in report["top_segments"]],
                "multilens_top_segment_ids": [
                    s.get("id") for s in report.get("multilens_top_segments") or []
                ],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
