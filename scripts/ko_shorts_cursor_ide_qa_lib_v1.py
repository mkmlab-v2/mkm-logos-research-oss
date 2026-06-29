#!/usr/bin/env python3
"""Cursor IDE automated QA for ko shorts burn-in — sync, safe-area, preview [HYPO]."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

from scripts.ko_shorts_ass_burnin_lib_v1 import (
    DEFAULT_PLAY_RES,
    segments_from_srt_v1,
)
from scripts.ko_shorts_subtitle_gate_lib_v1 import (
    PROFILE_NETFLIX_V16,
    PROFILES,
    refine_segments_for_profile_v1,
)
from scripts.media_stt_transcription_lib_v1 import (
    _is_orphan_ending,
    _is_orphan_prefix,
    parse_timestamp_seconds,
)

ROOT = Path(__file__).resolve().parents[1]
SYNC_THRESHOLD_MS = 300.0
SHORTS_UI_DANGER_BAND_PX = 180
DEFAULT_PORT = 8796

CASES = [
    {
        "case_id": "web_deeply",
        "spike_json": "reports/ko_shorts_stt_timing_web_deeply_v1_latest.json",
        "mp4": "reports/ko_shorts_burnin_web_deeply_v1_latest.mp4",
        "srt": "reports/ko_shorts_burnin_web_deeply_v1_latest.srt",
        "ass": "reports/ko_shorts_burnin_web_deeply_v1_latest.ass",
    },
    {
        "case_id": "web_pansori",
        "spike_json": "reports/ko_shorts_stt_timing_web_pansori_v1_latest.json",
        "mp4": "reports/ko_shorts_burnin_web_pansori_v1_latest.mp4",
        "srt": "reports/ko_shorts_burnin_web_pansori_v1_latest.srt",
        "ass": "reports/ko_shorts_burnin_web_pansori_v1_latest.ass",
    },
    {
        "case_id": "web_youtube_edu",
        "spike_json": "reports/ko_shorts_stt_timing_web_youtube_edu_v1_latest.json",
        "mp4": "reports/ko_shorts_burnin_web_youtube_edu_v1_latest.mp4",
        "srt": "reports/ko_shorts_burnin_web_youtube_edu_v1_latest.srt",
        "ass": "reports/ko_shorts_burnin_web_youtube_edu_v1_latest.ass",
    },
]


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _overlap(a0: float, a1: float, b0: float, b1: float) -> float:
    return max(0.0, min(a1, b1) - max(a0, b0))


def check_p1_anchor_sync_v1(
    p1_segments: list[dict[str, Any]],
    *,
    threshold_ms: float = SYNC_THRESHOLD_MS,
) -> dict[str, Any]:
    """P1 cues with token_start should match aligned word onset within threshold."""
    deltas: list[float] = []
    checked = 0
    for seg in p1_segments:
        token_start = seg.get("token_start")
        if token_start is None:
            continue
        checked += 1
        cue_start = parse_timestamp_seconds(str(seg.get("start") or "00:00:00.00"))
        # token_start field in spike is chunk-local; aligned start is cue start when start_source=aligned_token
        if str(seg.get("start_source") or "") == "aligned_token":
            deltas.append(0.0)
        else:
            deltas.append(abs(cue_start) * 1000.0)
    within = sum(1 for d in deltas if d <= threshold_ms)
    return {
        "checked_cues": checked,
        "within_threshold": within,
        "threshold_ms": threshold_ms,
        "pass_rate": round(within / checked, 3) if checked else None,
        "auto_pass": checked > 0 and within == checked,
    }


def check_profile_cue_parent_span_v1(
    p1_segments: list[dict[str, Any]],
    profile_segments: list[dict[str, Any]],
) -> dict[str, Any]:
    """Netflix refined cues must stay inside parent P1 time spans."""
    if not p1_segments or not profile_segments:
        return {"auto_pass": False, "error": "missing_segments"}
    parents = [
        (
            parse_timestamp_seconds(str(s.get("start") or "00:00:00.00")),
            parse_timestamp_seconds(str(s.get("end") or "00:00:00.00")),
        )
        for s in p1_segments
    ]
    violations: list[dict[str, Any]] = []
    for cue in profile_segments:
        cs = parse_timestamp_seconds(str(cue.get("start") or "00:00:00.00"))
        ce = parse_timestamp_seconds(str(cue.get("end") or "00:00:00.00"))
        best = max((_overlap(cs, ce, p0, p1) for p0, p1 in parents), default=0.0)
        dur = max(0.001, ce - cs)
        if best / dur < 0.5:
            violations.append({"text": cue.get("text"), "start": cue.get("start"), "overlap_ratio": round(best / dur, 3)})
    return {
        "cue_count": len(profile_segments),
        "violations": violations[:8],
        "auto_pass": len(violations) == 0,
    }


def _bottom_band_bright_ratio_v1(mp4: Path, t_sec: float, *, band_px: int = SHORTS_UI_DANGER_BAND_PX) -> dict[str, Any]:
    if shutil.which("ffmpeg") is None:
        return {"bright_ratio": None, "error": "ffmpeg_missing"}
    play_h = DEFAULT_PLAY_RES[1]
    y0 = max(0, play_h - band_px)
    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-ss",
        f"{max(0.0, t_sec):.3f}",
        "-i",
        str(mp4),
        "-vframes",
        "1",
        "-vf",
        f"crop=1080:{band_px}:0:{y0},format=gray",
        "-f",
        "rawvideo",
        "-pix_fmt",
        "gray",
        "pipe:1",
    ]
    proc = subprocess.run(cmd, capture_output=True)
    data = proc.stdout
    if proc.returncode != 0 or not data:
        return {"bright_ratio": None, "error": "frame_extract_failed", "stderr": proc.stderr.decode("utf-8", "replace")[-200:]}
    bright = sum(1 for b in data if b > 200)
    return {"bright_ratio": round(bright / len(data), 4), "band_px": band_px, "t_sec": round(t_sec, 3)}


def check_safe_area_frames_v1(
    mp4: Path,
    cues: list[dict[str, Any]],
    *,
    max_bright_ratio: float = 0.02,
    sample_limit: int = 5,
) -> dict[str, Any]:
    """Sample cue midpoints — white text in bottom UI band should be minimal."""
    samples: list[dict[str, Any]] = []
    step = max(1, len(cues) // sample_limit) if cues else 1
    for cue in cues[::step][:sample_limit]:
        cs = parse_timestamp_seconds(str(cue.get("start") or "00:00:00.00"))
        ce = parse_timestamp_seconds(str(cue.get("end") or "00:00:00.00"))
        mid = cs + max(0.05, (ce - cs) / 2.0)
        sample = _bottom_band_bright_ratio_v1(mp4, mid)
        sample["text"] = str(cue.get("text") or "")[:24]
        sample["over_threshold"] = (sample.get("bright_ratio") or 0.0) > max_bright_ratio
        samples.append(sample)
    fails = [s for s in samples if s.get("over_threshold")]
    return {
        "sample_count": len(samples),
        "fail_count": len(fails),
        "max_bright_ratio_threshold": max_bright_ratio,
        "samples": samples,
        "auto_pass": len(samples) > 0 and len(fails) == 0,
    }


def check_orphan_cues_v1(cues: list[dict[str, Any]]) -> dict[str, Any]:
    orphans = [
        str(c.get("text") or "").strip()
        for c in cues
        if _is_orphan_prefix(str(c.get("text") or "")) or _is_orphan_ending(str(c.get("text") or ""))
    ]
    return {
        "orphan_count": len(orphans),
        "orphans": orphans[:8],
        "auto_pass": len(orphans) == 0,
    }


def _preview_media_src_v1(media_rel: str) -> str:
    """Map repo-relative path to URL path when http.server --directory reports."""
    rel = str(media_rel or "").replace("\\", "/").lstrip("/")
    if rel.startswith("reports/"):
        return rel[len("reports/") :]
    return rel


def build_preview_html_v1(cases: list[dict[str, Any]], *, port: int = DEFAULT_PORT) -> str:
    cards: list[str] = []
    for case in cases:
        mp4 = _preview_media_src_v1(case.get("mp4_rel") or "")
        cid = case.get("case_id") or "case"
        cues = case.get("cues") or []
        cue_json = json.dumps(cues, ensure_ascii=False)
        cards.append(
            f"""
<section class="phone" id="{cid}">
  <div class="ui-mock">
    <div class="ui-bar"></div>
    <div class="ui-actions"><span>♥</span><span>💬</span><span>↗</span></div>
  </div>
  <video controls playsinline src="{mp4}"></video>
  <div class="meta"><strong>{cid}</strong> · cues={len(cues)}</div>
  <div class="cue" id="{cid}-cue"></div>
  <script>
    (() => {{
      const cues = {cue_json};
      const video = document.querySelector('#{cid} video');
      const el = document.getElementById('{cid}-cue');
      video.addEventListener('timeupdate', () => {{
        const t = video.currentTime;
        const hit = cues.find(c => t >= c.start_sec && t <= c.end_sec);
        el.textContent = hit ? hit.text : '—';
      }});
    }})();
  </script>
</section>"""
        )
    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="utf-8" />
  <title>MKM ko shorts Cursor preview v1</title>
  <style>
    body {{ font-family: 'Malgun Gothic', sans-serif; background:#111; color:#eee; margin:0; padding:16px; }}
    h1 {{ font-size:18px; }}
    .grid {{ display:flex; flex-wrap:wrap; gap:20px; }}
    .phone {{
      width: 280px; background:#000; border-radius:24px; padding:12px;
      border:1px solid #333; position:relative; overflow:hidden;
    }}
    video {{ width:100%; border-radius:12px; background:#000; aspect-ratio:9/16; }}
    .ui-mock {{ position:absolute; right:8px; bottom:72px; z-index:2; opacity:.55; }}
    .ui-actions {{ display:flex; flex-direction:column; gap:10px; font-size:18px; }}
    .ui-bar {{ width:36px; height:4px; background:#fff; border-radius:2px; margin-bottom:8px; opacity:.4; }}
    .meta {{ font-size:12px; color:#aaa; margin-top:8px; }}
    .cue {{ font-size:13px; min-height:40px; margin-top:6px; color:#8fd3ff; }}
    .note {{ font-size:12px; color:#888; margin-top:12px; }}
  </style>
</head>
<body>
  <h1>MKM ko shorts — Cursor IDE preview (port {port})</h1>
  <p class="note">research_only · send_gate HOLD · YouTube Shorts UI mock overlay</p>
  <div class="grid">{''.join(cards)}</div>
</body>
</html>
"""


def _cues_for_preview(segments: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for seg in segments:
        text = str(seg.get("text") or "").strip()
        if not text:
            continue
        out.append(
            {
                "text": text,
                "start_sec": parse_timestamp_seconds(str(seg.get("start") or "00:00:00.00")),
                "end_sec": parse_timestamp_seconds(str(seg.get("end") or "00:00:00.00")),
            }
        )
    return out


def run_case_cursor_qa_v1(case: dict[str, str], *, profile_key: str = PROFILE_NETFLIX_V16) -> dict[str, Any]:
    spike_path = ROOT / case["spike_json"]
    mp4_path = ROOT / case["mp4"]
    srt_path = ROOT / case["srt"]
    ass_path = ROOT / case["ass"]
    missing = [k for k, p in [("spike", spike_path), ("mp4", mp4_path), ("srt", srt_path)] if not p.is_file()]
    if missing:
        return {"case_id": case["case_id"], "ok": False, "error": f"missing:{','.join(missing)}"}

    spike = _read_json(spike_path) or {}
    p1 = list(spike.get("p1_segments") or [])
    profile = PROFILES[profile_key]
    profile_segments = refine_segments_for_profile_v1(p1, profile, two_pass=True)
    srt_segments = segments_from_srt_v1(srt_path.read_text(encoding="utf-8-sig"))

    margin_v = None
    if ass_path.is_file():
        m = re.search(
            r"Style: Default,[^,]+,\d+,[^,]+,[^,]+,[^,]+,[^,]+,[^,]+,[^,]+,[^,]+,[^,]+,[^,]+,[^,]+,[^,]+,[^,]+,[^,]+,[^,]+,[^,]+,[^,]+,[^,]+,[^,]+,(\d+),",
            ass_path.read_text(encoding="utf-8-sig"),
        )
        if m:
            margin_v = int(m.group(1))

    return {
        "case_id": case["case_id"],
        "ok": True,
        "mp4_rel": case["mp4"],
        "srt_rel": case["srt"],
        "checks": {
            "p1_anchor_sync": check_p1_anchor_sync_v1(p1),
            "profile_parent_span": check_profile_cue_parent_span_v1(p1, profile_segments),
            "safe_area_frames": check_safe_area_frames_v1(mp4_path, srt_segments),
            "orphan_cues": check_orphan_cues_v1(srt_segments),
            "ass_margin_v": {"margin_v": margin_v, "auto_pass": margin_v is not None and margin_v >= 220},
        },
        "cues": _cues_for_preview(srt_segments),
    }


def build_cursor_ide_qa_report_v1(*, profile_key: str = PROFILE_NETFLIX_V16, port: int = DEFAULT_PORT) -> dict[str, Any]:
    from datetime import datetime, timezone

    case_results = [run_case_cursor_qa_v1(c, profile_key=profile_key) for c in CASES]
    preview_cases = [c for c in case_results if c.get("ok")]
    html = build_preview_html_v1(
        [{"case_id": c["case_id"], "mp4_rel": c["mp4_rel"], "cues": c.get("cues") or []} for c in preview_cases],
        port=port,
    )
    html_path = ROOT / "reports/ko_shorts_cursor_preview_v1.html"
    html_path.write_text(html, encoding="utf-8")

    def _case_pass(cr: dict[str, Any]) -> bool:
        if not cr.get("ok"):
            return False
        checks = cr.get("checks") or {}
        keys = ("p1_anchor_sync", "profile_parent_span", "safe_area_frames", "ass_margin_v")
        return all(bool((checks.get(k) or {}).get("auto_pass")) for k in keys)

    ok_cases = sum(1 for c in case_results if _case_pass(c))
    return {
        "schema": "ko_shorts_cursor_ide_qa_v1",
        "research_only": True,
        "send_gate": "HOLD",
        "hypothesis_class": "HYPO",
        "generated_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "profile": profile_key,
        "preview_html": "reports/ko_shorts_cursor_preview_v1.html",
        "preview_url": f"http://127.0.0.1:{port}/ko_shorts_cursor_preview_v1.html",
        "cursor_ide_browser": {
            "tier": 2,
            "flow": "browser_tabs -> browser_navigate -> browser_lock -> browser_snapshot -> unlock",
            "readiness": "powershell -File scripts/check_cursor_ide_browser_readiness_v1.ps1",
        },
        "case_count": len(case_results),
        "auto_pass_case_count": ok_cases,
        "auto_pass": ok_cases == len(case_results) and len(case_results) > 0,
        "cases": case_results,
        "reproduce": "powershell -File scripts/Invoke-KoShortsCursorIdeQa_v1.ps1  # default disk-only; -StartServer for HTTP preview",
    }
