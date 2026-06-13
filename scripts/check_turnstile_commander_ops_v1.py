#!/usr/bin/env python3
"""Turnstile commander ops check — Tier 3 handoff + optional read-only widget API probe.

Never prints secret values. SSOT: docs/final/artifacts/turnstile_commander_ops_check_v1_latest.json

  py scripts/check_turnstile_commander_ops_v1.py
"""
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from mkm_cloudflare_token_v1 import (  # noqa: E402
    _read_dotenv_key,
    _read_windows_user_env,
    resolve_cloudflare_token,
    token_fingerprint,
)

OUT = ROOT / "docs" / "final" / "artifacts" / "turnstile_commander_ops_check_v1_latest.json"
ACCOUNT_ID = "646e42cf881ab43043c32430e99d9af4"
TURNSTILE_DASHBOARD = (
    f"https://dash.cloudflare.com/{ACCOUNT_ID}/turnstile"
)


def _token_for_key(key: str) -> tuple[str, str]:
    import os

    def _norm(v: str) -> str:
        return v.strip().strip("<>").strip('"').strip("'")

    v = _read_windows_user_env(key)
    if v:
        return _norm(v), f"user_env:{key}"
    v = os.environ.get(key, "").strip()
    if v:
        return _norm(v), f"process_env:{key}"
    v = _read_dotenv_key(key)
    if v:
        return _norm(v), f".env:{key}"
    return "", "missing"


def _list_widgets(tok: str) -> dict[str, Any]:
    url = (
        f"https://api.cloudflare.com/client/v4/accounts/{ACCOUNT_ID}/challenges/widgets"
    )
    req = urllib.request.Request(
        url,
        headers={"Authorization": f"Bearer {tok}", "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = json.loads(resp.read().decode())
            items = body.get("result") or []
            redacted = []
            for w in items if isinstance(items, list) else []:
                if not isinstance(w, dict):
                    continue
                redacted.append(
                    {
                        "sitekey": w.get("sitekey"),
                        "name": w.get("name"),
                        "domains": w.get("domains"),
                        "mode": w.get("mode"),
                        "created_on": w.get("created_on"),
                        "modified_on": w.get("modified_on"),
                    }
                )
            return {
                "http": resp.status,
                "success": bool(body.get("success")),
                "widget_count": len(redacted),
                "widgets_redacted": redacted,
                "blocker": None,
            }
    except urllib.error.HTTPError as e:
        try:
            body = json.loads(e.read().decode())
        except Exception:
            body = {}
        codes = [err.get("code") for err in (body.get("errors") or []) if isinstance(err, dict)]
        return {
            "http": e.code,
            "success": False,
            "widget_count": 0,
            "widgets_redacted": [],
            "blocker": f"http_{e.code}" + (f"_code_{codes[0]}" if codes else ""),
        }


def main() -> int:
    turnstile_tok, turnstile_src = _token_for_key("CLOUDFLARE_TURNSTILE_API_TOKEN")
    general_tok, general_src = resolve_cloudflare_token()
    rulesets_tok, rulesets_src = _token_for_key("CLOUDFLARE_RULESETS_API_TOKEN")

    api_probes: list[dict[str, Any]] = []
    for label, tok, src in (
        ("turnstile_dedicated", turnstile_tok, turnstile_src),
        ("general_dns", general_tok, general_src),
        ("rulesets", rulesets_tok, rulesets_src),
    ):
        if not tok:
            api_probes.append(
                {
                    "label": label,
                    "token_source": src,
                    "token_fingerprint": None,
                    "probe": {"skipped": True, "reason": "no_token"},
                }
            )
            continue
        api_probes.append(
            {
                "label": label,
                "token_source": src,
                "token_fingerprint": token_fingerprint(tok),
                "probe": _list_widgets(tok),
            }
        )

    any_api_ok = any(
        (p.get("probe") or {}).get("success") and (p.get("probe") or {}).get("widget_count", 0) >= 0
        for p in api_probes
        if not (p.get("probe") or {}).get("skipped")
    )
    widget_count = max(
        ((p.get("probe") or {}).get("widget_count") or 0) for p in api_probes
    )

    human_steps = [
        {
            "id": "H1_open_turnstile_dashboard",
            "tier": "tier3_human_chrome",
            "action_ko": "지휘관 Chrome에서 Turnstile 대시보드 열기",
            "url": TURNSTILE_DASHBOARD,
            "record": "스크린샷 또는 sitekey 개수 1줄 메모",
        },
        {
            "id": "H2_verify_widget_domains",
            "tier": "tier3_human_chrome",
            "action_ko": "각 위젯의 허용 도메인·모드(관리/비관리) 확인",
            "record": "jemaai.cloud / jema-ai.com 등 운영 도메인만 포함되는지",
        },
        {
            "id": "H3_secret_rotation_policy",
            "tier": "tier3_human_chrome",
            "action_ko": "secret 최근 rotate 여부·grace period 확인",
            "record": "rotate_secret 직후 2h grace — 배포 타이밍 메모",
        },
        {
            "id": "H4_completion_signal",
            "tier": "tier3_human_chrome",
            "action_ko": "완료 한 줄",
            "record": "CF Turnstile commander ops done",
        },
    ]

    if turnstile_tok and any(
        (p.get("label") == "turnstile_dedicated")
        and (p.get("probe") or {}).get("success")
        and (p.get("probe") or {}).get("widget_count", 0) >= 1
        for p in api_probes
    ):
        decision = "API_OK_WIDGETS_PRESENT"
        human_gate = "optional_dashboard_confirm"
    elif turnstile_tok and any(
        (p.get("label") == "turnstile_dedicated") and (p.get("probe") or {}).get("success")
        for p in api_probes
    ):
        decision = "API_OK_ZERO_WIDGETS"
        human_gate = "run_provision_turnstile_jema_ai_widget_v1"
    elif any_api_ok and widget_count > 0:
        decision = "API_PARTIAL_OK_PENDING_HUMAN_CONFIRM"
        human_gate = "optional_confirm_in_dashboard"
    elif any_api_ok:
        decision = "API_OK_ZERO_WIDGETS_PENDING_HUMAN"
        human_gate = "required_create_or_confirm_widgets"
    else:
        decision = "PENDING_HUMAN_TIER3"
        human_gate = "required_no_turnstile_api_scope"

    doc = {
        "schema": "turnstile_commander_ops_check_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "research_only": True,
        "tier3_policy": "mkm-browser-automation-v1.mdc — dash.cloudflare.com/Turnstile = Human Chrome only",
        "account_id": ACCOUNT_ID,
        "api_probes": api_probes,
        "human_steps": human_steps,
        "decision": decision,
        "human_gate": human_gate,
        "references": {
            "turnstile_changelog": "https://developers.cloudflare.com/turnstile/changelog/",
            "cf_edge_dashboard": "docs/final/JEMAAI_CLOUD_SHOWROOM_CF_EDGE_DASHBOARD_V1.md",
        },
        "reproduce": "py scripts/check_turnstile_commander_ops_v1.py",
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, indent=2), encoding="utf-8")
    print(json.dumps(doc, indent=2, ensure_ascii=False))
    print(f"\n[turnstile_ops] decision={decision} human_gate={human_gate}", file=sys.stderr)
    print(f"[turnstile_ops] artifact={OUT}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
