#!/usr/bin/env python3
"""Validate PersonaDiary Android emulator CLI run artifact (research_only · [HYPO])."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RUN_JSON = ROOT / "reports/personadiary_android_emulator_run_latest.json"
DEFAULT_SHOT = ROOT / "reports/personadiary_android_emulator_smoke_latest.png"
DEFAULT_OUT = ROOT / "reports/personadiary_android_emulator_smoke_latest.json"
INVOKE_PS1 = ROOT / "scripts/Invoke-PersonadiaryAndroidEmulatorRun_v1.ps1"
PKG = "com.mkmlife.personadiary.hypo"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _probe_screenshot_edge_bands(shot_path: Path) -> dict:
    """Detect non-black (#0a1210) body leak in top/bottom bands — optional Pillow."""
    out: dict = {"ok": None, "skipped": None, "top_band_green_leak": None, "bottom_band_green_leak": None}
    if not shot_path.is_file():
        out["skipped"] = "screenshot_missing"
        return out
    try:
        from PIL import Image  # type: ignore[import-untyped]
    except ImportError:
        out["skipped"] = "pillow_missing"
        return out

    try:
        img = Image.open(shot_path).convert("RGB")
    except Exception:
        out["skipped"] = "pillow_open_failed"
        return out
    w, h = img.size
    if w < 8 or h < 16:
        out["skipped"] = "screenshot_too_small"
        return out

    def green_leak(y0: int, y1: int) -> bool:
        leaks = 0
        samples = 0
        for y in range(y0, y1):
            for x in range(0, w, max(1, w // 24)):
                r, g, b = img.getpixel((x, y))
                samples += 1
                # Hub clinical green (#0a1210 family) — exclude iOS tint blue FAB (b > g).
                strong = g > r + 8 and g > b + 8 and g > 28
                subtle = r < 24 and g > 14 and b <= g and (g - r) >= 6 and (g - b) >= 2
                if strong or subtle:
                    leaks += 1
        return samples > 0 and (leaks / samples) > 0.08

    band = max(4, h // 40)
    top_leak = green_leak(0, band)
    bottom_leak = green_leak(h - band, h)
    out["top_band_green_leak"] = top_leak
    out["bottom_band_green_leak"] = bottom_leak
    out["ok"] = not top_leak and not bottom_leak
    return out


def validate_run_report(run: dict, *, shot_path: Path) -> tuple[bool, list[str]]:
    errors: list[str] = []
    if run.get("schema") != "personadiary_android_emulator_run_v1":
        errors.append("schema_mismatch")
    if run.get("package") != PKG:
        errors.append(f"package_expected:{PKG}")
    if not run.get("pid"):
        errors.append("missing_pid")
    if not run.get("webview_ok"):
        errors.append("webview_not_foreground")
    if run.get("system_anr_visible"):
        errors.append("system_anr_visible")
    if not run.get("research_only"):
        errors.append("research_only_false")
    if run.get("hypothesis_tier") != "B":
        errors.append("hypothesis_tier_not_B")

    shot = shot_path
    band_probe: dict = {"skipped": "no_screenshot"}
    if not shot.is_file():
        errors.append(f"screenshot_missing:{shot.relative_to(ROOT)}")
    elif shot.stat().st_size < 1000:
        errors.append("screenshot_too_small")
    else:
        band_probe = _probe_screenshot_edge_bands(shot)
        if band_probe.get("ok") is False:
            errors.append("edge_band_green_leak_detected")

    ok = len(errors) == 0 and bool(run.get("ok"))
    return ok, errors, band_probe


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-json", type=Path, default=DEFAULT_RUN_JSON)
    parser.add_argument("--screenshot", type=Path, default=DEFAULT_SHOT)
    parser.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    parser.add_argument(
        "--invoke",
        action="store_true",
        help="Run Invoke-PersonadiaryAndroidEmulatorRun_v1.ps1 first (start AVD + install + launch)",
    )
    parser.add_argument("--skip-emulator-start", action="store_true")
    parser.add_argument("--skip-install", action="store_true")
    args = parser.parse_args()

    if args.invoke:
        if not INVOKE_PS1.is_file():
            print(f"invoke_script_missing: {INVOKE_PS1}", file=sys.stderr)
            return 1
        cmd = [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(INVOKE_PS1),
        ]
        if args.skip_emulator_start:
            cmd.append("-SkipEmulatorStart")
        if args.skip_install:
            cmd.append("-SkipInstall")
        proc = subprocess.run(cmd, cwd=ROOT)
        if proc.returncode != 0:
            return proc.returncode

    if not args.run_json.is_file():
        print(f"run_json_missing: {args.run_json}", file=sys.stderr)
        return 1

    run = json.loads(args.run_json.read_text(encoding="utf-8-sig"))
    ok, errors, band_probe = validate_run_report(run, shot_path=args.screenshot)

    report = {
        "schema": "personadiary_android_emulator_smoke_v1",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tier": "B",
        "run_json": str(args.run_json.relative_to(ROOT)),
        "screenshot": str(args.screenshot.relative_to(ROOT)) if args.screenshot.is_file() else None,
        "pid": run.get("pid"),
        "webview_ok": run.get("webview_ok"),
        "system_anr_visible": run.get("system_anr_visible"),
        "edge_band_probe": band_probe,
        "ok": ok,
        "errors": errors,
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.out_json}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
