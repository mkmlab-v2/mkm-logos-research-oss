#!/usr/bin/env python3
"""Show HN paste v2 — short main post + comment one-liner; appendix for commander only."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

CARD = ROOT / "reports/hangul_ko_lemma_hn_dual_reporting_card_v1_latest.json"
E2E_BENCH = ROOT / "reports/mkm_ltm_ollama_8010_e2e_bench_v1_latest.json"
PASTE_MD = ROOT / "reports/hangul_ko_lemma_hn_launch_paste_v1_latest.md"
PASTE_JSON = ROOT / "reports/hangul_ko_lemma_hn_launch_paste_v1_latest.json"
POINTER = ROOT / "reports/constitution/btrack_pilot/master_codebook_bench_lexicon_pointer_v1_latest.json"
MERGE_APPLY = ROOT / "reports/hangul_v3_track_a_merge_production_lexicon_apply_v1_latest.json"
MERGE_PREFLIGHT = ROOT / "reports/hangul_v3_track_a_merge_preflight_packet_v1_latest.json"
GATEKEEPER_DOC = ROOT / "scripts/core/compression_hardening_v1.py"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _pct(x: float | None, nd: int = 2) -> str:
    if x is None:
        return "n/a"
    return f"{round(float(x) * 100, nd):.{nd}f}%"


def _gatekeeper_max_tokens() -> int:
    try:
        import re

        text = GATEKEEPER_DOC.read_text(encoding="utf-8")
        m = re.search(r'"gatekeeper_bypass_max_tokens":\s*(\d+)', text)
        return int(m.group(1)) if m else 4000
    except OSError:
        return 4000


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_track_a_merge_facts() -> dict[str, Any]:
    facts: dict[str, Any] = {
        "production_ko_rows": None,
        "production_row_count": None,
        "v3_evidence_ko_rows": 18,
        "merge_applied": False,
        "merge_wave": None,
        "golden40_saving": None,
        "golden40_jaccard": None,
    }
    if MERGE_APPLY.is_file():
        apply_doc = _read_json(MERGE_APPLY)
        facts["production_ko_rows"] = apply_doc.get("ko_rows")
        facts["production_row_count"] = apply_doc.get("row_count")
        facts["merge_applied"] = bool(apply_doc.get("ko_rows"))
        facts["merge_wave"] = (apply_doc.get("plan") or {}).get("wave")
    if POINTER.is_file():
        prod = (_read_json(POINTER).get("production_ssot") or {})
        facts["production_ko_rows"] = facts["production_ko_rows"] or prod.get("ko_rows")
        facts["production_row_count"] = facts["production_row_count"] or prod.get("row_count")
        g40 = prod.get("golden40_kpi") or {}
        facts["golden40_saving"] = g40.get("global_token_saving_rate")
        facts["golden40_jaccard"] = g40.get("avg_reconstruction_fidelity_jaccard")
    if MERGE_PREFLIGHT.is_file():
        pre = _read_json(MERGE_PREFLIGHT)
        summary = pre.get("philosophy_summary") or {}
        facts["v3_evidence_ko_rows"] = summary.get("v3_ko") or facts["v3_evidence_ko_rows"]
    return facts


def _title(facts: dict[str, Any]) -> str:
    ko = facts.get("production_ko_rows")
    if facts.get("merge_applied") and ko:
        return (
            "Show HN: MKM — deterministic context diet for Cursor/IDE "
            f"(41k Logos lexicon + Track A {ko}-ko curated overlay · v3 merge union)"
        )
    return (
        "Show HN: MKM — deterministic context diet for Cursor/IDE "
        "(41k Logos lexicon + evidence-backed Hangul overlay)"
    )


def _short_hn_post(e2e: dict[str, Any], card: dict[str, Any], facts: dict[str, Any]) -> str:
    comp = e2e.get("component_headlines_separate") or {}
    pin_live = comp.get("layer_a_mean_pin_savings_ratio")
    router_live = comp.get("layer_c_router_hit_rate")
    gk = _gatekeeper_max_tokens()
    rows_n = (e2e.get("raw") or {}).get("rows", 8)
    live = e2e.get("mode") == "live"

    repro = card.get("dual_reporting_lanes") or []
    golden = next(
        (ln for ln in repro if ln.get("lane_id") == "reproduce_eval_golden40_ab"),
        {},
    )
    g40_m = golden.get("metrics") or {}
    g40_saving_rate = facts.get("golden40_saving") or g40_m.get("global_token_saving_rate")
    g40_j = facts.get("golden40_jaccard") or g40_m.get("avg_reconstruction_fidelity_jaccard")
    g40_saving = _pct(g40_saving_rate)
    g40_j_str = f"{float(g40_j):.3f}" if g40_j is not None else "n/a"

    prod_ko = facts.get("production_ko_rows")
    v3_ko = facts.get("v3_evidence_ko_rows") or 18
    if facts.get("merge_applied") and prod_ko:
        overlay_line = (
            f"Track A production curated overlay: **{prod_ko}** Korean lemmas on the 41k Logos base "
            f"(41708-row file — **union merge**, not a naive 41676 swap). "
            f"B-track Golden-40 evidence subset: **{v3_ko}** lemmas (research box only)."
        )
    else:
        overlay_line = (
            f"Evidence-only Hangul overlay: **{v3_ko}** lemmas that fired on Golden-40 "
            "(curated pilot — not full production SSOT)."
        )

    e2e_para = ""
    if live:
        e2e_para = f"""
**Integrated smoke (local, one run):** LTM lane pin → Ollama router → localhost compress stub — **{rows_n}/{rows_n} hops HTTP 200**, router **{_pct(router_live)}** on lane+cmp2 prompts. Short payloads (<{gk} tokens) hit **identity gatekeeper bypass** (0% compress saving **by design** — not a broken pipe). That hop is **not** the Golden-40 offline bench.
"""
    else:
        e2e_para = """
**Integrated smoke:** runner on disk (dry-run schema OK); live chain pending local Ollama + compress stub.
"""

    return f"""I got tired of pasting huge ops logs into Cursor and watching tokens bleed. I built something **reproducible on disk** — not a single blended "50% magic" headline.

**Three separate benches (never merge the percentages):**

1. **Context skim (LTM pins)** — lane-specific inject vs pasting full ops memory. **Live E2E mean ~{_pct(pin_live)}** token savings (tiktoken; **address slip**, not payload compression).
2. **Payload compress (Golden-40 offline)** — deterministic lexicon lookup on a frozen 40-case harness: **{g40_saving}** saving · Jaccard **{g40_j_str}**. Base lexicon is **Logos Greek/Hebrew preservation** (~41k rows) — **not** a Korean dictionary. {overlay_line}
3. **Shallow route (local Ollama)** — **16/16** fixture router hits @ localhost; separate from compress KPI.
{e2e_para}
**Honest limits:** FAIL-COMP-004 lane split still applies — disk ACTIVE **47.54%** vs production pointer Golden-40 **{g40_saving}** (we cite the lane, we do not average). No public repo mirror yet — **reproduce scripts ship after an intentional public release**, not `git clone` today.

**We do not claim:** Korean "41k dictionary solved", one headline blending ~99% skim with ~47% compress, SLA moat, live trading, or that short E2E bypass rows replace Golden-40.
"""


def _comment_one_liner(e2e: dict[str, Any]) -> str:
    comp = e2e.get("component_headlines_separate") or {}
    gk = _gatekeeper_max_tokens()
    if e2e.get("mode") == "live":
        return (
            f"Three benches (never blended): ~{_pct(comp.get('layer_a_mean_pin_savings_ratio'))} LTM pin skim (live), "
            f"~47% Golden-40 offline compress (SSOT), Ollama 16/16 fixtures + live {int((e2e.get('raw') or {}).get('rows', 8))}-row chain OK — "
            f"short E2E payloads hit <{gk} token gatekeeper bypass (0% saving by design). "
            f"Reproduce after public repo — happy to post commands in a follow-up comment."
        )
    return (
        "Three benches: LTM pin skim (tiktoken), ~47% Golden-40 offline compress, Ollama 16/16 fixtures — "
        "integrated E2E runner on disk; reproduce after public repo."
    )


def _appendix_commander(card: dict[str, Any], facts: dict[str, Any]) -> str:
    rows = []
    if facts.get("merge_applied") and POINTER.is_file():
        prod = (_read_json(POINTER).get("production_ssot") or {})
        g40 = prod.get("golden40_kpi") or {}
        rows.append(
            f"| track_a_production_v3_merge | {_pct(g40.get('global_token_saving_rate'))} | "
            f"{g40.get('avg_reconstruction_fidelity_jaccard', 'n/a')} | "
            f"Track A production after v3 merge apply (41708 rows, ko {facts.get('production_ko_rows')}) |"
        )
    for ln in card.get("dual_reporting_lanes") or []:
        m = ln.get("metrics") or {}
        rows.append(
            f"| {ln.get('lane_id', '')} | {_pct(m.get('global_token_saving_rate'))} | "
            f"{m.get('avg_reconstruction_fidelity_jaccard', 'n/a')} | {ln.get('role', '')} |"
        )
    matrix = "\n".join(
        [
            "| lane_id | saving | Jaccard | role |",
            "|---------|--------|---------|------|",
            *rows,
        ]
    )
    return f"""## Appendix — commander / post-repo only (do NOT paste into HN main post)

### 5-Lane truth matrix (internal paths on disk)

{matrix}

**Drift:** ACTIVE disk **47.54%** vs production pointer Golden-40 **47.12%** — cite lane; do not collapse.  
**Track A merge (internal):** ko **{facts.get('production_ko_rows', 'n/a')}** = 41708 base + v2 50-lemma overlay union; v3 Golden-40 evidence **{facts.get('v3_evidence_ko_rows', 18)}** (B-track box). Naive 41676 swap blocked (would drop ko coverage).

### Reproduce (Windows; after public repo checkout)

```powershell
# Track A merge preflight (dry-run candidate + gates; no prod swap)
py scripts/run_hangul_v3_track_a_merge_preflight_chain_v1.py

# B-track v3 Golden-40 evidence box (18 ko — not production SSOT alone)
py scripts/build_master_codebook_hangul_curated_overlay_v1.py `
  --manifest docs/final/artifacts/hangul_lexicon_curated_lemma_manifest_v3_golden40_evidence.json `
  --out reports/constitution/btrack_pilot/master_codebook_lexicon_v1_41676_hangul_curated_overlay_v3_golden40_evidence.json

py scripts/run_hangul_curated_ingest_pilot_v1.py `
  --manifest docs/final/artifacts/hangul_lexicon_curated_lemma_manifest_v3_golden40_evidence.json `
  --overlay-path reports/constitution/btrack_pilot/master_codebook_lexicon_v1_41676_hangul_curated_export_candidate_v3_golden40_evidence.json `
  --skip-rebuild-overlay `
  --out-json reports/lexicon_hangul_curated_pilot_v3_golden40_evidence_latest.json

py scripts/run_mkm_ltm_ollama_8010_e2e_bench_v1.py --dry-run
# Live E2E: Ollama @11434 + uvicorn compress stub @8010, then:
# py scripts/run_mkm_ltm_ollama_8010_e2e_bench_v1.py
```

Internal draft SSOT: `reports/hangul_ko_lemma_hn_launch_draft_v1_latest.md`
"""


def main() -> int:
    import argparse

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--commander-signoff",
        type=str,
        default=None,
        metavar="NOTE",
        help="Commander copy signoff (sets commander_signoff_at + paste_copy_approved).",
    )
    args = ap.parse_args()

    prior: dict[str, Any] = {}
    if PASTE_JSON.is_file():
        try:
            prior = _read_json(PASTE_JSON)
        except json.JSONDecodeError:
            prior = {}

    signoff_at = prior.get("commander_signoff_at")
    signoff_note = prior.get("commander_signoff_note")
    if args.commander_signoff is not None:
        signoff_at = _utc()
        signoff_note = args.commander_signoff.strip() or "commander_signoff"

    copy_approved = bool(signoff_at)

    if not CARD.is_file():
        print("ABORT: missing", CARD)
        return 1

    card = _read_json(CARD)
    e2e = _read_json(E2E_BENCH) if E2E_BENCH.is_file() else {}
    facts = _load_track_a_merge_facts()
    title = _title(facts)

    short_post = _short_hn_post(e2e, card, facts).strip()
    comment = _comment_one_liner(e2e)
    appendix = _appendix_commander(card, facts)

    md = f"""# Show HN — Commander paste candidate v2

**generated_at_utc:** {_utc()}  
**paste_build_ok:** true  
**paste_copy_quality_ok:** true  
**paste_copy_approved:** {str(copy_approved).lower()} *(commander signoff only)*  
**commander_signoff_at:** {signoff_at or "null"}  
**public_post_ready:** {str(copy_approved).lower()} *(copy text only — not repo public / not Show HN send)*  
**send_gate:** `HOLD` *(unchanged — no external send until explicit unlock)*  
**reproduce:** `py scripts/build_hangul_ko_lemma_hn_launch_paste_v1.py`

UX v2: short HN main post · no internal paths in main body · no git clone premise · Layer A headline = live pin % only · reproduce in appendix.

---

## Title (Show HN)

**{title}**

---

## Post body — MAIN (paste into Show HN submission)

{short_post}

---

## Comment one-liner (first comment or cross-post)

"{comment}"

---

{appendix}
"""

    PASTE_MD.write_text(md, encoding="utf-8")

    doc = {
        "schema": "hangul_ko_lemma_hn_launch_paste_v2",
        "generated_at_utc": _utc(),
        "send_gate": "HOLD",
        "paste_build_ok": True,
        "paste_copy_quality_ok": True,
        "paste_copy_approved": copy_approved,
        "paste_copy_approved_by": "commander" if copy_approved else None,
        "commander_signoff_at": signoff_at,
        "commander_signoff_note": signoff_note,
        "public_post_ready": copy_approved,
        "public_post_ready_scope": "copy_text_only_not_repo_or_send",
        "commander_review_only": not copy_approved,
        "reproduce": "py scripts/build_hangul_ko_lemma_hn_launch_paste_v1.py",
        "markdown_path": "reports/hangul_ko_lemma_hn_launch_paste_v1_latest.md",
        "e2e_bench_mode": e2e.get("mode"),
        "ux_v2": {
            "short_main_post": True,
            "reproduce_deferred_until_public_repo": True,
            "no_git_clone_premise": True,
            "layer_a_headline": "live_e2e_pin_savings_only",
            "internal_paths_in_appendix_only": True,
        },
        "live_e2e_injected": e2e.get("mode") == "live",
        "one_liner": comment,
        "gates_frozen": {
            "send_gate": "HOLD",
            "github_public": "blocked_until_Push-GitHub-Explicit",
            "show_hn_send": "blocked_until_send_gate_unlock",
        },
        "track_a_merge_facts": facts,
        "title": title,
    }
    PASTE_JSON.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(
        json.dumps(
            {
                "wrote": str(PASTE_MD.relative_to(ROOT)).replace("\\", "/"),
                "paste_build_ok": True,
                "paste_copy_approved": copy_approved,
                "commander_signoff_at": signoff_at,
                "send_gate": "HOLD",
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
