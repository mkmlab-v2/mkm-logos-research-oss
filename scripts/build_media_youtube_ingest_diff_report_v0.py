#!/usr/bin/env python3
"""Build ranking diff report after YouTube transcript ingest [HYPO]."""

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

from scripts.build_media_stt_from_youtube_transcript_v0 import build_doc_from_youtube_text
from scripts.infer_media_segment_provenance_v0 import enrich_segments_provenance_v0
from scripts.media_segment_mdl_compress_v0 import compress_media_text_mdl_v0
from scripts.parse_youtube_transcript_segments_v0 import split_youtube_transcript_blocks
from scripts.rank_media_segments_v0 import (
    compute_multilens_rank_v0,
    compute_scholarly_rank_v0,
    compute_segment_rank_v0,
)

DEFAULT_OUT = ROOT / "reports/media_youtube_ingest_diff_v0_latest.json"
DEFAULT_BASELINE = ROOT / "tests/fixtures/media_stt_transcription_polluted_bench_v1.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _segment_brief(seg: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": seg.get("id"),
        "start": seg.get("start"),
        "end": seg.get("end"),
        "v0_score": seg.get("v0_score"),
        "provenance_hint": seg.get("provenance_hint"),
        "text_preview": str(seg.get("text") or "")[:120],
    }


def _rank_lanes(doc: dict[str, Any]) -> dict[str, Any]:
    theme_keywords = list(doc.get("theme_keywords") or [])
    negative_keywords = list(doc.get("negative_keywords") or [])
    multilens_keywords = list(doc.get("multilens_keywords") or [])
    segments = enrich_segments_provenance_v0(
        list(doc.get("segments") or []),
        theme_keywords=theme_keywords,
        negative_keywords=negative_keywords or None,
    )
    scholarly = compute_scholarly_rank_v0(
        segments,
        theme_keywords,
        negative_keywords=negative_keywords or None,
    )
    multilens = compute_multilens_rank_v0(segments, multilens_keywords, top_k=3)
    debunked = [s for s in scholarly if str(s.get("provenance_hint") or "") == "debunked_fake"]
    full_ranked = compute_segment_rank_v0(
        segments,
        theme_keywords,
        negative_keywords=negative_keywords or None,
    )
    debunked_ids = {
        str(s.get("id"))
        for s in segments
        if str(s.get("provenance_hint") or "") == "debunked_fake"
    }
    fake_ranked = [s for s in full_ranked if str(s.get("id")) in debunked_ids]
    fake_bottom = list(reversed(fake_ranked[-3:])) if fake_ranked else []
    return {
        "segment_count": len(segments),
        "provenance_counts": _provenance_counts(segments),
        "scholarly_top3": [_segment_brief(s) for s in scholarly[:3]],
        "multilens_top3": [_segment_brief(s) for s in multilens[:3]],
        "debunked_in_scholarly_lane": len(debunked),
        "debunked_bottom3": [_segment_brief(s) for s in fake_bottom],
    }


def _provenance_counts(segments: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for seg in segments:
        key = str(seg.get("provenance_hint") or "unknown")
        counts[key] = counts.get(key, 0) + 1
    return counts


def build_diff_report(
    transcript: str,
    *,
    baseline_doc: dict[str, Any] | None = None,
    theme: str,
    wav_source: str,
    target_suite: str,
    theme_keywords: list[str],
    negative_keywords: list[str],
    multilens_keywords: list[str],
    merge_min_chars: int = 40,
    merge_max_chars: int = 280,
    overlap_window_sec: float = 90.0,
) -> dict[str, Any]:
    blocks = split_youtube_transcript_blocks(transcript)
    ingest_doc = build_doc_from_youtube_text(
        transcript,
        theme=theme,
        wav_source=wav_source,
        target_suite=target_suite,
        theme_keywords=theme_keywords,
        negative_keywords=negative_keywords,
        multilens_keywords=multilens_keywords,
        merge_min_chars=merge_min_chars,
        merge_max_chars=merge_max_chars,
    )
    ingest_lane = _rank_lanes(ingest_doc)
    baseline_lane = _rank_lanes(baseline_doc) if baseline_doc else None

    diff: dict[str, Any] = {
        "segment_count_delta": None,
        "scholarly_top3_id_overlap": None,
        "multilens_top3_id_overlap": None,
        "scholarly_top3_proximity": None,
        "multilens_top3_proximity": None,
    }
    if baseline_lane:
        diff["segment_count_delta"] = ingest_lane["segment_count"] - baseline_lane["segment_count"]
        diff["scholarly_top3_proximity"] = _proximity_overlap(
            ingest_lane["scholarly_top3"],
            baseline_lane["scholarly_top3"],
            window_sec=overlap_window_sec,
            theme_keywords=theme_keywords,
        )
        diff["multilens_top3_proximity"] = _proximity_overlap(
            ingest_lane["multilens_top3"],
            baseline_lane["multilens_top3"],
            window_sec=overlap_window_sec,
            theme_keywords=multilens_keywords,
        )
        diff["scholarly_top3_id_overlap"] = _id_overlap(
            ingest_lane["scholarly_top3"],
            baseline_lane["scholarly_top3"],
        )
        diff["multilens_top3_id_overlap"] = _id_overlap(
            ingest_lane["multilens_top3"],
            baseline_lane["multilens_top3"],
        )

    layer_c_mdl_poc: dict[str, Any] = {"scholarly_top1": None, "multilens_top3": []}
    seg_map = {str(s.get("id")): s for s in ingest_doc.get("segments") or []}

    def _mdl_row(top: dict[str, Any], keywords: list[str]) -> dict[str, Any] | None:
        full = seg_map.get(str(top.get("id")))
        if not full:
            return None
        mdl = compress_media_text_mdl_v0(str(full.get("text") or ""), anchor_keywords=keywords)
        return {
            "segment_id": top.get("id"),
            "start": top.get("start"),
            "provenance_hint": top.get("provenance_hint"),
            **mdl,
        }

    scholarly_top = (ingest_lane.get("scholarly_top3") or [None])[0]
    if isinstance(scholarly_top, dict) and scholarly_top.get("id"):
        layer_c_mdl_poc["scholarly_top1"] = _mdl_row(scholarly_top, theme_keywords)

    for ml_top in ingest_lane.get("multilens_top3") or []:
        if not isinstance(ml_top, dict) or not ml_top.get("id"):
            continue
        row = _mdl_row(ml_top, multilens_keywords)
        if row:
            layer_c_mdl_poc["multilens_top3"].append(row)

    return {
        "schema": "media_youtube_ingest_diff_v0",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "send_gate": "HOLD",
        "hypothesis_class": "HYPO",
        "source_chars": len(transcript),
        "parsed_block_count": len(blocks),
        "ingest": ingest_lane,
        "baseline_fixture": baseline_lane,
        "diff": diff,
        "layer_c_mdl_poc": layer_c_mdl_poc,
        "merge_min_chars": merge_min_chars,
        "merge_max_chars": merge_max_chars,
        "reproduce": "py scripts/build_media_youtube_ingest_diff_report_v0.py --help",
    }


def _start_sec(ts: str) -> float | None:
    m = re.match(r"^(\d{2}):(\d{2}):(\d{2})(?:\.(\d+))?$", str(ts or "").strip())
    if not m:
        return None
    h, mi, s, frac = m.groups()
    base = int(h) * 3600 + int(mi) * 60 + int(s)
    if frac:
        base += int(frac) / (10 ** len(frac))
    return float(base)


def _keyword_overlap(a: str, b: str, keywords: list[str]) -> int:
    return sum(1 for k in keywords if k in a and k in b)


def _proximity_overlap(
    a: list[dict[str, Any]],
    b: list[dict[str, Any]],
    *,
    window_sec: float = 90.0,
    theme_keywords: list[str] | None = None,
) -> dict[str, Any]:
    kws = theme_keywords or []
    pairs: list[dict[str, Any]] = []
    matched_b: set[int] = set()
    for ai, row_a in enumerate(a):
        ta = _start_sec(str(row_a.get("start") or ""))
        if ta is None:
            continue
        preview_a = str(row_a.get("text_preview") or "")
        best_j = None
        best_score = -1.0
        for j, row_b in enumerate(b):
            if j in matched_b:
                continue
            tb = _start_sec(str(row_b.get("start") or ""))
            if tb is None:
                continue
            dt = abs(ta - tb)
            if dt > window_sec:
                continue
            preview_b = str(row_b.get("text_preview") or "")
            kw = _keyword_overlap(preview_a, preview_b, kws)
            score = kw * 10.0 - (dt / window_sec)
            if score > best_score:
                best_score = score
                best_j = j
        if best_j is not None:
            matched_b.add(best_j)
            row_b = b[best_j]
            pairs.append(
                {
                    "ingest_start": row_a.get("start"),
                    "baseline_start": row_b.get("start"),
                    "delta_sec": round(
                        abs(ta - (_start_sec(str(row_b.get("start") or "")) or ta)),
                        1,
                    ),
                    "keyword_overlap": _keyword_overlap(
                        preview_a,
                        str(row_b.get("text_preview") or ""),
                        kws,
                    ),
                }
            )
    return {
        "overlap_count": len(pairs),
        "window_sec": window_sec,
        "pairs": pairs,
    }


def _id_overlap(a: list[dict[str, Any]], b: list[dict[str, Any]]) -> dict[str, Any]:
    # baseline uses manual ids; compare start+preview for ingest vs baseline
    a_keys = {_overlap_key(x) for x in a}
    b_keys = {_overlap_key(x) for x in b}
    inter = a_keys & b_keys
    return {"overlap_count": len(inter), "overlap_keys": sorted(inter)}


def _preview_overlap(a: list[dict[str, Any]], b: list[dict[str, Any]]) -> dict[str, Any]:
    return _id_overlap(a, b)


def _overlap_key(row: dict[str, Any]) -> str:
    return f"{row.get('start')}|{str(row.get('text_preview') or '')[:40]}"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input", type=Path, required=True)
    ap.add_argument("--baseline", type=Path, default=DEFAULT_BASELINE)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--theme", default="성경 기원 논쟁 (YouTube full ingest)")
    ap.add_argument("--wav-source", default="fixture://youtube_transcript_full_v0 (no WAV)")
    ap.add_argument("--target-suite", default="CapCut & AntiGravity [YT_FULL]")
    ap.add_argument(
        "--theme-keywords",
        default="조로,엘로힘,유수,바빌론,페르시아,다신교,종교학,학자,메시지",
    )
    ap.add_argument(
        "--negative-keywords",
        default="시친,니비루,아누나키,이시스,외계인,뇌피셜",
    )
    ap.add_argument(
        "--multilens-keywords",
        default="뱀,에덴,릴리스,오피,프로메테우스,루시퍼,지혜,선악",
    )
    ap.add_argument("--merge-min-chars", type=int, default=650)
    ap.add_argument("--merge-max-chars", type=int, default=1300)
    ap.add_argument("--overlap-window-sec", type=float, default=90.0)
    ap.add_argument("--mdl-out", type=Path, default=ROOT / "reports/media_segment_mdl_compress_v0_latest.json")
    ap.add_argument("--write-stt-json", type=Path, default=ROOT / "reports/forensics/stt_transcription_v1_latest.json")
    ap.add_argument("--task-id", default="20260621-YT-FULL")
    ap.add_argument("--chain-handoff", action="store_true")
    args = ap.parse_args()

    src = args.input if args.input.is_absolute() else ROOT / args.input
    if not src.is_file():
        print(json.dumps({"ok": False, "error": "input_missing"}), file=sys.stderr)
        return 1

    text = src.read_text(encoding="utf-8-sig")
    kws = [k.strip() for k in args.theme_keywords.split(",") if k.strip()]
    neg = [k.strip() for k in args.negative_keywords.split(",") if k.strip()]
    ml = [k.strip() for k in args.multilens_keywords.split(",") if k.strip()]

    baseline_doc = None
    baseline_path = args.baseline if args.baseline.is_absolute() else ROOT / args.baseline
    if baseline_path.is_file():
        baseline_doc = _read_json(baseline_path)

    report = build_diff_report(
        text,
        baseline_doc=baseline_doc,
        theme=args.theme,
        wav_source=args.wav_source,
        target_suite=args.target_suite,
        theme_keywords=kws,
        negative_keywords=neg,
        multilens_keywords=ml,
        merge_min_chars=args.merge_min_chars,
        merge_max_chars=args.merge_max_chars,
        overlap_window_sec=args.overlap_window_sec,
    )

    ingest_doc = build_doc_from_youtube_text(
        text,
        theme=args.theme,
        wav_source=args.wav_source,
        target_suite=args.target_suite,
        theme_keywords=kws,
        negative_keywords=neg,
        multilens_keywords=ml,
        merge_min_chars=args.merge_min_chars,
        merge_max_chars=args.merge_max_chars,
    )
    stt_out = args.write_stt_json if args.write_stt_json.is_absolute() else ROOT / args.write_stt_json
    stt_out.parent.mkdir(parents=True, exist_ok=True)
    stt_out.write_text(json.dumps(ingest_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    report["stt_json"] = _rel(stt_out)

    out = args.out if args.out.is_absolute() else ROOT / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if report.get("layer_c_mdl_poc"):
        mdl_out = args.mdl_out if args.mdl_out.is_absolute() else ROOT / args.mdl_out
        mdl_out.parent.mkdir(parents=True, exist_ok=True)
        poc = report["layer_c_mdl_poc"]
        mdl_doc = {
            "schema": "media_segment_mdl_compress_v0",
            "generated_at_utc": report["generated_at_utc"],
            "research_only": True,
            "send_gate": "HOLD",
            "hypothesis_class": "HYPO",
            "source_task": args.task_id,
            "lanes": poc,
            "universal_root_mdl_poc_pointer": (
                "scripts/run_universal_root_mdl_prune_poc_v1.py (lexicon; separate from media text)"
            ),
        }
        mdl_out.write_text(json.dumps(mdl_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        report["layer_c_mdl_artifact"] = _rel(mdl_out)
        out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    chain_ok = None
    if args.chain_handoff:
        import subprocess

        handoff_cmd = [
            sys.executable,
            str(ROOT / "scripts/build_media_handoff_worker_v1.py"),
            "--task-id",
            args.task_id,
            "--source",
            str(stt_out),
            "--multilens-top-k",
            "3",
            "--strict-schema",
        ]
        if report.get("layer_c_mdl_artifact"):
            handoff_cmd.extend(["--mdl-artifact", str(ROOT / report["layer_c_mdl_artifact"])])
        proc = subprocess.run(
            handoff_cmd,
            cwd=str(ROOT),
            capture_output=True,
            text=True,
        )
        chain_ok = proc.returncode == 0
        if proc.returncode != 0:
            print(proc.stderr or proc.stdout, file=sys.stderr)
            return 2
        report["handoff_task_id"] = args.task_id
        report["handoff_markdown"] = f"reports/handoff_workers/HW-{args.task_id}-LOGOS_CLIP.md"
        out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(
        json.dumps(
            {
                "ok": True,
                "report": _rel(out),
                "segments": report["ingest"]["segment_count"],
                "blocks": report["parsed_block_count"],
                "chain_handoff": chain_ok,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
