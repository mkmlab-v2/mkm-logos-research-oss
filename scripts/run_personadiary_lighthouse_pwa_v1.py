#!/usr/bin/env python3
"""PersonaDiary PWA Lighthouse gate (tier_0 · live URL · no API credits)."""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_URL = "https://personadiary.com/ops"
DEFAULT_OUT = ROOT / "reports/personadiary_lighthouse_pwa_latest.json"
DEFAULT_RAW = ROOT / "reports/personadiary_lighthouse_pwa_raw_latest.json"
MANIFEST_URL = "https://personadiary.com/personadiary/manifest.webmanifest"
SW_URL = "https://personadiary.com/personadiary/sw.js"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _score(categories: dict, key: str) -> float | None:
    cat = categories.get(key) or {}
    raw = cat.get("score")
    if raw is None:
        return None
    try:
        return round(float(raw) * 100.0, 1)
    except (TypeError, ValueError):
        return None


def _audit_pass(audits: dict, audit_id: str) -> bool | None:
    audit = audits.get(audit_id) or {}
    val = audit.get("score")
    if val is None:
        return None
    try:
        return float(val) >= 0.9
    except (TypeError, ValueError):
        return None


def evaluate_report(
    report: dict,
    *,
    pwa_min: float,
    a11y_min: float,
    perf_min: float,
    pwa_proxy_ok: bool | None = None,
) -> tuple[bool, list[str]]:
    categories = report.get("categories") or {}
    audits = report.get("audits") or {}
    pwa = _score(categories, "pwa")
    a11y = _score(categories, "accessibility")
    perf = _score(categories, "performance")
    errors: list[str] = []
    if pwa is None:
        if pwa_proxy_ok is False:
            errors.append("pwa_proxy_fail:manifest_or_sw")
        elif pwa_proxy_ok is None:
            errors.append("missing_pwa_score")
    elif pwa < pwa_min:
        errors.append(f"pwa_below_min:{pwa}<{pwa_min}")
    if a11y is None:
        errors.append("missing_accessibility_score")
    elif a11y < a11y_min:
        errors.append(f"a11y_below_min:{a11y}<{a11y_min}")
    if perf is None:
        errors.append("missing_performance_score")
    elif perf < perf_min:
        errors.append(f"perf_below_min:{perf}<{perf_min}")
    installable = _audit_pass(audits, "installable-manifest")
    sw_registered = _audit_pass(audits, "service-worker")
    if installable is False:
        errors.append("audit_installable_manifest_fail")
    if sw_registered is False:
        errors.append("audit_service_worker_fail")
    return len(errors) == 0, errors


def urllib_pwa_proxy(timeout: int = 20) -> dict:
    out: dict = {}
    ok = True
    for name, url in (("manifest", MANIFEST_URL), ("service_worker", SW_URL)):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "MKM-PersonadiaryLHCI/1.0"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                body = resp.read()
            out[name] = {"ok": resp.status == 200 and len(body) > 20, "status": resp.status, "bytes": len(body)}
        except Exception as exc:  # noqa: BLE001
            out[name] = {"ok": False, "error": str(exc)[:160]}
        ok = ok and bool(out[name].get("ok"))
    out["ok"] = ok
    return out


def run_lighthouse(url: str, raw_path: Path, timeout_sec: int) -> dict:
    if not shutil.which("node"):
        return {"ok": False, "error": "node_not_found", "hint": "Install Node.js for npx lighthouse"}
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    out_path = str(raw_path).replace("\\", "/")
    base = [
        "npx",
        "--yes",
        "lighthouse@12.6.0",
        url,
        "--output=json",
        f"--output-path={out_path}",
        "--quiet",
        "--only-categories=pwa,performance,accessibility",
        '--chrome-flags=--headless --no-sandbox --disable-gpu',
    ]
    if sys.platform == "win32":
        cmd_str = subprocess.list2cmdline(base)
        proc = subprocess.run(
            cmd_str,
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=timeout_sec,
            shell=True,
        )
    else:
        proc = subprocess.run(base, cwd=ROOT, capture_output=True, text=True, timeout=timeout_sec)
    if proc.returncode != 0 and not raw_path.is_file():
        return {
            "ok": False,
            "exit_code": proc.returncode,
            "stderr": (proc.stderr or "")[-1500:],
            "stdout": (proc.stdout or "")[-500:],
        }
    if not raw_path.is_file():
        return {"ok": False, "error": "lighthouse_json_missing", "exit_code": proc.returncode}
    try:
        report = json.loads(raw_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return {"ok": False, "error": f"lighthouse_json_invalid:{exc}"}
    return {"ok": True, "report": report, "exit_code": proc.returncode}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default=os.getenv("MKM_PERSONADIARY_LHCI_URL", DEFAULT_URL))
    parser.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--raw-json", type=Path, default=DEFAULT_RAW)
    parser.add_argument("--timeout", type=int, default=180)
    parser.add_argument("--pwa-min", type=float, default=float(os.getenv("MKM_PERSONADIARY_LHCI_PWA_MIN", "55")))
    parser.add_argument("--a11y-min", type=float, default=float(os.getenv("MKM_PERSONADIARY_LHCI_A11Y_MIN", "82")))
    parser.add_argument("--perf-min", type=float, default=float(os.getenv("MKM_PERSONADIARY_LHCI_PERF_MIN", "45")))
    parser.add_argument("--strict", action="store_true", help="Fail on threshold miss (default: warn only)")
    args = parser.parse_args()

    with tempfile.TemporaryDirectory(prefix="pd_lhci_") as tmp:
        raw = Path(tmp) / "lh.json"
        run = run_lighthouse(args.url, raw, args.timeout)
        if not run.get("ok"):
            out = {
                "schema": "personadiary_lighthouse_pwa_v1",
                "generated_at_utc": _utc_now(),
                "research_only": True,
                "url": args.url,
                "ok": False,
                "errors": [run.get("error") or "lighthouse_failed"],
                "run": {k: v for k, v in run.items() if k != "report"},
            }
            args.out_json.parent.mkdir(parents=True, exist_ok=True)
            args.out_json.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print(f"WROTE: {args.out_json}")
            return 1

        report = run["report"]
        args.raw_json.parent.mkdir(parents=True, exist_ok=True)
        args.raw_json.write_text(json.dumps(report, ensure_ascii=False), encoding="utf-8")

        pwa_proxy = urllib_pwa_proxy()
        pass_ok, errors = evaluate_report(
            report,
            pwa_min=args.pwa_min,
            a11y_min=args.a11y_min,
            perf_min=args.perf_min,
            pwa_proxy_ok=pwa_proxy.get("ok"),
        )
        categories = report.get("categories") or {}
        summary = {
            "schema": "personadiary_lighthouse_pwa_v1",
            "generated_at_utc": _utc_now(),
            "research_only": True,
            "hypothesis_tier": "B",
            "url": args.url,
            "scores": {
                "pwa": _score(categories, "pwa"),
                "accessibility": _score(categories, "accessibility"),
                "performance": _score(categories, "performance"),
            },
            "pwa_proxy": pwa_proxy,
            "thresholds": {
                "pwa_min": args.pwa_min,
                "a11y_min": args.a11y_min,
                "perf_min": args.perf_min,
            },
            "raw_path": str(args.raw_json.relative_to(ROOT)),
            "ok": pass_ok if args.strict else True,
            "threshold_pass": pass_ok,
            "errors": errors,
            "mode": "strict" if args.strict else "warn",
        }
        if args.strict and not pass_ok:
            summary["ok"] = False

        args.out_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"WROTE: {args.out_json}")
        if args.strict and not pass_ok:
            return 1
        if not pass_ok:
            print(f"WARN: thresholds missed: {errors}", file=sys.stderr)
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
