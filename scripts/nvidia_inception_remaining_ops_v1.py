#!/usr/bin/env python3
"""Post-billing remaining Inception ops — read-only / free only (no GPU, no new charges).

  py scripts/nvidia_inception_remaining_ops_v1.py
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

OUT = ROOT / "reports/nvidia_inception_remaining_ops_latest.json"
NEBIUS_PAYMENTS = "https://console.nebius.com/tenant-e00fe2zhs67gmz6wha/billing/payments"
PHOENIX_BENEFITS = "https://programs.nvidia.com/phoenix/benefits"
AZURE_STARTUPS = (
    "https://portal.azure.com/#view/Microsoft_Azure_Startups/"
    "AzureForStartups.ReactView/skipWizardRedirect~/true"
)

# Never click these (cost guard)
COST_BLOCK_TEXT = (
    "create instance",
    "run job",
    "add card",
    "save billing details",
    "top up",
    "deploy",
    "start cluster",
)


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _safe_text(page, timeout: int = 10_000) -> str:
    try:
        return page.inner_text("body", timeout=timeout) or ""
    except Exception:
        return ""


def _probe_nebius(page) -> dict[str, Any]:
    out: dict[str, Any] = {"step": "nebius_billing_verify", "cost": 0}
    page.goto(NEBIUS_PAYMENTS, wait_until="domcontentloaded", timeout=120_000)
    page.wait_for_timeout(4000)
    text = _safe_text(page)
    out["url"] = page.url[:200]
    if re.search(r"\$25\.?0{0,2}", text):
        out["balance_usd"] = 25.0
        out["billing_active"] = "Active" in text
    m = re.search(r"Balance\s*\$?([\d,.]+)", text, re.I)
    if m:
        try:
            out["balance_usd"] = float(m.group(1).replace(",", ""))
        except ValueError:
            pass
    out["customer_id"] = None
    cid = re.search(r"customer-[a-z0-9]+", text, re.I)
    if cid:
        out["customer_id"] = cid.group(0)
    out["payment_ok"] = bool(out.get("billing_active")) and (out.get("balance_usd") or 0) >= 0
    out["blocked_action"] = "GPU instances / jobs — skipped (cost guard)"
    shot = ROOT / "reports/nvidia_nebius_payments_verify_latest.png"
    page.screenshot(path=str(shot), full_page=True, timeout=25_000)
    out["screenshot"] = str(shot.relative_to(ROOT)).replace("\\", "/")
    return out


def _probe_phoenix(page) -> dict[str, Any]:
    out: dict[str, Any] = {"step": "phoenix_benefits_scrape", "cost": 0}
    page.goto(PHOENIX_BENEFITS, wait_until="domcontentloaded", timeout=120_000)
    page.wait_for_timeout(4000)
    out["url"] = page.url[:200]
    out["logged_in"] = "login" not in page.url.lower()
    text = _safe_text(page)
    rows: list[dict[str, str]] = []
    for line in text.splitlines():
        line = line.strip()
        if not line or len(line) < 8:
            continue
        if any(
            k in line
            for k in (
                "AWS",
                "Google",
                "Lambda",
                "Nebius",
                "Azure",
                "Innovation Lab",
                "Requested",
                "Available",
                "Approved",
                "Pending",
            )
        ):
            rows.append({"line": line[:120]})
    out["benefit_lines"] = rows[:30]
    for partner in ("AWS", "Google", "Lambda", "Nebius", "Azure", "Innovation Lab"):
        if partner.lower() in text.lower():
            out.setdefault("partners_mentioned", []).append(partner)
    if "Requested" in text:
        out["has_requested_section"] = True
    shot = ROOT / "reports/nvidia_phoenix_benefits_probe_latest.png"
    page.screenshot(path=str(shot), full_page=True, timeout=25_000)
    out["screenshot"] = str(shot.relative_to(ROOT)).replace("\\", "/")
    return out


def _probe_azure(page) -> dict[str, Any]:
    out: dict[str, Any] = {"step": "azure_founders_probe", "cost": 0}
    page.goto(AZURE_STARTUPS, wait_until="domcontentloaded", timeout=120_000)
    page.wait_for_timeout(6000)
    out["url"] = page.url[:200]
    text = _safe_text(page, timeout=15_000)
    out["logged_in"] = "moksorinw@gmail.com" in text or "onmicrosoft.com" in text.lower()
    if "LinkedIn" in text:
        out["linkedin_verification_required"] = True
        out["human_gate"] = "linkedin_tier3"
    m = re.search(r"\$[\d,]+", text)
    if m:
        out["credits_tier_seen"] = m.group(0)
    out["snippet"] = text[:500].replace("\n", " | ")
    shot = ROOT / "reports/nvidia_azure_founders_probe_latest.png"
    page.screenshot(path=str(shot), full_page=True, timeout=25_000)
    out["screenshot"] = str(shot.relative_to(ROOT)).replace("\\", "/")
    return out


def main() -> int:
    from playwright.sync_api import sync_playwright

    run: dict[str, Any] = {
        "schema": "nvidia_inception_remaining_ops_v1",
        "generated_at_utc": _utc(),
        "cost_policy": {
            "no_gpu_spinup": True,
            "no_new_billing_charges": True,
            "no_nim_paid_inference": True,
            "nebius_prepaid_only": "use existing $25 balance only when commander approves compute",
        },
        "steps": [],
        "human_gates": [],
    }

    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
        ctx = browser.contexts[0]
        page = ctx.new_page()

        for probe in (_probe_nebius, _probe_phoenix, _probe_azure):
            try:
                step = probe(page)
                run["steps"].append(step)
                if step.get("human_gate"):
                    run["human_gates"].append(step["human_gate"])
            except Exception as exc:
                run["steps"].append({"step": probe.__name__, "error": str(exc)[:300]})

        page.close()

    # NGC EULA — free; subprocess to keep this file small
    try:
        r = subprocess.run(
            [sys.executable, str(ROOT / "scripts/ngc_org_account_eula_autofill_v1.py"),
             "--cdp-url", "http://127.0.0.1:9222", "--wait-for-login-sec", "45"],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            timeout=120,
        )
        ngc: dict[str, Any] = {"step": "ngc_eula", "cost": 0, "exit_code": r.returncode}
        try:
            ngc["report"] = json.loads(
                (ROOT / "reports/ngc_org_account_eula_autofill_latest.json").read_text(encoding="utf-8")
            )
        except Exception:
            ngc["stdout_tail"] = (r.stdout or "")[-400:]
        run["steps"].append(ngc)
    except Exception as exc:
        run["steps"].append({"step": "ngc_eula", "error": str(exc)[:300]})

    # Patch downstream SSOT
    neb = next((s for s in run["steps"] if s.get("step") == "nebius_billing_verify"), {})
    if neb.get("payment_ok"):
        nbr = ROOT / "reports/nvidia_nebius_benefit_request_latest.json"
        if nbr.is_file():
            doc = json.loads(nbr.read_text(encoding="utf-8"))
            doc["billing_complete"] = True
            doc["balance_usd"] = neb.get("balance_usd")
            doc["next_ops"] = [
                "Phoenix Benefits → Requested 행 확인 (며칠 후 자동 반영)",
                "GPU PoC 필요 시에만 quota 내 research_only — 사전 승인·비용 상한",
                "NVIDIA Inception Nebius $5K 크레딧은 파트너 조건·프로모 반영 대기",
            ]
            doc["generated_at_utc"] = _utc()
            nbr.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    run["summary"] = {
        "nebius_billing": "ok" if neb.get("payment_ok") else "check_ui",
        "azure": "linkedin_pending" if "linkedin_tier3" in run["human_gates"] else "probe_done",
        "phoenix": "scraped",
        "compute": "not_started_by_design",
    }

    OUT.write_text(json.dumps(run, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(run, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
