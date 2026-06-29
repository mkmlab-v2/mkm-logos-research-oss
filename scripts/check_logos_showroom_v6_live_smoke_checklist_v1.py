#!/usr/bin/env python3
"""v6 showroom live smoke checklist — HTTP fetch api.jemaai.cloud ([HYPO], optional network)."""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_URLS = ROOT / "docs/final/artifacts/jemaai_showroom_public_urls_v1_latest.json"
DEFAULT_OUT = ROOT / "reports/logos_showroom_v6_live_smoke_checklist_v1_latest.json"

TIMEOUT_SEC = 25


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _fetch(url: str) -> tuple[int, str]:
    req = urllib.request.Request(url, headers={"User-Agent": "MKM-ShowroomSmoke/1.0"})
    with urllib.request.urlopen(req, timeout=TIMEOUT_SEC) as resp:
        body = resp.read().decode("utf-8", errors="replace")
        return int(resp.status), body


def _load_urls(path: Path) -> dict[str, Any]:
    doc = json.loads(path.read_text(encoding="utf-8-sig"))
    pages = doc.get("pages") or {}
    v6 = pages.get("logos_oracle_v6") or {}
    base = (doc.get("hosts") or {}).get("static_showroom_demo_primary") or "https://api.jemaai.cloud"
    html_url = v6.get("api_mirror") or f"{base.rstrip('/')}/public_showroom_logos_oracle_v6.html"
    presets_url = f"{base.rstrip('/')}/showroom_meaning_topology_qa_presets_v1.json"
    return {"html_url": html_url, "presets_url": presets_url}


def run_check(*, urls_doc: Path, skip_network: bool) -> dict[str, Any]:
    targets = _load_urls(urls_doc)
    failures: list[str] = []
    checks: dict[str, Any] = {"targets": targets, "network_skipped": skip_network}

    if skip_network:
        checks["status"] = "SKIPPED"
        return {
            "schema": "logos_showroom_v6_live_smoke_checklist_v1",
            "generated_at_utc": _utc(),
            "research_only": True,
            "send_gate": "HOLD",
            "ok": True,
            "gate_pass": True,
            "gate_failures": [],
            "checks": checks,
            "manual_steps_ko": [
                "브라우저: api_mirror v6 URL 열기",
                "질문: 우주 창조의 원리 → genesis era 하이라이트",
                "무관 질문 → abstention 카피, Dan.2 하이라이트 없음",
            ],
            "reproducible_command": "py scripts/check_logos_showroom_v6_live_smoke_checklist_v1.py",
        }

    html_status = 0
    presets_status = 0
    try:
        html_status, html = _fetch(targets["html_url"])
        checks["html_status"] = html_status
        checks["html_has_matchPreset"] = "function matchPreset" in html
        checks["html_has_abstention_path"] = "abstention" in html or "fallback" in html
        if html_status != 200:
            failures.append(f"html status {html_status}")
        if "public_showroom_logos_oracle_v6" not in html and "matchPreset" not in html:
            failures.append("html does not look like v6 oracle")
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        failures.append(f"html fetch failed: {e}")

    try:
        presets_status, presets_raw = _fetch(targets["presets_url"])
        checks["presets_status"] = presets_status
        presets = json.loads(presets_raw)
        fb = presets.get("fallback") or {}
        checks["remote_fallback_abstention"] = fb.get("abstention") is True
        checks["remote_fallback_empty_highlights"] = not (fb.get("highlight_node_ids") or [])
        genesis = next(
            (p for p in (presets.get("presets") or []) if p.get("id") == "era_genesis_order_and_fall"),
            None,
        )
        if genesis:
            kws = [str(x) for x in (genesis.get("keywords") or [])]
            checks["remote_genesis_keywords_sample"] = kws[:8]
            checks["remote_genesis_has_우주"] = any("우주" in k for k in kws)
        else:
            failures.append("remote presets missing era_genesis_order_and_fall")
        if fb.get("abstention") is not True:
            failures.append("remote fallback abstention false")
        if presets_status != 200:
            failures.append(f"presets status {presets_status}")
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as e:
        failures.append(f"presets fetch/parse failed: {e}")

    ok = len(failures) == 0
    checks["status"] = "PASS" if ok else "FAIL"
    return {
        "schema": "logos_showroom_v6_live_smoke_checklist_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "send_gate": "HOLD",
        "ok": ok,
        "gate_pass": ok,
        "gate_failures": failures,
        "checks": checks,
        "reproducible_command": "py scripts/check_logos_showroom_v6_live_smoke_checklist_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--urls-json", type=Path, default=DEFAULT_URLS)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--skip-network", action="store_true", help="Emit checklist only; no HTTP")
    args = ap.parse_args()
    if not args.urls_json.is_file():
        print(f"missing urls: {args.urls_json}", file=sys.stderr)
        return 2
    doc = run_check(urls_doc=args.urls_json, skip_network=args.skip_network)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc["ok"], "gate_failures": doc["gate_failures"], "out": str(args.output)}, ensure_ascii=False))
    return 0 if doc["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
