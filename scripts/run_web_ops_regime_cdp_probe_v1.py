#!/usr/bin/env python3
"""Live CDP probe: dual observation + pointer drift for web_ops_regime_gate_v1 (B-track)."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.build_web_ops_regime_gate_v1 import build_gate, _merge_nebius_docs, _read_json
from scripts.web_ops_regime_classifier_v1 import (
    is_auth_wall_observation,
    nebius_billing_open_url,
    parse_balance_usd,
    probe_from_live_observation,
)

DEFAULT_OUT = ROOT / "reports/web_ops_regime_cdp_probe_v1_latest.json"
DEFAULT_GATE_OUT = ROOT / "reports/web_ops_regime_gate_v1_latest.json"
DEFAULT_BASELINES = ROOT / "reports/web_ops_regime_pointer_baselines_v1.json"
DEFAULT_LIVE_OBS = ROOT / "reports/web_ops_regime_live_observation_v1_latest.json"
DEFAULT_IDE_OBS = ROOT / "reports/web_ops_regime_ide_browser_observation_v1_latest.json"
DEFAULT_NEBIUS = ROOT / "reports/nvidia_nebius_console_setup_latest.json"
DEFAULT_NEBIUS_BENEFIT = ROOT / "reports/nvidia_nebius_benefit_request_latest.json"
DEFAULT_AZURE = ROOT / "reports/azure_gpu_feasibility_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_baselines(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    doc = json.loads(path.read_text(encoding="utf-8-sig"))
    rows = doc.get("baselines") if isinstance(doc.get("baselines"), dict) else doc
    return rows if isinstance(rows, dict) else {}


def _body_hints(text: str) -> dict[str, Any]:
    low = (text or "").lower()
    return {
        "billing_setup_needed": any(
            k in low for k in ("add payment", "payment method", "connect card", "billing setup", "결제", "카드")
        ),
        "payment_configured": any(
            k in low
            for k in ("balance", "ending balance", "consumption", "active", "card ending", "customer-", "$25")
        ),
    }


def _extract_secondary_body(page: Any) -> str:
    try:
        return page.evaluate(
            """() => {
                const b = document.body;
                if (!b) return '';
                return (b.innerText || b.textContent || '').trim();
            }"""
        ) or ""
    except Exception:
        return ""


def _billing_tab_score(url: str) -> int:
    low = (url or "").lower()
    score = 0
    if "console.nebius.com" not in low:
        return score
    if "billing" in low:
        score += 10
    if "transactions" in low:
        score += 8
    if "payments" in low:
        score += 5
    if "/network" in low or "network" in low.split("/")[-1]:
        score -= 6
    return score


def _pick_page(browser: Any, host_filter: str) -> Any | None:
    needle = host_filter.lower().strip()
    candidates: list[tuple[int, Any]] = []
    for ctx in browser.contexts:
        for pg in ctx.pages:
            url = (pg.url or "").lower()
            if needle and needle in url:
                candidates.append((_billing_tab_score(url), pg))
    if not candidates:
        return None
    candidates.sort(key=lambda item: (-item[0], item[1].url or ""))
    return candidates[0][1]


def capture_observation_from_playwright_page(
    page: Any,
    *,
    human_gate: str | None = None,
    extra_hints: dict[str, Any] | None = None,
) -> dict[str, Any]:
    url = page.url or ""
    title = page.title() or ""
    body_primary = page.inner_text("body", timeout=12_000) or ""
    body_secondary = _extract_secondary_body(page)
    hints = _body_hints(body_primary)
    hints.update(_body_hints(body_secondary))
    if extra_hints:
        hints.update(extra_hints)
    return {
        "captured_at_utc": _utc(),
        "observation_mode": "playwright_cdp_page",
        "url": url,
        "title": title,
        "body_primary": body_primary,
        "body_secondary": body_secondary,
        "hints": hints,
        "human_gate": human_gate,
    }


def write_live_observation_json(
    observation: dict[str, Any],
    *,
    out: Path = DEFAULT_LIVE_OBS,
    also_mirror_ide: bool = True,
    skip_auth_wall_overwrite: bool = True,
) -> Path:
    if skip_auth_wall_overwrite and is_auth_wall_observation(observation):
        for path in (out, DEFAULT_IDE_OBS if also_mirror_ide else None):
            if path is None or not path.is_file():
                continue
            try:
                existing = json.loads(path.read_text(encoding="utf-8-sig"))
            except (OSError, json.JSONDecodeError):
                continue
            if not is_auth_wall_observation(existing):
                return path
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(observation, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if also_mirror_ide:
        mirror = dict(observation)
        mirror["observation_mode"] = str(observation.get("observation_mode") or "live") + "_mirrored_ide"
        DEFAULT_IDE_OBS.write_text(json.dumps(mirror, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return out


def capture_live_observation(
    *,
    cdp_url: str,
    host_filter: str,
    wait_ms: int,
    open_url: str | None = None,
) -> dict[str, Any]:
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp(cdp_url.strip())
        page = _pick_page(browser, host_filter)
        if page is None:
            if not open_url:
                raise RuntimeError(f"no_tab_matching_host:{host_filter}")
            ctx = browser.contexts[0] if browser.contexts else browser.new_context()
            page = ctx.new_page()
            page.goto(open_url, wait_until="domcontentloaded", timeout=120_000)
        elif open_url:
            norm_cur = (page.url or "").split("?")[0].rstrip("/").lower()
            norm_tgt = open_url.split("?")[0].rstrip("/").lower()
            if norm_cur != norm_tgt:
                page.goto(open_url, wait_until="domcontentloaded", timeout=120_000)
        page.bring_to_front()
        if wait_ms > 0:
            page.wait_for_timeout(wait_ms)
        url = page.url or ""
        title = page.title() or ""
        body_primary = page.inner_text("body", timeout=12_000) or ""
        body_secondary = _extract_secondary_body(page)
        hints = _body_hints(body_primary)
        hints.update(_body_hints(body_secondary))
        balance = parse_balance_usd(body_primary) or parse_balance_usd(body_secondary)
        if balance is not None:
            hints["balance_usd"] = balance
            hints.setdefault("payment_configured", True)
        return {
            "captured_at_utc": _utc(),
            "cdp_url": cdp_url,
            "host_filter": host_filter,
            "url": url,
            "title": title,
            "body_primary": body_primary,
            "body_secondary": body_secondary,
            "hints": hints,
            "human_gate": None,
        }


def observation_from_nebius_portal(doc: dict[str, Any]) -> dict[str, Any]:
    """Derive dual-channel observation from Nebius console probe JSON (offline fallback)."""
    console = doc.get("console") if isinstance(doc.get("console"), dict) else {}
    url = str(
        console.get("payments_url")
        or doc.get("billing_url")
        or doc.get("limits_url")
        or doc.get("project_url")
        or ""
    )
    if "/billing/consumption" in url:
        url = url.replace("/billing/consumption", "/billing/payments")
    title = str(doc.get("console_title") or "")
    body = str(doc.get("billing_snippet") or "")
    if doc.get("balance_usd") is not None:
        body += f" Active Balance ${doc['balance_usd']:.2f} Ending balance Consumption $0.00"
    if doc.get("gpu_limits_mentioned"):
        body += " Limits Quotas " + " ".join(str(g) for g in doc["gpu_limits_mentioned"])
    hints = _body_hints(body)
    if doc.get("billing_complete") or doc.get("setup_ok"):
        hints["payment_configured"] = True
    if doc.get("balance_usd") is not None:
        hints["balance_usd"] = doc["balance_usd"]
    if doc.get("billing_setup_needed") is False and doc.get("billing_payment_configured") is False:
        if hints.get("payment_configured"):
            pass
    human_gate = doc.get("human_gate")
    return {
        "captured_at_utc": _utc(),
        "observation_mode": "portal_json_derived",
        "url": url,
        "title": title,
        "body_primary": body,
        "body_secondary": body,
        "hints": hints,
        "human_gate": human_gate,
    }


def probe_from_observation_doc(
    doc: dict[str, Any],
    *,
    baselines: dict[str, Any],
    min_dual_similarity: float,
) -> dict[str, Any]:
    url = str(doc.get("url") or "")
    portal = "nebius" if "nebius.com" in url else "unknown"
    if "azure" in url:
        portal = "azure"
    return probe_from_live_observation(
        probe_id="cdp_live_tab",
        portal=portal,
        url=url,
        title=str(doc.get("title") or ""),
        body_primary=str(doc.get("body_primary") or doc.get("body_snippet") or ""),
        body_secondary=str(doc.get("body_secondary") or doc.get("body_primary") or doc.get("body_snippet") or ""),
        hints=dict(doc.get("hints") or {}),
        human_gate=doc.get("human_gate"),
        baselines=baselines,
        min_dual_similarity=min_dual_similarity,
    )


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--cdp-url", default="http://127.0.0.1:9222")
    ap.add_argument("--host-filter", default="console.nebius.com")
    ap.add_argument("--wait-ms", type=int, default=2000)
    ap.add_argument("--dry-run-from-json", type=Path, default=None)
    ap.add_argument("--from-nebius-json", type=Path, default=None)
    ap.add_argument("--from-nebius-benefit-json", type=Path, default=DEFAULT_NEBIUS_BENEFIT)
    ap.add_argument("--baselines-json", type=Path, default=DEFAULT_BASELINES)
    ap.add_argument("--min-dual-similarity", type=float, default=0.72)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--refresh-gate", action="store_true", default=True)
    ap.add_argument("--no-refresh-gate", dest="refresh_gate", action="store_false")
    ap.add_argument("--gate-out", type=Path, default=DEFAULT_GATE_OUT)
    ap.add_argument("--skip-azure", action="store_true")
    args = ap.parse_args()

    baselines = _load_baselines(args.baselines_json)
    run: dict[str, Any] = {
        "schema": "web_ops_regime_cdp_probe_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "track_wall": "b_track_research",
    }

    try:
        if args.dry_run_from_json:
            obs = _read_json(args.dry_run_from_json)
            run["observation_source"] = "dry_run_json"
            run["observation_path"] = str(args.dry_run_from_json)
        elif args.from_nebius_json:
            nebius = _merge_nebius_docs(
                _read_json(args.from_nebius_json),
                _read_json(args.from_nebius_benefit_json),
            )
            if not nebius:
                raise ValueError("empty_nebius_portal_json")
            obs = observation_from_nebius_portal(nebius)
            run["observation_source"] = "portal_json_derived"
            run["observation_path"] = str(args.from_nebius_json)
        else:
            obs = capture_live_observation(
                cdp_url=args.cdp_url,
                host_filter=args.host_filter,
                wait_ms=args.wait_ms,
                open_url=nebius_billing_open_url(),
            )
            if is_auth_wall_observation(obs):
                raise RuntimeError("auth_wall_observation:tier3_human_login_required")
            run["observation_source"] = "cdp_live"
            run["cdp_url"] = args.cdp_url
            run["host_filter"] = args.host_filter

        probe = probe_from_observation_doc(
            obs,
            baselines=baselines,
            min_dual_similarity=args.min_dual_similarity,
        )
        run["observation"] = {
            "url": obs.get("url"),
            "title": obs.get("title"),
            "hints": obs.get("hints"),
        }
        run["probe"] = probe
        run["dual_observation"] = probe.get("dual_observation")
        run["pointer_drift"] = probe.get("pointer_drift")
        run["final_action"] = probe.get("final_action")
        run["ok"] = True
    except Exception as exc:
        run["ok"] = False
        run["error"] = str(exc)
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(run, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"ok": False, "error": str(exc), "out": str(args.out)}, ensure_ascii=False))
        return 2

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(run, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    gate_summary: dict[str, Any] | None = None
    if args.refresh_gate and run.get("probe"):
        nebius = _merge_nebius_docs(_read_json(DEFAULT_NEBIUS), _read_json(DEFAULT_NEBIUS_BENEFIT))
        azure = {} if args.skip_azure else _read_json(DEFAULT_AZURE)
        gate = build_gate(
            nebius_doc=nebius or None,
            azure_doc=azure or None,
            extra_probes=[probe],
        )
        gate["evidence_bundle"]["web_ops_regime_cdp_probe"] = str(args.out)
        args.gate_out.parent.mkdir(parents=True, exist_ok=True)
        args.gate_out.write_text(json.dumps(gate, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        gate_summary = {
            "gate_out": str(args.gate_out),
            "gate_pass": gate["gate_pass"],
            "worst_final_action": gate["conflict_resolver"]["worst_final_action"],
            "probe_count": gate["conflict_resolver"]["probe_count"],
        }

    print(
        json.dumps(
            {
                "ok": True,
                "out": str(args.out),
                "final_action": probe.get("final_action"),
                "dual_alignment_pass": (probe.get("dual_observation") or {}).get("alignment_pass"),
                "pointer_drift": (probe.get("pointer_drift") or {}).get("drift_detected"),
                "gate": gate_summary,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
