#!/usr/bin/env python3
"""Nebius console post-login setup probe (CDP). Billing card = Tier-3 human only."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

OUT = ROOT / "reports/nvidia_nebius_console_setup_latest.json"
PROJECT_URL = "https://console.nebius.com/project-e00cq6bepr00aphrjtdpzf"
BILLING_PAYMENTS = "/tenant-e00fe2zhs67gmz6wha/billing/payments"
BILLING_USAGE = "/tenant-e00fe2zhs67gmz6wha/billing/consumption"
LIMITS = "/limits"


def _click_text(page, *labels: str) -> str | None:
    for label in labels:
        for loc in (
            page.get_by_role("link", name=label, exact=False),
            page.get_by_role("button", name=label, exact=False),
            page.get_by_text(label, exact=False),
        ):
            try:
                el = loc.first
                if el.count() and el.is_visible(timeout=2000):
                    el.click(timeout=8000)
                    return label
            except Exception:
                continue
    return None


def _body_hints(text: str) -> dict:
    low = text.lower()
    return {
        "billing_setup_needed": any(
            k in low
            for k in (
                "add payment",
                "payment method",
                "결제",
                "카드",
                "billing setup",
                "청구",
                "connect card",
            )
        ),
        "payment_configured": any(
            k in low
            for k in (
                "payment method added",
                "card ending",
                "default payment",
                "paid",
                "balance",
                "$25",
                "active",
                "customer-",
            )
        ),
        "onboarding_visible": "onboarding" in low or "온보딩" in text,
    }


def main() -> int:
    from playwright.sync_api import sync_playwright

    run: dict = {
        "project_url": PROJECT_URL,
        "project_id": "project-e00cq6bepr00aphrjtdpzf",
        "region": "eu-north1",
        "tenant": "amber-rat-tenant-5cf",
        "setup_ok": False,
    }

    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
        page = next(
            (pg for pg in browser.contexts[0].pages if "console.nebius.com" in (pg.url or "")),
            None,
        )
        if page is None:
            page = browser.contexts[0].new_page()
            page.goto(PROJECT_URL, wait_until="domcontentloaded", timeout=120_000)
        page.bring_to_front()
        page.wait_for_timeout(4000)
        run["console_title"] = page.title()
        home_text = page.inner_text("body", timeout=12000) or ""
        run["home_hints"] = _body_hints(home_text)

        # Onboarding course banner
        clicked = _click_text(
            page,
            "Get started on the course",
            "Nebius AI Cloud Onboarding Course",
            "온보딩 코스를 시작하세요",
            "온보딩",
        )
        if clicked:
            page.wait_for_timeout(4000)
            run["onboarding_clicked"] = clicked
            run["onboarding_url"] = page.url[:250]
            if page.url != PROJECT_URL:
                page.go_back(wait_until="domcontentloaded", timeout=60_000)
                page.wait_for_timeout(2000)

        # Billing → Payments
        pay = _click_text(page, "Payments", "결제", "Manage billing", "Billing")
        if not pay:
            page.goto(f"https://console.nebius.com{BILLING_PAYMENTS}", wait_until="domcontentloaded", timeout=120_000)
        else:
            page.wait_for_timeout(3000)
        run["billing_nav"] = pay or "direct_url"
        run["billing_url"] = page.url[:250]
        billing_text = page.inner_text("body", timeout=12000) or ""
        run["billing_snippet"] = billing_text[:800].replace("\n", " | ")
        hints = _body_hints(billing_text)
        run.update({f"billing_{k}": v for k, v in hints.items()})

        try:
            from scripts.run_web_ops_regime_cdp_probe_v1 import (
                capture_observation_from_playwright_page,
                write_live_observation_json,
            )

            live_obs = capture_observation_from_playwright_page(
                page,
                human_gate=run.get("human_gate"),
                extra_hints=hints,
            )
            live_path = write_live_observation_json(live_obs)
            run["web_ops_live_observation"] = str(live_path.relative_to(ROOT)).replace("\\", "/")
        except Exception as exc:
            run["web_ops_live_observation_error"] = str(exc)[:200]

        if hints.get("billing_setup_needed") and not hints.get("payment_configured"):
            run["human_gate"] = "nebius_payment_card_tier3"
            run["hint"] = (
                "Payments 화면에서 카드 연결 ($25 최소 입금). "
                "카드 번호는 지휘관이 직접 입력 — 에이전트 불가."
            )

        # Limits
        page.goto(f"https://console.nebius.com{LIMITS}", wait_until="domcontentloaded", timeout=120_000)
        page.wait_for_timeout(3000)
        limits_text = page.inner_text("body", timeout=12000) or ""
        run["limits_url"] = page.url[:250]
        for gpu in ("H200", "H100", "L40S"):
            if gpu in limits_text:
                run.setdefault("gpu_limits_mentioned", []).append(gpu)
        m = re.search(r"H100[^\d]*(\d+)", limits_text)
        if m:
            run["h100_limit_hint"] = m.group(0)[:40]

        run["setup_ok"] = bool(run.get("payment_configured")) or (
            not run.get("human_gate") and "default-project" in (run.get("console_title") or "")
        )

        shot = ROOT / "reports/nvidia_nebius_console_setup_latest.png"
        page.goto(PROJECT_URL, wait_until="domcontentloaded", timeout=120_000)
        page.wait_for_timeout(2000)
        try:
            page.screenshot(path=str(shot), full_page=True, timeout=25_000)
            run["screenshot"] = str(shot.relative_to(ROOT)).replace("\\", "/")
        except Exception:
            pass

    OUT.write_text(json.dumps(run, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    try:
        import subprocess

        bundle_rc = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts/run_web_ops_regime_full_bundle_v1.py"),
                "--skip-live-cdp",
                "--skip-azure",
            ],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
        )
        run["web_ops_regime_bundle_rc"] = bundle_rc.returncode
        if bundle_rc.stdout.strip():
            run["web_ops_regime_bundle_stdout"] = bundle_rc.stdout.strip()[-500:]
        gate_path = ROOT / "reports/web_ops_regime_gate_v1_latest.json"
        if gate_path.is_file():
            gate_doc = json.loads(gate_path.read_text(encoding="utf-8-sig"))
            run["web_ops_regime_gate"] = str(gate_path.relative_to(ROOT)).replace("\\", "/")
            run["web_ops_final_action"] = gate_doc["conflict_resolver"]["worst_final_action"]
            run["web_ops_gate_pass"] = gate_doc.get("gate_pass")
        OUT.write_text(json.dumps(run, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    except Exception as exc:
        run["web_ops_regime_gate_error"] = str(exc)[:200]

    print(json.dumps(run, ensure_ascii=False, indent=2))
    return 0 if run.get("setup_ok") and not run.get("human_gate") else 1


if __name__ == "__main__":
    raise SystemExit(main())
