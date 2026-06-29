#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Post-LLM four-slot fill — imagination_path / unknown_gap only (B-track)."""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from datetime import datetime, timezone
from typing import Any

FORBIDDEN_PHRASES = (
    "Fact-Lock 100%",
    "환각 제거",
    "확정적으로",
    "반드시 받은 이유는",
    "인과가 확정",
)
HYPO_PREFIX = "[HYPO][NON_GATING] "
CAUSAL_TAIL = " — 코퍼스·시드 기반 해석 경로이며 인과·사실 확정이 아닙니다."


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _truthy_env(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in ("1", "true", "yes", "on")


def _policy_ok(envelope: dict[str, Any], *, human_gate_ack: bool) -> list[str]:
    errors: list[str] = []
    policy = envelope.get("llm_fill_policy_v1") or {}
    if not policy.get("enabled"):
        errors.append("llm_fill_policy_v1.enabled is false")
    if policy.get("requires_human_gate_ack") and not human_gate_ack:
        errors.append("human_gate_ack required")
    req_env = str(policy.get("requires_env") or "MKM_FOUR_SLOT_LLM_FILL_ALLOWED")
    if policy.get("cost_tier") == "tier_15" and not _truthy_env(req_env):
        errors.append(f"env {req_env} not set for tier_15 live fill")
    enf = envelope.get("enforcement") or {}
    if enf.get("llm_autofill_for_schools") is not True:
        errors.append("envelope enforcement.llm_autofill_for_schools must be true")
    if (envelope.get("fact_lock") or {}).get("send_gate") != "HOLD":
        errors.append("send_gate must remain HOLD")
    return errors


def _forbidden_hit(text: str, extra: list[str] | None = None) -> str | None:
    hay = text or ""
    for phrase in (*(extra or []), *FORBIDDEN_PHRASES):
        if phrase and phrase in hay:
            return phrase
    return None


def _template_expand_item(item: dict[str, Any], *, max_chars: int) -> dict[str, Any]:
    base = str(item.get("text_ko") or "").strip()
    label = str((item.get("label_ko") or item.get("extra", {}).get("label_ko") or "")).strip()
    school = str((item.get("school_id") or item.get("extra", {}).get("school_id") or "")).strip()
    head = HYPO_PREFIX
    if label:
        head += f"{label}"
        if school:
            head += f" ({school})"
        head += ": "
    body = base if base else "큐레이션 시드 미리보기 — 본문 밖 단정 금지."
    out = (head + body + CAUSAL_TAIL).strip()
    if len(out) > max_chars:
        out = out[: max_chars - 1] + "…"
    merged = dict(item)
    merged["text_ko"] = out
    merged["must_not_present_as_fact"] = True
    merged["source_tier"] = str(item.get("source_tier") or "post_llm_template_v1")
    merged["post_llm_fill"] = {"mode": "template_expand", "filled_at_utc": _utc_now()}
    return merged


def _ollama_expand(prompt: str, *, model: str, timeout: int = 60) -> str | None:
    host = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434").rstrip("/")
    body = json.dumps(
        {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.2},
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        f"{host}/api/generate",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            doc = json.loads(resp.read().decode("utf-8"))
            return str(doc.get("response") or "").strip() or None
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError):
        return None


def _live_expand_item(item: dict[str, Any], *, envelope: dict[str, Any], max_chars: int) -> dict[str, Any]:
    policy = envelope.get("llm_fill_policy_v1") or {}
    model = os.environ.get("OLLAMA_MODEL", "gemma4:e2b")
    label = str((item.get("label_ko") or item.get("extra", {}).get("label_ko") or "학파 읽기"))
    seed = str(item.get("text_ko") or "")[:320]
    prompt = (
        "You write Korean research-only theology panorama notes. "
        "Never claim causal certainty for 'why' questions. "
        "Never say Fact-Lock 100% or hallucination-free. "
        "Start with [HYPO][NON_GATING]. Max 3 sentences.\n"
        f"School: {label}\nSeed:\n{seed}\n"
    )
    generated = _ollama_expand(prompt, model=model)
    merged = dict(item)
    if generated and not _forbidden_hit(generated, policy.get("forbidden_phrases")):
        text = generated if generated.startswith("[HYPO") else HYPO_PREFIX + generated
        if CAUSAL_TAIL.strip() not in text:
            text = (text.rstrip() + CAUSAL_TAIL).strip()
        merged["text_ko"] = text[:max_chars]
        merged["post_llm_fill"] = {"mode": "ollama_live", "model": model, "filled_at_utc": _utc_now()}
    else:
        merged = _template_expand_item(item, max_chars=max_chars)
        merged["post_llm_fill"]["fallback"] = "template_expand"
    merged["must_not_present_as_fact"] = True
    return merged


def apply_post_llm_fill(
    insight: dict[str, Any],
    *,
    envelope: dict[str, Any],
    mode: str = "template_expand",
    human_gate_ack: bool = False,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Return (updated_insight, fill_report)."""
    policy = envelope.get("llm_fill_policy_v1") or {}
    allowed = set(policy.get("allowed_slots") or ["imagination_path", "unknown_gap"])
    max_chars = int(policy.get("max_chars_per_item") or 480)
    four = insight.get("four_slot_response_v1")
    if not four:
        return insight, {"ok": False, "error": "missing_four_slot_response_v1"}

    if mode == "live":
        pol_err = _policy_ok(envelope, human_gate_ack=human_gate_ack)
        if pol_err:
            return insight, {"ok": False, "error": "policy_blocked", "details": pol_err}

    slots = dict(four.get("slots") or {})
    filled_counts: dict[str, int] = {}
    for slot_id in allowed:
        if slot_id not in slots:
            continue
        slot = dict(slots[slot_id])
        items_out: list[dict[str, Any]] = []
        for raw in slot.get("items") or []:
            if not isinstance(raw, dict):
                continue
            if mode == "live":
                items_out.append(_live_expand_item(raw, envelope=envelope, max_chars=max_chars))
            else:
                items_out.append(_template_expand_item(raw, max_chars=max_chars))
        slot["items"] = items_out
        slots[slot_id] = slot
        filled_counts[slot_id] = len(items_out)

    four = dict(four)
    four["slots"] = slots
    four["post_llm_fill_v1"] = {
        "schema": "magic_orb_four_slot_post_llm_fill_v1",
        "mode": mode,
        "filled_at_utc": _utc_now(),
        "slots_filled": filled_counts,
        "cost_tier": policy.get("cost_tier") or ("tier_15" if mode == "live" else "tier_0"),
        "human_gate_ack": human_gate_ack,
        "track": "B",
        "send_gate": "HOLD",
    }

    out = dict(insight)
    out["four_slot_response_v1"] = four
    report = {
        "ok": True,
        "mode": mode,
        "slots_filled": filled_counts,
        "items_total": sum(filled_counts.values()),
    }
    return out, report


def quality_check(insight: dict[str, Any], envelope: dict[str, Any] | None = None) -> list[str]:
    errors: list[str] = []
    four = insight.get("four_slot_response_v1") or {}
    meta = four.get("post_llm_fill_v1") or {}
    if not meta:
        errors.append("missing post_llm_fill_v1 metadata")
        return errors

    extra_forbidden = []
    if envelope:
        extra_forbidden = list((envelope.get("llm_fill_policy_v1") or {}).get("forbidden_phrases") or [])

    for slot_id in ("imagination_path", "unknown_gap"):
        for item in (four.get("slots") or {}).get(slot_id, {}).get("items") or []:
            text = str(item.get("text_ko") or "")
            hit = _forbidden_hit(text, extra_forbidden)
            if hit:
                errors.append(f"forbidden phrase in {slot_id}: {hit}")
            if not text.startswith("[HYPO"):
                errors.append(f"{slot_id} item must start with [HYPO")
            if not item.get("must_not_present_as_fact", True):
                errors.append(f"{slot_id} must_not_present_as_fact required")

    if meta.get("send_gate", "HOLD") != "HOLD":
        errors.append("post_llm_fill send_gate must be HOLD")

    fact_items = (four.get("slots") or {}).get("fact_locked", {}).get("items") or []
    if fact_items and not (four.get("slots") or {}).get("fact_locked", {}).get("empty_reason"):
        errors.append("post_llm_fill must not populate fact_locked without empty_reason cleared")

    why_merge = re.search(r"(그래서|따라서).{0,40}(받은 이유|인과)", "\n".join(
        str(i.get("text_ko") or "") for i in (four.get("slots") or {}).get("imagination_path", {}).get("items") or []
    ))
    if why_merge:
        errors.append("imagination_path causal merge pattern detected")

    return errors
