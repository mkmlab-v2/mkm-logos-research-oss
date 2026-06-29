#!/usr/bin/env python3
"""PersonaDiary offline/PWA scenario — SW registration + offline reload probe (tier_0).

Note: sw.js is installability-only (no fetch cache). Offline reload may fail by design;
gate passes when online markers OK and offline behavior is documented (warn) unless --strict.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "reports/personadiary_offline_pwa_scenario_latest.json"
OPS_URL = "https://personadiary.com/ops"
MARKERS = ("pd-main-ops", "Persona Diary")


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _fetch(url: str, timeout: int = 25) -> tuple[int, str]:
    req = urllib.request.Request(url, headers={"User-Agent": "MKM-PersonadiaryOfflineProbe/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.status, resp.read().decode("utf-8", errors="replace")


def urllib_probe() -> dict:
    steps: dict = {}
    try:
        st, html = _fetch(OPS_URL)
        missing = [m for m in MARKERS if m not in html]
        steps["ops_online"] = {"ok": st == 200 and not missing, "status": st, "missing": missing}
    except Exception as exc:  # noqa: BLE001
        steps["ops_online"] = {"ok": False, "error": str(exc)[:200]}
    for path in ("/personadiary/manifest.webmanifest", "/personadiary/sw.js"):
        try:
            st, body = _fetch(f"https://personadiary.com{path}")
            steps[path] = {"ok": st == 200 and len(body) > 20, "status": st, "bytes": len(body.encode())}
        except Exception as exc:  # noqa: BLE001
            steps[path] = {"ok": False, "error": str(exc)[:200]}
    return steps


def playwright_scenario(url: str, timeout_ms: int) -> dict:
    spec = importlib.util.find_spec("playwright.sync_api")
    if spec is None:
        return {"skipped": True, "reason": "playwright_not_installed"}

    from playwright.sync_api import sync_playwright

    result: dict = {"playwright": True}
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 390, "height": 844})
        page = context.new_page()
        page.goto(url, wait_until="networkidle", timeout=timeout_ms)
        page.wait_for_timeout(2500)
        online_text = page.content()
        result["online_markers_ok"] = all(m in online_text for m in MARKERS)
        sw_ok = page.evaluate(
            """async () => {
              if (!('serviceWorker' in navigator)) return { ok: false, reason: 'no_sw_api' };
              try {
                await Promise.race([
                  navigator.serviceWorker.ready,
                  new Promise((_, r) => setTimeout(() => r(new Error('timeout')), 8000)),
                ]);
              } catch (e) {
                return { ok: false, reason: 'ready_timeout' };
              }
              const reg = await navigator.serviceWorker.getRegistration();
              return { ok: !!reg, reason: reg ? 'registered' : 'no_registration' };
            }"""
        )
        result["service_worker"] = sw_ok
        manifest_ok = page.evaluate(
            """() => {
              const link = document.querySelector('link[rel="manifest"]');
              return { ok: !!link, href: link ? link.getAttribute('href') : null };
            }"""
        )
        result["manifest_link"] = manifest_ok
        context.set_offline(True)
        try:
            page.reload(wait_until="domcontentloaded", timeout=timeout_ms)
            offline_text = page.content()
            offline_markers = all(m in offline_text for m in MARKERS)
            result["offline_reload"] = {
                "ok": offline_markers,
                "note": "sw_has_no_fetch_handler; pass if bfcache/http cache serves shell",
            }
        except Exception as exc:  # noqa: BLE001
            result["offline_reload"] = {
                "ok": False,
                "error": str(exc)[:200],
                "note": "expected_possible_when_no_fetch_cache",
            }
        browser.close()
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default=OPS_URL)
    parser.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--timeout-ms", type=int, default=45000)
    parser.add_argument("--strict", action="store_true", help="Require offline_reload.ok")
    parser.add_argument("--skip-playwright", action="store_true")
    args = parser.parse_args()

    urllib_steps = urllib_probe()
    pw = {"skipped": True, "reason": "skip_playwright_flag"} if args.skip_playwright else playwright_scenario(args.url, args.timeout_ms)

    urllib_ok = all(v.get("ok") for v in urllib_steps.values() if isinstance(v, dict))
    online_ok = pw.get("online_markers_ok", urllib_steps.get("ops_online", {}).get("ok", False))
    sw_ok = pw.get("service_worker", {}).get("ok") if isinstance(pw.get("service_worker"), dict) else None
    offline_ok = pw.get("offline_reload", {}).get("ok") if isinstance(pw.get("offline_reload"), dict) else None

    warnings: list[str] = []
    if sw_ok is False:
        warnings.append("service_worker_not_registered_in_session")
    if offline_ok is False:
        warnings.append("offline_reload_failed_expected_without_fetch_cache")

    if args.strict:
        core_ok = urllib_ok and bool(online_ok) and sw_ok is True and offline_ok is True
    else:
        core_ok = urllib_ok and bool(online_ok)

    report = {
        "schema": "personadiary_offline_pwa_scenario_v1",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tier": "B",
        "url": args.url,
        "urllib": urllib_steps,
        "playwright": pw,
        "sw_design_note": "public/personadiary/sw.js is installability shell only (no fetch cache)",
        "warnings": warnings,
        "ok": core_ok,
        "mode": "strict" if args.strict else "warn",
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.out_json}")
    return 0 if core_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
