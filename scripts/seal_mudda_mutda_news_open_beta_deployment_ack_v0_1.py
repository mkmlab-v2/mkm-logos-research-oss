#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Seal COMMANDER_MUTDA_NEWS_OPEN_BETA_DEPLOYMENT_ACK.

Lifts mutda.ai defensive park for MUTDA News OPEN_BETA only.
Does NOT authorize paid ads, mainline redirect, Product DONE, or Decision OS superiority.

  py scripts/seal_mudda_mutda_news_open_beta_deployment_ack_v0_1.py
  py scripts/check_mudda_mutda_news_open_beta_deployment_ack_v0_1.py
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/final/artifacts"
OUT = ART / "mudda_mutda_news_open_beta_deployment_ack_v0_1_latest.json"
APPROVAL = ROOT / "reports" / "delegation_mutda_news_open_beta_approval_map_v0_1_latest.json"
ZONE_REG = ART / "mkm_cloudflare_zone_registry_v1.json"
PORTFOLIO = ROOT / "docs/final/MKM_DOMAIN_PORTFOLIO_POINTER_V1.md"
RECEIPT = ART / "mudda_mutda_ai_defensive_domain_registration_receipt_v0_1_latest.json"
SERIES_FMT = ART / "mkm_mutda_series_format_v1_latest.json"
OUT_DIR = ROOT / "docs/research/mudda/mutda_news_open_beta_v0_1"


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _write(path: Path, doc: dict) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(doc, ensure_ascii=False, indent=2) + "\n"
    path.write_bytes(text.encode("utf-8"))
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def main() -> int:
    now = _utc()
    doc = {
        "schema": "mudda.mutda_news_open_beta_deployment_ack.v0_1",
        "generated_at_utc": now,
        "commander_ack": "COMMANDER_MUTDA_NEWS_OPEN_BETA_DEPLOYMENT_ACK",
        "MISSION": "MKM_MUTDA_NEWS_OPEN_BETA_V1",
        "DELEGATION": "HIGH",
        "status": "ACK_SEALED_OPEN_BETA_AUTHORIZED",
        "PURPOSE": "mutda_news_open_beta_public_entry_only",
        "prior_policy": "mutda.ai=DEFENSIVE_PARK",
        "override": {
            "type": "NARROW_OPEN_BETA_DEPLOY_OVERRIDE",
            "reason_ko": (
                "지휘관 HIGH_DELEGATION ACK로 방어파크 해제. "
                "첫 공개 제품=묻다뉴스만. 기존 본선 대체·리다이렉트 금지."
            ),
        },
        "GOAL": [
            "mutda.ai 방어파크 → OPEN_BETA 입구",
            "첫 공개 제품 = MUTDA News only",
            "a-codeai / jema-ai / mkmlife / logos 본선 유지",
            "MUTDA가 기존 제품을 대체하거나 redirect하지 않음",
        ],
        "AUTHORIZED": [
            "mutda_ai_dns_connect",
            "cloudflare_proxy_tls",
            "minimal_worker_pages_origin_routing",
            "frontend_minimal_shell",
            "build_test_dev_smoke",
            "production_deploy_mutda_ai",
            "public_open_beta_url",
            "rollback",
            "health_checker",
            "open_beta_badge",
            "analytics_minimal_non_pii",
            "robots_sitemap_og",
            "ep01_publish_on_mutda_news",
            "manual_curated_articles",
        ],
        "NOT_AUTHORIZED": [
            "paid_ads",
            "auto_bulk_news_scraping_publishing",
            "paid_checkout",
            "auto_send_notify",
            "redirect_acodeai_jema_mkmlife_logos_to_mutda",
            "retire_mainline_brands",
            "decision_os_superiority_claim",
            "mdi_predictive_claim",
            "political_correct_answer_generation",
            "product_done",
            "friend_ready_claim",
            "market_validation_pass",
            "unbiased_news_front_claim",
            "unverified_superlative_copy",
        ],
        "OPEN_BETA_SURFACE": {
            "/": "MUTDA brand + tagline",
            "/news": "묻다뉴스",
            "/news/ep01": "sealed EP01",
            "/ask": "EP01 Ask seed beta entry",
            "/about": "주식회사 목소리네트워크 · MKM LAB 후순위",
        },
        "MUTDA_NEWS_CONTRACT": "FACT → CAUSE → LENS → DECISION",
        "REQUIRED": [
            "provenance_source",
            "fact_inference_split",
            "unknown_preserve",
            "lens_non_gating",
            "human_final_judgment",
            "no_hype_copy",
            "no_unbiased_news_claim",
            "no_unverified_superlatives",
        ],
        "SUCCESS_CRITERIA": [
            "https://mutda.ai reachable",
            "/news ok",
            "EP01 render ok",
            "mobile_desktop_smoke",
            "tls_pass",
            "mainline_unaffected",
            "public_copy_fact_lock_pass",
            "rollback_receipt_exists",
        ],
        "FINAL_STATUS_ALLOWED": ["OPEN_BETA_READY", "OPEN_BETA_LIVE"],
        "PRODUCT_DONE": False,
        "FRIEND_READY": False,
        "MARKET_VALIDATION": "NOT_ESTABLISHED",
        "send_gate": "HOLD",
        "IF_MUTDA_APP_NOT_FOUND": {
            "create_giant_product": False,
            "create_minimal_open_beta_shell": True,
            "consume_sealed_format_ep01": True,
            "suggested_path": "projects/mutda-news-open-beta-v1",
        },
        "labels": {
            "MUTDA_DOMAIN": "OPEN_BETA_AUTHORIZED",
            "MASTER_BRAND": "HYPOTHESIS",
            "CURRENT_MAINLINE_REPLACEMENT": False,
            "DEPLOY": True,
            "ADS": False,
            "WORKER": "MINIMAL_AUTHORIZED",
        },
        "NEXT": "PREFLIGHT_THEN_MINIMAL_SHELL_THEN_DEPLOY",
        "next_auto_issue": True,
    }
    sha = _write(OUT, doc)

    approval = {
        "schema": "mkm.delegation_approval_map.v0_1",
        "generated_at_utc": now,
        "mission": "MKM_MUTDA_NEWS_OPEN_BETA_V1",
        "scale": "L",
        "lane": "design",
        "commander_ack": "COMMANDER_MUTDA_NEWS_OPEN_BETA_DEPLOYMENT_ACK",
        "ack_artifact": str(OUT.relative_to(ROOT)).replace("\\", "/"),
        "delegation_status": "AUTHORIZED_OPEN_BETA_DEPLOY",
        "auto_nodes": [
            "preflight_disk_cf",
            "scaffold_minimal_shell",
            "build_test_local_smoke",
            "cf_worker_assets_deploy",
            "dns_route_mutda_ai",
            "live_smoke_health",
            "rollback_receipt",
            "portfolio_pointer_update",
        ],
        "stop_nodes": [
            "paid_ads",
            "bulk_auto_scrape_publish",
            "checkout",
            "redirect_mainline_to_mutda",
            "product_done_claim",
            "send_external_blast",
        ],
        "auto_pending": [],
        "human_stop_before": [],
        "note_ko": "외부 배포는 본 ACK로 EXTERNAL_ACTION 범위 내 허용(묻다뉴스 OPEN_BETA만).",
    }
    _write(APPROVAL, approval)

    if ZONE_REG.is_file():
        zreg = json.loads(ZONE_REG.read_text(encoding="utf-8"))
        for z in zreg.get("zones") or []:
            if z.get("name") == "mutda.ai":
                z["mkm_role"] = "mutda_news_open_beta"
                z["park_policy"] = "lifted_by_open_beta_ack"
                z["open_beta_ack"] = str(OUT.relative_to(ROOT)).replace("\\", "/")
        zreg["generated_at_utc"] = now
        _write(ZONE_REG, zreg)

    if SERIES_FMT.is_file():
        fmt = json.loads(SERIES_FMT.read_text(encoding="utf-8"))
        hs = fmt.setdefault("host_surface", {})
        hs["mutda_ai_domain"] = "OPEN_BETA_AUTHORIZED"
        hs["mutda_ai_public_deploy"] = "OPEN_BETA_NEWS_ONLY"
        walls = fmt.setdefault("walls", {})
        walls["mutda_ai_public_deploy"] = "OPEN_BETA_NEWS_ONLY"
        walls["news_portal"] = "FORBIDDEN_FULL_PORTAL"
        walls["mainline_redirect"] = "FORBIDDEN"
        fmt["PRODUCT_DONE"] = False
        fmt["send_gate"] = "HOLD"
        _write(SERIES_FMT, fmt)

    if RECEIPT.is_file():
        rec = json.loads(RECEIPT.read_text(encoding="utf-8"))
        rec["open_beta_override_ack"] = str(OUT.relative_to(ROOT)).replace("\\", "/")
        rec["park_status"] = "LIFTED_FOR_OPEN_BETA_NEWS_ONLY"
        _write(RECEIPT, rec)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    _write(OUT_DIR / "MUTDA_NEWS_OPEN_BETA_DEPLOYMENT_ACK_V0_1.json", doc)

    print(
        json.dumps(
            {
                "ok": True,
                "commander_ack": doc["commander_ack"],
                "MISSION": doc["MISSION"],
                "PRODUCT_DONE": False,
                "send_gate": "HOLD",
                "sha256": sha,
                "artifact": str(OUT.relative_to(ROOT)).replace("\\", "/"),
                "approval_map": str(APPROVAL.relative_to(ROOT)).replace("\\", "/"),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
