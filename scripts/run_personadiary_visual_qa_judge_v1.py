#!/usr/bin/env python3
"""PersonaDiary visual capture + optional Vision QA judge ([HYPO] · research_only).

tier_0: capture-only (screenshot bytes / live /ops fetch) — no API cost.
tier_google_developer: gemini_multimodal_batch crosscheck (AI Studio key).
tier_google_vertex / tier_azure_openai: attempted when --billing set; falls back to skip with reason.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SHOT = ROOT / "reports/personadiary_android_emulator_smoke_latest.png"
DEFAULT_OUT = ROOT / "reports/personadiary_visual_qa_judge_latest.json"
CAPTURE_OUT = ROOT / "reports/personadiary_visual_capture_latest.json"
OPS_URL = "https://personadiary.com/ops"
MARKERS = ("pd-main-ops", "pd-ops-native-hypo", "Persona Diary")
MAX_VISION_PER_MONTH = int(os.getenv("MKM_PERSONADIARY_VISION_QA_MAX_PER_MONTH", "4"))


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _monthly_vision_count() -> int:
    log = ROOT / "reports/personadiary_visual_qa_usage.jsonl"
    if not log.is_file():
        return 0
    month = datetime.now(timezone.utc).strftime("%Y-%m")
    n = 0
    for line in log.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if row.get("event") == "vision_qa" and str(row.get("month", "")).startswith(month):
            n += 1
    return n


def _append_usage(billing: str) -> None:
    log = ROOT / "reports/personadiary_visual_qa_usage.jsonl"
    log.parent.mkdir(parents=True, exist_ok=True)
    row = {
        "event": "vision_qa",
        "ts_utc": _utc_now(),
        "month": datetime.now(timezone.utc).strftime("%Y-%m"),
        "billing": billing,
    }
    with log.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def capture_live_ops(timeout: int = 25) -> dict:
    req = urllib.request.Request(OPS_URL, headers={"User-Agent": "MKM-PersonadiaryVisualCapture/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            html = resp.read().decode("utf-8", errors="replace")
        missing = [m for m in MARKERS if m not in html]
        return {
            "live_fetch_ok": len(missing) == 0,
            "url": OPS_URL,
            "missing_markers": missing,
            "html_bytes": len(html.encode("utf-8")),
        }
    except Exception as exc:  # noqa: BLE001 — smoke report
        return {"live_fetch_ok": False, "url": OPS_URL, "error": str(exc)[:200]}


def capture_screenshot(shot_path: Path) -> dict:
    if not shot_path.is_file():
        return {"screenshot_ok": False, "path": str(shot_path.relative_to(ROOT)), "bytes": 0}
    size = shot_path.stat().st_size
    return {
        "screenshot_ok": size >= 1000,
        "path": str(shot_path.relative_to(ROOT)),
        "bytes": size,
    }


def _run_gemini_crosscheck(shot: Path, billing: str) -> dict:
    if _monthly_vision_count() >= MAX_VISION_PER_MONTH:
        return {
            "skipped": True,
            "reason": f"monthly_cap:{MAX_VISION_PER_MONTH}",
            "billing": billing,
        }
    if billing == "vertex":
        proc = subprocess.run(
            [sys.executable, str(ROOT / "scripts/check_google_genai_readiness_v1.py"), "check"],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            return {"skipped": True, "reason": "vertex_not_ready", "billing": billing}
    if billing == "azure":
        ready = ROOT / "reports/azure_openai_llm_readiness_latest.json"
        if not ready.is_file():
            return {"skipped": True, "reason": "azure_readiness_missing", "billing": billing}
        try:
            data = json.loads(ready.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {"skipped": True, "reason": "azure_readiness_invalid", "billing": billing}
        if not data.get("readiness_ok"):
            return {"skipped": True, "reason": "azure_readiness_not_ok", "billing": billing}
        return {
            "skipped": True,
            "reason": "azure_vision_judge_not_wired_use_developer_or_vertex",
            "billing": billing,
        }

    prompt = (
        "PersonaDiary /ops mobile PWA preview. Check layout break, unreadable text, "
        "broken responsive shell, missing nav. Reply JSON: "
        '{"verdict":"pass|warn|fail","issues":[],"confidence":"low|medium"}'
    )
    meta = f"url={OPS_URL}; billing={billing}; research_only=true"
    cmd = [
        sys.executable,
        str(ROOT / "scripts/gemini_multimodal_batch.py"),
        "crosscheck",
        "--file",
        str(shot),
        "--meta",
        meta,
        "--prompt",
        prompt,
        "--thinking-budget",
        "0",
    ]
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=120)
    _append_usage(billing if billing in ("developer", "vertex") else "developer")
    text = (proc.stdout or proc.stderr or "").strip()
    verdict = "warn"
    if proc.returncode != 0:
        return {"ok": False, "exit_code": proc.returncode, "billing": billing, "raw": text[:2000]}
    try:
        # model may return markdown fenced json
        chunk = text
        if "```" in chunk:
            chunk = chunk.split("```")[1]
            if chunk.startswith("json"):
                chunk = chunk[4:]
        parsed = json.loads(chunk.strip())
        verdict = str(parsed.get("verdict", "warn")).lower()
    except (json.JSONDecodeError, IndexError):
        verdict = "warn"
    return {
        "ok": verdict in ("pass", "warn"),
        "verdict": verdict,
        "billing": billing,
        "exit_code": proc.returncode,
        "raw_excerpt": text[:1500],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--screenshot", type=Path, default=DEFAULT_SHOT)
    parser.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    parser.add_argument(
        "--mode",
        choices=("capture-only", "full"),
        default="full",
        help="capture-only writes visual_capture artifact without LLM",
    )
    parser.add_argument(
        "--billing",
        choices=("dry-run", "developer", "vertex", "azure"),
        default="dry-run",
    )
    parser.add_argument("--capture-out", type=Path, default=CAPTURE_OUT)
    args = parser.parse_args()

    live = capture_live_ops()
    shot = capture_screenshot(args.screenshot)
    capture = {
        "schema": "personadiary_visual_capture_v1",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "live": live,
        "screenshot": shot,
        "capture_ok": bool(live.get("live_fetch_ok")) or bool(shot.get("screenshot_ok")),
    }
    args.capture_out.parent.mkdir(parents=True, exist_ok=True)
    args.capture_out.write_text(json.dumps(capture, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if args.mode == "capture-only":
        print(f"WROTE: {args.capture_out}")
        return 0 if capture["capture_ok"] else 1

    judge: dict
    if args.billing == "dry-run":
        judge = {
            "skipped": True,
            "reason": "dry_run",
            "hint": "Use --billing developer|vertex for Vision QA (credit tier)",
        }
    elif not shot.get("screenshot_ok"):
        judge = {"skipped": True, "reason": "no_screenshot", "hint": "Run android emulator smoke or provide --screenshot"}
    else:
        judge = _run_gemini_crosscheck(args.screenshot, args.billing)

    report = {
        "schema": "personadiary_visual_qa_judge_v1",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tier": "B",
        "billing": args.billing,
        "capture": capture,
        "judge": judge,
        "ok": capture["capture_ok"] and (judge.get("skipped") or judge.get("ok", False)),
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.out_json}")
    if not report["ok"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
