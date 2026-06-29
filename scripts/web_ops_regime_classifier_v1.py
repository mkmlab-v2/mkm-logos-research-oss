#!/usr/bin/env python3
"""Classify web portal pages into MKM web-ops regimes (B-track, research_only)."""
from __future__ import annotations

import hashlib
import re
from typing import Any

REGIME_CATALOG: dict[str, dict[str, Any]] = {
    "captcha_blocker": {
        "label_ko": "봇 방지·CAPTCHA",
        "allowed_actions": ["observe"],
        "forbidden_actions": ["click", "fill", "submit", "navigate_loop"],
        "final_action": "HOLD_HUMAN",
        "human_gate": "captcha_turnstile_tier3",
    },
    "auth_wall": {
        "label_ko": "인증·OAuth 벽",
        "allowed_actions": ["observe"],
        "forbidden_actions": ["login", "password_fill", "oauth_click"],
        "final_action": "HOLD_AUTH",
        "human_gate": "auth_oauth_tier3",
    },
    "payment_risk": {
        "label_ko": "결제·카드 위험",
        "allowed_actions": ["observe", "billing_address_prefill"],
        "forbidden_actions": ["card_fill", "submit_payment", "create_vm"],
        "final_action": "HOLD_PAYMENT",
        "human_gate": "payment_card_tier3",
    },
    "destructive_submit": {
        "label_ko": "생성·제출·삭제",
        "allowed_actions": ["observe"],
        "forbidden_actions": ["create_vm", "create_gpu", "submit", "delete"],
        "final_action": "HOLD_DESTRUCTIVE",
        "human_gate": "destructive_submit_human",
    },
    "form_prefill_only": {
        "label_ko": "폼 프리필만",
        "allowed_actions": ["observe", "fill_non_payment_fields"],
        "forbidden_actions": ["submit", "card_fill"],
        "final_action": "ALLOW_PREFILL",
        "human_gate": None,
    },
    "read_only_dashboard": {
        "label_ko": "읽기 전용 대시보드",
        "allowed_actions": ["observe", "screenshot", "cdp_extract"],
        "forbidden_actions": ["create_vm", "submit_payment", "submit"],
        "final_action": "ALLOW_READ",
        "human_gate": None,
    },
    "unknown": {
        "label_ko": "미분류",
        "allowed_actions": ["observe"],
        "forbidden_actions": ["submit", "card_fill", "create_vm"],
        "final_action": "HOLD_UNKNOWN",
        "human_gate": "unknown_page_tier3",
    },
}

REGIME_PRIORITY: list[str] = [
    "captcha_blocker",
    "auth_wall",
    "payment_risk",
    "destructive_submit",
    "form_prefill_only",
    "read_only_dashboard",
    "unknown",
]

FINAL_ACTION_SEVERITY: dict[str, int] = {
    "ALLOW_READ": 0,
    "ALLOW_PREFILL": 1,
    "HOLD_UNKNOWN": 2,
    "HOLD_POINTER_DRIFT": 3,
    "HOLD_DESTRUCTIVE": 4,
    "HOLD_PAYMENT": 5,
    "HOLD_AUTH": 6,
    "HOLD_HUMAN": 7,
}

SIGNAL_RULES: list[tuple[str, str, str]] = [
    ("captcha_blocker", "captcha", "captcha"),
    ("captcha_blocker", "turnstile", "turnstile"),
    ("captcha_blocker", "verify you are human", "verify_human"),
    ("auth_wall", "sign in", "sign_in"),
    ("auth_wall", "log in", "log_in"),
    ("auth_wall", "accountchooser", "account_chooser"),
    ("auth_wall", "oauth", "oauth"),
    ("auth_wall", "password", "password"),
    ("auth_wall", "mfa", "mfa"),
    ("auth_wall", "sign in with microsoft", "microsoft_auth"),
    ("auth_wall", "login.microsoft", "microsoft_auth"),
    ("auth_wall", "microsoft account", "microsoft_auth"),
    ("payment_risk", "add payment", "add_payment"),
    ("payment_risk", "payment method", "payment_method"),
    ("payment_risk", "connect card", "connect_card"),
    ("payment_risk", "billing setup", "billing_setup"),
    ("payment_risk", "카드", "card_ko"),
    ("payment_risk", "결제 설정", "billing_setup_ko"),
    ("destructive_submit", "create vm", "create_vm"),
    ("destructive_submit", "create instance", "create_instance"),
    ("destructive_submit", "create gpu", "create_gpu"),
    ("destructive_submit", "delete", "delete"),
    ("read_only_dashboard", "limits", "limits"),
    ("read_only_dashboard", "quotas", "quotas"),
    ("read_only_dashboard", "balance", "balance"),
    ("read_only_dashboard", "consumption", "consumption"),
    ("read_only_dashboard", "ending balance", "ending_balance"),
    ("read_only_dashboard", "active", "active_account"),
    ("read_only_dashboard", "gpu quota", "gpu_quota"),
    ("form_prefill_only", "billing details", "billing_details"),
    ("form_prefill_only", "first name", "first_name"),
]

# Tier-2 CDP default navigation (transactions tab preferred for balance read).
NEBIUS_BILLING_OPEN_URL_PREFERRED = (
    "https://console.nebius.com/tenant-e00fe2zhs67gmz6wha/billing/"
    "customer-e00vbag5rkkjsv07n79y3/payments/transactions"
)
NEBIUS_BILLING_OPEN_URL_FALLBACK = (
    "https://console.nebius.com/tenant-e00fe2zhs67gmz6wha/billing/payments"
)


def nebius_billing_open_url(*, prefer_transactions: bool = True) -> str:
    if prefer_transactions:
        return NEBIUS_BILLING_OPEN_URL_PREFERRED
    return NEBIUS_BILLING_OPEN_URL_FALLBACK


HUMAN_GATE_REGIME: dict[str, str] = {
    "nebius_payment_card_tier3": "payment_risk",
    "nebius_billing_address_and_card_tier3": "payment_risk",
    "nebius_oauth_manual": "auth_wall",
    "google_account_chooser_or_consent": "auth_wall",
    "microsoft_password_or_mfa": "auth_wall",
    "linkedin_tier3": "auth_wall",
    "captcha_turnstile_tier3": "captcha_blocker",
}


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().lower())


_AUTH_WALL_URL_FRAGMENTS = (
    "auth.nebius.com",
    "/ui/login",
    "login.microsoft",
    "accountchooser",
    "login.live.com",
)


def is_auth_wall_observation(doc: dict[str, Any]) -> bool:
    """True when observation is Tier-3 login/OAuth wall (not console billing)."""
    url = (str(doc.get("url") or "")).lower()
    if any(fragment in url for fragment in _AUTH_WALL_URL_FRAGMENTS):
        return True
    if "console.nebius.com" in url:
        return False
    body = _norm(
        f"{doc.get('body_primary') or ''} {doc.get('body_secondary') or ''}"
    )
    if "welcome to nebius" in body and any(
        marker in body
        for marker in (
            "get started with google",
            "get started with microsoft",
            "get started with github",
            "get started with sso",
        )
    ):
        return True
    return False


def detect_signals(*, url: str, body_text: str, hints: dict[str, Any] | None = None) -> list[str]:
    blob = _norm(f"{url}\n{body_text}")
    if hints:
        blob += "\n" + _norm(" ".join(f"{k}={v}" for k, v in hints.items() if isinstance(v, (str, bool, int, float))))
    found: list[str] = []
    for _regime, needle, signal_id in SIGNAL_RULES:
        if needle in blob and signal_id not in found:
            found.append(signal_id)
    if hints:
        if hints.get("billing_setup_needed") and not hints.get("payment_configured"):
            if "billing_setup_unconfigured" not in found:
                found.append("billing_setup_unconfigured")
        if hints.get("payment_configured"):
            if "payment_configured" not in found:
                found.append("payment_configured")
        if hints.get("feasibility_report") or hints.get("artifact_read_only"):
            if "artifact_read_only" not in found:
                found.append("artifact_read_only")
    if "microsoft approves" in blob and "microsoft_auth" in found:
        found.remove("microsoft_auth")
    return found


def classify_regime(
    *,
    url: str,
    body_text: str,
    hints: dict[str, Any] | None = None,
    human_gate: str | None = None,
    intended_action: str = "observe",
) -> dict[str, Any]:
    hints = hints or {}
    signals = detect_signals(url=url, body_text=body_text, hints=hints)

    if human_gate and human_gate in HUMAN_GATE_REGIME:
        regime_id = HUMAN_GATE_REGIME[human_gate]
    else:
        matched = {rule[0] for rule in SIGNAL_RULES if rule[2] in signals}
        if "billing_setup_unconfigured" in signals and "payment_configured" not in signals:
            matched.add("payment_risk")
        if hints.get("payment_configured") or hints.get("billing_complete"):
            matched.discard("payment_risk")
        if "payment_configured" in signals or hints.get("balance_usd"):
            matched.add("read_only_dashboard")
        if hints.get("feasibility_report") or hints.get("artifact_read_only"):
            matched.add("read_only_dashboard")
            matched.discard("auth_wall")
        if intended_action in {"create_vm", "create_gpu", "submit"}:
            matched.add("destructive_submit")

        regime_id = "unknown"
        for candidate in REGIME_PRIORITY:
            if candidate in matched:
                regime_id = candidate
                break

    catalog = REGIME_CATALOG[regime_id]
    final_action = catalog["final_action"]
    if human_gate and regime_id in {"payment_risk", "auth_wall", "captcha_blocker"}:
        final_action = catalog["final_action"]

    outcome_class = "pass_candidate"
    if regime_id in {"payment_risk", "auth_wall", "captcha_blocker", "destructive_submit"}:
        outcome_class = "neutral_bucket"
    elif regime_id == "unknown":
        outcome_class = "opportunistic"
    elif regime_id == "read_only_dashboard" and (hints.get("payment_configured") or "payment_configured" in signals):
        outcome_class = "pass_candidate"

    return {
        "regime_id": regime_id,
        "signals": signals,
        "repair_v2": {
            "regime_id": regime_id,
            "regime_label_ko": catalog["label_ko"],
            "allowed_actions": list(catalog["allowed_actions"]),
            "forbidden_actions": list(catalog["forbidden_actions"]),
        },
        "final_action": final_action,
        "human_gate": human_gate or catalog.get("human_gate"),
        "outcome_class": outcome_class,
    }


def build_lens_hints(
    *,
    regime_id: str,
    signals: list[str],
    url: str,
    click_intercepted: bool = False,
) -> dict[str, Any]:
    logos_note = "[NON_GATING] URL·결제·quota 신호만; 로그인 추측 금지"
    if "payment_configured" in signals or "balance" in " ".join(signals):
        logos_note = "[NON_GATING] billing/read-only 신호 우세"
    flow = "observe_only"
    if regime_id == "read_only_dashboard":
        flow = "limits_or_payments_read_then_exit"
    elif regime_id == "form_prefill_only":
        flow = "prefill_non_payment_then_human_submit"
    elif regime_id in {"payment_risk", "auth_wall"}:
        flow = "stop_before_tier3_human"
    friction = "low"
    if click_intercepted or regime_id in {"auth_wall", "captcha_blocker"}:
        friction = "high"
    elif regime_id == "unknown":
        friction = "medium"
    return {
        "logos": {"tag": "NON_GATING", "note": logos_note, "url_host": (url or "").split("/")[2] if url else ""},
        "myeongni": {"flow_hint": flow},
        "sasang": {"ui_friction": friction, "click_intercepted": click_intercepted},
    }


def page_fingerprint(*, url: str, anchor_strings: list[str]) -> str:
    payload = _norm(url) + "|" + "|".join(sorted(_norm(s) for s in anchor_strings if s))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def _token_set(text: str) -> set[str]:
    return {t for t in re.split(r"[^a-z0-9]+", _norm(text)) if len(t) >= 3}


def text_similarity(a: str, b: str) -> float:
    sa, sb = _token_set(a), _token_set(b)
    if not sa and not sb:
        return 1.0
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


def dual_observation_gate(
    *,
    body_primary: str,
    body_secondary: str,
    min_similarity: float = 0.72,
) -> dict[str, Any]:
    sim = round(text_similarity(body_primary, body_secondary), 4)
    alignment_pass = sim >= min_similarity
    return {
        "raw_primary_chars": len(body_primary or ""),
        "raw_secondary_chars": len(body_secondary or ""),
        "similarity": sim,
        "min_similarity": min_similarity,
        "alignment_pass": alignment_pass,
        "delta": round(sim - min_similarity, 4),
        "label": "operational (dual channel agreement)" if alignment_pass else "mismatch_hold",
    }


def pointer_drift_check(
    *,
    probe_key: str,
    current_fingerprint: str,
    baselines: dict[str, Any],
) -> dict[str, Any]:
    row = baselines.get(probe_key) if isinstance(baselines, dict) else None
    baseline_fp = str((row or {}).get("page_fingerprint") or "")
    if not baseline_fp:
        return {
            "probe_key": probe_key,
            "baseline_fingerprint": None,
            "current_fingerprint": current_fingerprint,
            "drift_detected": False,
            "action": None,
            "note": "no_baseline_seed_optional",
        }
    drift = baseline_fp != current_fingerprint
    return {
        "probe_key": probe_key,
        "baseline_fingerprint": baseline_fp,
        "current_fingerprint": current_fingerprint,
        "drift_detected": drift,
        "action": "HOLD_POINTER_DRIFT" if drift else None,
        "note": "ui_anchor_changed_review_before_click" if drift else "baseline_match",
    }


def parse_balance_usd(text: str) -> float | None:
    blob = _norm(text)
    patterns = (
        r"active\s+balance[^\d$]*\$?\s*([\d,]+\.?\d*)",
        r"ending\s+balance[^\d$]*\$?\s*([\d,]+\.?\d*)",
        r"(?:balance|prepaid)[^\d$]*\$?\s*([\d,]+\.?\d*)",
    )
    for pattern in patterns:
        m = re.search(pattern, blob, re.I)
        if m:
            try:
                return float(m.group(1).replace(",", ""))
            except ValueError:
                continue
    m = re.search(r"\$\s*([\d,]+\.\d{2})\b", text or "")
    if not m:
        return None
    try:
        return float(m.group(1).replace(",", ""))
    except ValueError:
        return None


def probe_from_live_observation(
    *,
    probe_id: str,
    portal: str,
    url: str,
    title: str,
    body_primary: str,
    body_secondary: str,
    hints: dict[str, Any] | None = None,
    human_gate: str | None = None,
    baselines: dict[str, Any] | None = None,
    intended_action: str = "observe",
    min_dual_similarity: float = 0.72,
) -> dict[str, Any]:
    hints = dict(hints or {})
    balance = parse_balance_usd(body_primary) or parse_balance_usd(body_secondary)
    if balance is not None:
        hints["balance_usd"] = balance
        hints.setdefault("payment_configured", True)

    classified = classify_regime(
        url=url,
        body_text=f"{title}\n{body_primary}",
        hints=hints,
        human_gate=human_gate,
        intended_action=intended_action,
    )
    dual = dual_observation_gate(
        body_primary=body_primary,
        body_secondary=body_secondary,
        min_similarity=min_dual_similarity,
    )
    anchors = [title, url] + classified["signals"][:5]
    fp = page_fingerprint(url=url, anchor_strings=anchors)
    drift = pointer_drift_check(probe_key=f"{portal}:{probe_id}", current_fingerprint=fp, baselines=baselines or {})

    final_action = classified["final_action"]
    if not dual["alignment_pass"]:
        final_action = "HOLD_UNKNOWN"
    elif drift.get("drift_detected"):
        final_action = "HOLD_POINTER_DRIFT"

    outcome_class = classified["outcome_class"]
    if final_action.startswith("HOLD_"):
        outcome_class = "neutral_bucket"

    return {
        "probe_id": probe_id,
        "portal": portal,
        "observation_source": "cdp_live",
        "raw": {
            "url": url,
            "title": title,
            "body_snippet": (body_primary or "")[:500],
            "body_secondary_snippet": (body_secondary or "")[:500],
            "signals": classified["signals"],
            "human_gate_in": human_gate,
            "balance_usd": balance,
        },
        "dual_observation": dual,
        "pointer_drift": drift,
        "repair_v2": classified["repair_v2"],
        "lens_hints": build_lens_hints(
            regime_id=classified["regime_id"],
            signals=classified["signals"],
            url=url,
            click_intercepted=not dual["alignment_pass"],
        ),
        "final_action": final_action,
        "human_gate": classified["human_gate"],
        "outcome_class": outcome_class,
        "page_fingerprint": fp,
    }


def worst_final_action(actions: list[str]) -> str:
    if not actions:
        return "HOLD_UNKNOWN"
    return max(actions, key=lambda a: FINAL_ACTION_SEVERITY.get(a, 99))


def probe_from_portal_json(
    *,
    probe_id: str,
    portal: str,
    doc: dict[str, Any],
    intended_action: str = "observe",
) -> dict[str, Any]:
    url = str(doc.get("billing_url") or doc.get("limits_url") or doc.get("project_url") or doc.get("url") or "")
    title = str(doc.get("console_title") or doc.get("title") or "")
    body = str(
        doc.get("billing_snippet")
        or doc.get("body_snippet")
        or doc.get("snippet")
        or ""
    )
    hints = {
        k: v
        for k, v in doc.items()
        if k.startswith("billing_") or k in {"payment_configured", "billing_setup_needed", "billing_complete"}
    }
    if doc.get("balance_usd") is not None:
        hints["balance_usd"] = doc.get("balance_usd")
    if doc.get("billing_complete"):
        hints["payment_configured"] = True
    human_gate = doc.get("human_gate")
    if isinstance(human_gate, str):
        human_gate = human_gate or None

    classified = classify_regime(
        url=url,
        body_text=f"{title}\n{body}",
        hints=hints,
        human_gate=human_gate,
        intended_action=intended_action,
    )
    anchors = [title, url] + classified["signals"][:5]
    return {
        "probe_id": probe_id,
        "portal": portal,
        "raw": {
            "url": url,
            "title": title,
            "body_snippet": body[:500],
            "signals": classified["signals"],
            "human_gate_in": human_gate,
            "balance_usd": doc.get("balance_usd"),
            "consumption_usd": doc.get("consumption_usd"),
        },
        "repair_v2": classified["repair_v2"],
        "lens_hints": build_lens_hints(
            regime_id=classified["regime_id"],
            signals=classified["signals"],
            url=url,
            click_intercepted=bool(doc.get("click_intercepted")),
        ),
        "final_action": classified["final_action"],
        "human_gate": classified["human_gate"],
        "outcome_class": classified["outcome_class"],
        "page_fingerprint": page_fingerprint(url=url, anchor_strings=anchors),
    }
