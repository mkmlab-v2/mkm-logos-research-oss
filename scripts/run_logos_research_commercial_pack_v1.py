#!/usr/bin/env python3
"""Logos research commercial pack — Phase O metrics + product manifest + no1kmedi sync."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
OUT_MANIFEST = ROOT / "docs/final/artifacts/logos_research_commercial_product_v1_latest.json"
OUT_RUN = ROOT / "reports/logos_research_commercial_pack_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(name: str, cmd: list[str], *, timeout: int = 600) -> dict[str, Any]:
    t0 = time.perf_counter()
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=timeout)
    return {
        "name": name,
        "cmd": cmd,
        "exit_code": proc.returncode,
        "elapsed_sec": round(time.perf_counter() - t0, 2),
        "stdout_tail": (proc.stdout or "")[-300:],
        "ok": proc.returncode == 0,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--skip-phase-o", action="store_true")
    ap.add_argument("--skip-lexicon-audit", action="store_true")
    args = ap.parse_args()

    steps: list[dict[str, Any]] = []
    if not args.skip_phase_o:
        steps.append(_run("phase_o", [PY, "scripts/run_logos_track_b_phase_o_v1.py"], timeout=900))
    steps.append(_run("product_metrics", [PY, "scripts/build_logos_research_product_metrics_v1.py"]))
    if not args.skip_lexicon_audit:
        steps.append(
            _run(
                "lexicon_4d_research_audit",
                [PY, "scripts/run_logos_lexicon_4d_research_audit_v1.py", "--skip-phase-pa"],
            )
        )

    metrics_path = ROOT / "reports/logos_research_product_metrics_v1_latest.json"
    metrics = json.loads(metrics_path.read_text(encoding="utf-8-sig")) if metrics_path.is_file() else {}

    manifest = {
        "schema": "logos_research_commercial_product_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "non_gating": True,
        "research_only": True,
        "public_domain": "logos.jema-ai.com",
        "canonical_origin": "https://logos.jema-ai.com",
        "hub_integration": {
            "brand_hub": "https://jema-ai.com",
            "hub_link_key": "research_logos",
            "apex_redirect": "jema-ai.com/logos-research → 308 logos.jema-ai.com",
        },
        "product_skus": [
            {"id": "demo", "billing": "free_quota", "audience": "public_lead"},
            {"id": "pro", "billing": "subscription", "audience": "individual_researcher"},
            {"id": "institution", "billing": "annual_seats", "audience": "seminary_university_publisher"},
        ],
        "forbidden": [
            "theology_doctrine_sale",
            "track_a_bridge",
            "live_trading_bridge",
            "ms_headline_merge",
            "investment_advice_copy",
        ],
        "implementation": {
            "next_page": "projects/no1kmedi/src/app/logos-research/page.tsx",
            "copy_json": "projects/no1kmedi/marketing-site/logos-research-copy.json",
            "metrics_json": "projects/no1kmedi/public/data/logos_research_product_metrics_v1.json",
            "middleware": "projects/no1kmedi/src/middleware.ts (LOGOS_HOSTS)",
        },
        "dns_note": "Cloudflare jema-ai.com zone: CNAME logos → same origin as app.jema-ai.com (farm pattern).",
        "metrics_snapshot": metrics.get("metrics") or {},
        "reproduce": "py scripts/run_logos_research_commercial_pack_v1.py",
    }
    OUT_MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    OUT_MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    overall_ok = all(s.get("ok") for s in steps)
    run_doc = {
        "schema": "logos_research_commercial_pack_v1",
        "generated_at_utc": _utc(),
        "ok": overall_ok,
        "manifest": str(OUT_MANIFEST.relative_to(ROOT)).replace("\\", "/"),
        "steps": steps,
    }
    OUT_RUN.parent.mkdir(parents=True, exist_ok=True)
    OUT_RUN.write_text(json.dumps(run_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": overall_ok, "manifest": str(OUT_MANIFEST), "out": str(OUT_RUN)}, ensure_ascii=False))
    return 0 if overall_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
