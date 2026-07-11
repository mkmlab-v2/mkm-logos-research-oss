#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build security-scrubbed Claude submit pack for Claim-A L0 (research only).

Honesty rev 1.7 contract (1.6 + egress Hero reframe):
  - independent_blind = third_party only
  - commander_full_kit / self_reviewed_full_kit disclosed separately
  - api_error_count defined as arm-call failures
  - gate_ok = syntactic egress, not semantic quality
  - Blind unblinded prefer (plain vs id_only) lighted next to headline
  - A/B label tallies ≠ arm tallies when sides are randomized per item
  - External Hero = egress/security boundary — NOT usefulness for pointer arm

  py scripts/build_mkm_middleware_claim_a_claude_submit_pack_v1.py
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.mkm_middleware_llm_harness_lib_v1 import utc_now  # noqa: E402

ART = ROOT / "docs/final/artifacts"
OUT_MD = ART / "mkm_middleware_claim_a_claude_submit_pack_v1_latest.md"
OUT_JSON = ART / "mkm_middleware_claim_a_claude_submit_pack_v1_latest.json"
OUT_MIRROR_MD = ROOT / "reports/mkm_middleware_claim_a_claude_submit_pack_v1_latest.md"
REREVIEW = ART / "mkm_middleware_claim_a_claude_rereview_pack_v1_latest.md"
REREVIEW_MIRROR = ROOT / "reports/mkm_middleware_claim_a_claude_rereview_pack_v1_latest.md"

SECRETISH = re.compile(
    r"(?i)("
    r"api[_-]?key\s*[:=]\s*\S+"
    r"|-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----"
    r"|bearer\s+[a-z0-9._\-]{20,}"
    r"|sk-[a-z0-9]{20,}"
    r"|xai-[a-z0-9]{20,}"
    r"|AIza[0-9A-Za-z\-_]{20,}"
    r")"
)

GATE_DEF = (
    "Syntactic egress contract only: min_locked_citations + no_outside_pack_refs "
    "+ hold_mentioned + no_forbidden_substrings + non_empty "
    "(+ adversarial refusal when applicable). NOT semantic answer quality."
)

EGRESS_HERO = (
    "Keep the corpus local. What leaves your boundary: pointers, locked citations, "
    "and a hard HOLD — never the corpus itself."
)
LEGACY_HEADLINE = (
    "Keep the corpus local. Send pointers. Enforce citation scope and a hard HOLD "
    "line before anything leaves your boundary."
)


def _load(p: Path) -> dict[str, Any]:
    if not p.is_file():
        return {}
    return json.loads(p.read_text(encoding="utf-8-sig"))


def _rel(p: Path) -> str:
    try:
        return str(p.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return p.name


def _audit() -> tuple[list[str], list[str], dict[str, Any]]:
    cl = _load(ART / "mkm_middleware_anti_self_grade_checklist_v1_latest.json")
    gem = _load(ART / "mkm_middleware_gemini_hold_gap_diag_v1_latest.json")
    az = _load(ART / "mkm_middleware_claim_a_three_arm_ab_azure_v1_latest.json")
    ol = _load(ART / "mkm_middleware_claim_a_three_arm_ab_v1_latest.json")
    fair = _load(ART / "mkm_middleware_external_baseline_ab_v1_latest.json")
    send = _load(ART / "mkm_middleware_claim_a_send_open_v1_latest.json")
    ingest = _load(ART / "mkm_middleware_blind_rubric_ingest_v1_latest.json")
    filled = _load(ART / "mkm_middleware_blind_rubric_scores_filled_v1_latest.json")

    chk = cl.get("checklist") or {}
    hf = gem.get("live_hold_first_smoke") or {}
    adv_ol = (ol.get("metrics") or {}).get("adversarial") or {}
    adv_az = (az.get("metrics") or {}).get("adversarial") or {}
    n_az = int(adv_az.get("n_adversarial") or 0)
    scored_az = int(adv_az.get("n_scored_C") or 0)
    api_err_az = int(az.get("api_error_count") or 0)
    uniq_c_err = n_az - scored_az
    decomp = az.get("api_error_decomposition") or {}

    prefer_ab = dict(
        Counter(str(s.get("prefer") or "").upper() for s in (filled.get("scores") or []))
    )
    prefer_unblind = ingest.get("prefer_counts") or {}
    key = _load(ART / "mkm_middleware_blind_rubric_key_v1_latest.json")
    a_arm_dist = Counter(m.get("A_arm") for m in (key.get("map") or []))
    b_arm_dist = Counter(m.get("B_arm") for m in (key.get("map") or []))
    plain_n = int(prefer_unblind.get("plain_full") or 0)
    id_n = int(prefer_unblind.get("id_only") or 0)
    blind_n = int(ingest.get("n_scores_complete") or filled.get("pack_n_items") or 0)

    blockers: list[str] = []
    warnings: list[str] = []

    if not hf or int(hf.get("n") or 0) < 12:
        blockers.append("gemini_hold_first live smoke missing or n<12")
    if not gem.get("round_delta_note_ko"):
        blockers.append("HOLD-first round_delta_note_ko missing (0.33 vs 0.25 unexplained)")
    if not az.get("api_error_count_definition"):
        blockers.append("Azure api_error_count_definition missing")
    if str(cl.get("honesty_rev") or "") not in ("1.5", "1.6", "1.7"):
        warnings.append(f"honesty_rev={cl.get('honesty_rev')} (expect 1.7)")
    if cl.get("independent_blind") is True and (cl.get("checklist") or {}).get(
        "blind_scorer_class"
    ) != "third_party_human":
        blockers.append("independent_blind=true but scorer is not third_party_human")
    if not cl.get("commander_full_kit_blind") and not cl.get("independent_blind"):
        if not cl.get("self_accepted_proxy_blind"):
            blockers.append("no disclosed blind class (commander_full_kit / independent / proxy)")
    if cl.get("self_accepted_proxy_blind"):
        warnings.append("self_accepted_proxy_blind=true — disclose; not third-party")
    if send.get("send_gate") != "OPEN":
        warnings.append("send_gate is not OPEN")
    if n_az < 20:
        blockers.append(f"Azure adv n={n_az} < 20")
    if scored_az < n_az:
        warnings.append(
            f"Azure unique-C attrition {uniq_c_err}/{n_az}; "
            f"api_error_count={api_err_az} is arm-calls (≈{uniq_c_err}×3), not 90% task fail"
        )
    if float(
        ((fair.get("by_provider") or {}).get("gemini") or {})
        .get("plain_full", {})
        .get("gate_ok_rate")
        or 0
    ) < 0.5:
        warnings.append("Gemini plain-arm gate residual weak (~0.20)")
    if plain_n > id_n and blind_n >= 20:
        warnings.append(
            f"VALUE-PROP TENSION: unblinded prefer plain_full {plain_n} > id_only {id_n} "
            f"(n={blind_n}) — legacy 'send pointers' usefulness NOT endorsed; "
            "rev 1.7 Hero is egress/security frame only"
        )
    if filled.get("ported_from_proxy_sheet"):
        blockers.append("filled scores still marked ported_from_proxy_sheet")

    onepager = ART / "mkm_middleware_l0_send_ready_onepager_v1_latest.md"
    onepager_txt = (
        onepager.read_text(encoding="utf-8", errors="ignore") if onepager.is_file() else ""
    )
    egress_reframe = (
        "claim frame" in onepager_txt.lower()
        and "egress" in onepager_txt.lower()
        and ("what leaves your boundary" in onepager_txt.lower() or "usefulness-proven" in onepager_txt.lower())
    )
    if not egress_reframe:
        blockers.append(
            "onepager missing rev 1.7 egress Hero/claim frame "
            "(What leaves your boundary… / Claim frame)"
        )

    # Headline orphan reuse (Claude 1.6 residual → distribution nail)
    try:
        from scripts.check_mkm_middleware_headline_reuse_guard_v1 import (  # noqa: WPS433
            write_checklist as _headline_checklist,
        )

        hl = _headline_checklist()
        if not hl.get("ok"):
            blockers.append(
                "headline reuse guard FAIL — corpus/send-pointers without counter-signal"
            )
        snap_hl = {
            "headline_reuse_ok": hl.get("ok"),
            "egress_hero_aligned_on_onepager": hl.get("egress_hero_aligned_on_onepager"),
            "checklist": "docs/final/artifacts/mkm_middleware_headline_reuse_checklist_v1_latest.json",
        }
    except Exception as e:  # noqa: BLE001
        warnings.append(f"headline reuse guard unavailable: {type(e).__name__}")
        snap_hl = {"headline_reuse_ok": None}

    for label, path in (
        ("onepager", ART / "mkm_middleware_l0_send_ready_onepager_v1_latest.md"),
        ("rereview", REREVIEW),
    ):
        if path.is_file() and SECRETISH.search(path.read_text(encoding="utf-8", errors="ignore")):
            blockers.append(f"{label} matches secretish pattern — scrub before submit")

    snap = {
        "honesty_rev": cl.get("honesty_rev"),
        "egress_reframe": egress_reframe,
        "send_gate": send.get("send_gate"),
        "independent_blind": bool(cl.get("independent_blind")),
        "commander_full_kit_blind": bool(cl.get("commander_full_kit_blind")),
        "self_reviewed_full_kit": bool(cl.get("self_reviewed_full_kit")),
        "self_accepted_proxy_blind": bool(cl.get("self_accepted_proxy_blind")),
        "headline_reuse": snap_hl,
        "gate_ok_definition": GATE_DEF,
        "egress_hero": EGRESS_HERO,
        "legacy_headline": LEGACY_HEADLINE,
        "hold_first_round_delta_ko": gem.get("round_delta_note_ko"),
        "gemini_hold_first": {
            "n": hf.get("n"),
            "legacy_hold": (hf.get("legacy_final_line_only") or {}).get("hold_mentioned_rate"),
            "hold_first_hold": (hf.get("hold_first_v1_4") or {}).get("hold_mentioned_rate"),
            "legacy_gate": (hf.get("legacy_final_line_only") or {}).get("gate_ok_rate"),
            "hold_first_gate": (hf.get("hold_first_v1_4") or {}).get("gate_ok_rate"),
            "model": hf.get("model"),
            "generated_at_utc": gem.get("generated_at_utc"),
        },
        "fair_ab": {
            "n": fair.get("n_requested") or fair.get("n"),
            "max_tokens": fair.get("max_tokens"),
            "chars_save": {
                p: (fair.get("by_provider") or {}).get(p, {}).get(
                    "chars_saving_rate_id_only_vs_plain"
                )
                for p in (fair.get("providers") or [])
            },
            "gates": {
                p: {
                    "plain": (fair.get("by_provider") or {})
                    .get(p, {})
                    .get("plain_full", {})
                    .get("gate_ok_rate"),
                    "id_only": (fair.get("by_provider") or {})
                    .get(p, {})
                    .get("id_only", {})
                    .get("gate_ok_rate"),
                }
                for p in (fair.get("providers") or [])
            },
        },
        "adv_ollama": {
            "n_adversarial": adv_ol.get("n_adversarial"),
            "true_block": adv_ol.get("C_true_block"),
            "miss_block": adv_ol.get("C_miss_block"),
            "refused_ok": adv_ol.get("C_refused_ok"),
            "n_scored_C": adv_ol.get("n_scored_C"),
            "provider": ol.get("provider"),
            "note": "Do not compare head-to-head with Azure without n/attrition footnotes",
        },
        "adv_azure": {
            "n_adversarial": n_az,
            "n_scored_C": scored_az,
            "api_error_count_arm_calls": api_err_az,
            "unique_adv_tasks_with_C_api_error": uniq_c_err,
            "api_error_count_definition": az.get("api_error_count_definition"),
            "api_error_decomposition": decomp,
            "true_block": adv_az.get("C_true_block"),
            "miss_block": adv_az.get("C_miss_block"),
            "refused_ok": adv_az.get("C_refused_ok"),
            "provider": az.get("provider"),
            "model": az.get("model"),
            "generated_at_utc": az.get("generated_at_utc"),
            "note": "true_block denom = n_scored_C; not comparable 1:1 to ollama n=30",
        },
        "blind": {
            "n": blind_n,
            "scorer_class": filled.get("scorer") or chk.get("blind_scorer_class"),
            "prefer_blind_labels_AB": prefer_ab,
            "prefer_unblinded_arms": prefer_unblind,
            "ab_side_randomization": {
                "A_arm_distribution": dict(a_arm_dist),
                "B_arm_distribution": dict(b_arm_dist),
                "note_ko": (
                    "A/B are randomized sides per item — prefer A count must NOT equal "
                    "prefer id_only or plain_full. 15/9 vs 10/14 is expected under shuffle, "
                    "not a 1-row ledger bug."
                ),
            },
            "value_prop_tension": {
                "plain_full_prefer": plain_n,
                "id_only_prefer": id_n,
                "plain_share": round(plain_n / max(1, blind_n), 4),
                "headline_challenged": bool(plain_n > id_n),
            },
            "independent_blind": bool(cl.get("independent_blind")),
            "commander_full_kit_blind": bool(cl.get("commander_full_kit_blind")),
            "self_reviewed_full_kit": bool(cl.get("self_reviewed_full_kit")),
        },
        "router_hygiene_not_claim_a": {
            "note": "Separate ledger; w1_pass=false; do not merge into Claim-A headline",
        },
    }
    return blockers, warnings, snap


def _render(
    snap: dict[str, Any], blockers: list[str], warnings: list[str], *, paste_ready: bool
) -> str:
    hf = snap["gemini_hold_first"]
    fair = snap["fair_ab"]
    ol = snap["adv_ollama"]
    az = snap["adv_azure"]
    bl = snap["blind"]
    status = "PASTE_READY" if paste_ready else "DRAFT_NOT_READY"
    lines = [
        f"# Claude submit pack — Claim-A L0 · honesty rev {snap.get('honesty_rev') or '?'} · {status}",
        "",
        "## Security / scope guard",
        "- No secrets · no FULL blind kit · no corpus dump · repo-relative paths only",
        "- Scope: L0 research critique only · not Track A · not live trading · not market GO",
        "",
        "## Paste-ready verdict",
        f"- status: **{status}**",
        f"- send_gate (scoped): `{snap.get('send_gate')}`",
        f"- independent_blind: `{snap.get('independent_blind')}` "
        "(**true only if third_party_human**)",
        f"- commander_full_kit_blind / self_reviewed_full_kit: "
        f"`{snap.get('commander_full_kit_blind')}` / `{snap.get('self_reviewed_full_kit')}`",
        f"- self_accepted_proxy_blind: `{snap.get('self_accepted_proxy_blind')}`",
    ]
    if blockers:
        lines.append("- blockers:")
        for b in blockers:
            lines.append(f"  - {b}")
    if warnings:
        lines.append("- residual warnings:")
        for w in warnings:
            lines.append(f"  - {w}")

    vt = (bl.get("value_prop_tension") or {})
    ab_note = (bl.get("ab_side_randomization") or {}).get("note_ko")
    lines += [
        "",
        "## Metric definitions (read before numbers)",
        f"- **gate_ok**: {snap.get('gate_ok_definition')}",
        "- **api_error_count**: arm-call failures (A/B/C × tasks). "
        "Unique adversarial C attrition = `n_adversarial − n_scored_C` "
        f"(here {az.get('unique_adv_tasks_with_C_api_error')}/{az.get('n_adversarial')}). "
        f"Arm-call total {az.get('api_error_count_arm_calls')} ≈ that unique count × 3 — "
        "**not** 18/20=90% task failure.",
        "",
        "## Hero / claim frame (rev 1.7 · egress · do not bury)",
        f"> {snap.get('egress_hero')}",
        "",
        "**Claim frame:** egress / security boundary only. "
        "Do **not** sell pointer-only answers as usefulness-proven.",
        "",
        f"**Blind usefulness tension (commander Blind unblinded, n={bl.get('n')}):** "
        f"prefer **plain_full {vt.get('plain_full_prefer')}** > "
        f"**id_only {vt.get('id_only_prefer')}** "
        f"(plain share ≈ {vt.get('plain_share')}). "
        "Chars-save / syntactic gate ≠ human prefer for pointer arm. "
        "**Not** market GO; Hero reframes product narrative as egress, not usefulness SLA.",
        "",
        "### Legacy headline (research ledger only — paste with Counter-signal)",
        f"> {snap.get('legacy_headline')}",
        "",
        f"- A/B label tally {bl.get('prefer_blind_labels_AB')} vs unblinded "
        f"{bl.get('prefer_unblinded_arms')}: {ab_note} "
        f"Key A_arm dist={ (bl.get('ab_side_randomization') or {}).get('A_arm_distribution') }.",
        "",
        "## Measured (research · per-signal n · do not merge)",
        f"- Fair external AB · n={fair.get('n')} · max_tokens={fair.get('max_tokens')} · "
        f"chars save≈{fair.get('chars_save')}",
        f"- Fair gates (syntactic): {fair.get('gates')}",
        "  - id_only=1.0 on Azure+Gemini can be expected under syntactic gate; "
        "it is **not** semantic accuracy.",
        f"- Gemini HOLD-first · n={hf.get('n')} · model=`{hf.get('model')}` · "
        f"hold {hf.get('legacy_hold')}→{hf.get('hold_first_hold')} · "
        f"gate {hf.get('legacy_gate')}→{hf.get('hold_first_gate')} · "
        f"run `{hf.get('generated_at_utc')}`",
        f"  - Round delta: {snap.get('hold_first_round_delta_ko')}",
        "",
        "### Adversarial C — report separately (different n / attrition)",
        f"- **Ollama** · n_adv={ol.get('n_adversarial')} scored_C={ol.get('n_scored_C')} · "
        f"true_block={ol.get('true_block')} · miss={ol.get('miss_block')} · "
        f"refused_ok={ol.get('refused_ok')}",
        f"- **Azure** · n_adv={az.get('n_adversarial')} scored_C={az.get('n_scored_C')} · "
        f"unique_C_api_error={az.get('unique_adv_tasks_with_C_api_error')} · "
        f"api_error_arm_calls={az.get('api_error_count_arm_calls')} · "
        f"true_block={az.get('true_block')} (denom=scored_C) · miss={az.get('miss_block')} · "
        f"model=`{az.get('model')}`",
        "  - Do **not** read Azure true_block=1.0 as stronger than Ollama 0.87 without footnotes.",
        "",
        f"- Blind detail · n={bl.get('n')} · scorer=`{bl.get('scorer_class')}` · "
        f"independent_blind={bl.get('independent_blind')} · "
        f"commander_full_kit={bl.get('commander_full_kit_blind')} "
        "(prefer tallies: see Hero / Blind tension above — not buried here only)",
        "",
        "## Closed in 1.5–1.6 · lighted in 1.7",
        "1–5. Labels / api_error / HOLD-first delta / gate_ok / adv footnotes — closed in 1.5.",
        "6. **Selective emphasis:** plain_full Blind prefer lighted beside headline (1.6).",
        "7. **A/B vs arm tallies:** explained via per-item side randomization (not a 1-row bug).",
        "8. **Egress Hero reframe:** external paste uses boundary/HOLD frame; "
        "legacy 'Send pointers' usefulness claim withdrawn from Hero (1.7).",
        "",
        "## Ask Claude",
        "Re-critique honesty rev **1.7** egress Hero reframe + retained Blind usefulness tension. "
        "**Do not** certify market GO / Track A / product SLA / L2-lens=compression success.",
        "",
        "## Artifact index",
        "- `docs/final/artifacts/mkm_middleware_claim_a_claude_submit_pack_v1_latest.md`",
        "- `docs/final/artifacts/mkm_middleware_anti_self_grade_checklist_v1_latest.json`",
        "- `docs/final/artifacts/mkm_middleware_gemini_hold_gap_diag_v1_latest.json`",
        "- `docs/final/artifacts/mkm_middleware_claim_a_three_arm_ab_azure_v1_latest.json`",
        "- `docs/final/artifacts/mkm_middleware_l0_send_ready_onepager_v1_latest.md`",
        "- `docs/final/artifacts/mkm_middleware_headline_reuse_checklist_v1_latest.json`",
        "",
        f"generated_at_utc: {utc_now()}",
        "schema: mkm_middleware_claim_a_claude_submit_pack_v1",
        "",
    ]
    return "\n".join(lines)


def _render_rereview(snap: dict[str, Any], *, paste_ready: bool) -> str:
    status = "PASTE_READY" if paste_ready else "DRAFT_NOT_READY"
    vt = (snap.get("blind") or {}).get("value_prop_tension") or {}
    return "\n".join(
        [
            f"## Claude 제출 팩 — honesty rev 1.7 ({status})",
            "",
            "### Closed (1.5–1.6)",
            "1–7: labels · api_error · HOLD delta · gate_ok · adv footnotes · "
            "selective emphasis · A/B randomization.",
            "",
            "### New in 1.7",
            "8. **Egress Hero** — external/SEND paste uses:",
            f"> {snap.get('egress_hero')}",
            "",
            "Claim frame = egress/security. Blind usefulness tension retained "
            f"(plain_full {vt.get('plain_full_prefer')} > id_only {vt.get('id_only_prefer')}). "
            "Legacy 'Send pointers' usefulness claim is **not** the Hero.",
            "",
            "### Next-step nails",
            "1. **Headline reuse guard** — `py scripts/check_mkm_middleware_headline_reuse_guard_v1.py`",
            "2. **Optional** third-party Blind / different rubric (independent_blind still false)",
            "3. **Not** L2 lens = compression success · **Not** market GO · **Not** Track A",
            "",
            "### Paste",
            "`docs/final/artifacts/mkm_middleware_claim_a_claude_submit_pack_v1_latest.md`",
            "",
            "No market GO / Track A / product SLA.",
            "",
            f"generated_at_utc: {utc_now()}",
            "schema: mkm_middleware_claim_a_claude_rereview_pack_v1",
            "",
        ]
    )


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--force-draft", action="store_true")
    ap.add_argument("--allow-azure-small", action="store_true")
    args = ap.parse_args()

    blockers, warnings, snap = _audit()
    if args.allow_azure_small:
        blockers = [b for b in blockers if "Azure adv n=" not in b]
    paste_ready = len(blockers) == 0
    if blockers and not args.force_draft:
        paste_ready = False

    if blockers and args.force_draft:
        paste_ready = False

    md = _render(snap, blockers, warnings, paste_ready=paste_ready)
    if SECRETISH.search(md):
        print("ERR: generated pack matched secretish pattern", file=sys.stderr)
        return 1
    OUT_MD.write_text(md, encoding="utf-8")
    OUT_MIRROR_MD.write_text(md, encoding="utf-8")

    rr = _render_rereview(snap, paste_ready=paste_ready)
    REREVIEW.write_text(rr, encoding="utf-8")
    REREVIEW_MIRROR.write_text(rr, encoding="utf-8")

    meta = {
        "schema": "mkm_middleware_claim_a_claude_submit_pack_v1",
        "version": "1.7.0",
        "generated_at_utc": utc_now(),
        "paste_ready": paste_ready,
        "blockers": blockers,
        "warnings": warnings,
        "snapshot": snap,
        "out_md": _rel(OUT_MD),
        "rereview_md": _rel(REREVIEW),
    }
    OUT_JSON.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if blockers and not args.force_draft:
        print(f"DRAFT_NOT_READY: {OUT_MD}")
        for b in blockers:
            print(f"BLOCKER: {b}")
        return 2
    print(f"{'PASTE_READY' if paste_ready else 'DRAFT'}: {OUT_MD}")
    return 0 if paste_ready else 2


if __name__ == "__main__":
    raise SystemExit(main())
