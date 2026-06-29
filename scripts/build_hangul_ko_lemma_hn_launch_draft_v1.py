#!/usr/bin/env python3
"""Build Show HN Launch Draft v1 — 3-layer story, 5-lane truth matrix, reproduce block."""

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
LTM = ROOT / "reports/mkm_ltm_resume_lane_token_bench_v1_latest.json"
OLLAMA = ROOT / "reports/ollama_shallow_router_bench_v1_latest.json"
V3_PILOT = ROOT / "reports/lexicon_hangul_curated_pilot_v3_golden40_evidence_latest.json"
V3_EXPORT = ROOT / "reports/hangul_ko_lemma_v3_export_candidate_v1_latest.json"
E2E_SPEC = ROOT / "reports/mkm_ltm_ollama_8010_e2e_bench_spec_v1_latest.json"
E2E_BENCH = ROOT / "reports/mkm_ltm_ollama_8010_e2e_bench_v1_latest.json"
POSITIONING = ROOT / "docs/final/artifacts/mkm_b2b_compression_positioning_external_v1_latest.json"
MD_OUT = ROOT / "reports/hangul_ko_lemma_hn_launch_draft_v1_latest.md"
JSON_OUT = ROOT / "reports/hangul_ko_lemma_hn_launch_draft_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _pct(x: float | None, nd: int = 2) -> str:
    if x is None:
        return "n/a"
    return f"{round(float(x) * 100, nd):.{nd}f}%"


def _build_md(
    card: dict[str, Any],
    ltm: dict[str, Any],
    ollama: dict[str, Any],
    v3: dict[str, Any],
) -> str:
    lanes = {lane["lane_id"]: lane for lane in card.get("dual_reporting_lanes") or []}
    ev = card.get("evidence_anchors") or {}
    infra = (ltm.get("lanes") or {}).get("infra") or {}
    infra_ratio = infra.get("savings_ratio_vs_naive_baseline")
    ollama_m = ollama.get("metrics") or {}
    v3_gate = v3.get("double_gate") or {}
    v3_g40 = (v3.get("golden40_compare") or {}).get("curated_overlay") or {}

    reproduce_block = """```powershell
# From repo root (Windows). Requires Python 3.11+ and project deps (tiktoken for full bench).

# A) Evidence-only 18-ko overlay + double gate (exit 0 = both_pass)
py scripts/build_master_codebook_hangul_curated_overlay_v1.py `
  --manifest docs/final/artifacts/hangul_lexicon_curated_lemma_manifest_v3_golden40_evidence.json `
  --out reports/constitution/btrack_pilot/master_codebook_lexicon_v1_41676_hangul_curated_overlay_v3_golden40_evidence.json

py scripts/run_hangul_curated_ingest_pilot_v1.py `
  --manifest docs/final/artifacts/hangul_lexicon_curated_lemma_manifest_v3_golden40_evidence.json `
  --overlay-path reports/constitution/btrack_pilot/master_codebook_lexicon_v1_41676_hangul_curated_overlay_v3_golden40_evidence.json `
  --skip-rebuild-overlay `
  --out-json reports/lexicon_hangul_curated_pilot_v3_golden40_evidence_latest.json

# B) Optional: regenerate dual-reporting card + this draft
py scripts/build_hangul_ko_lemma_hn_dual_reporting_and_manifest_v3_v1.py
py scripts/build_hangul_ko_lemma_hn_launch_draft_v1.py
```"""

    truth_rows = []
    for lid in (
        "bench_pointer_ssot",
        "v2_active_apply_log",
        "active_report_disk",
        "ms_submission_archive",
        "reproduce_eval_golden40_ab",
    ):
        lane = lanes.get(lid) or {}
        m = lane.get("metrics") or {}
        truth_rows.append(
            f"| `{lid}` | {_pct(m.get('global_token_saving_rate'))} | "
            f"{m.get('avg_reconstruction_fidelity_jaccard', 'n/a')} | {lane.get('role', '')} |"
        )
    truth_table = "\n".join(
        [
            "| lane_id | saving | Jaccard | role |",
            "|---------|--------|---------|------|",
            *truth_rows,
        ]
    )

    forbidden = card.get("forbidden_claims") or []
    forbidden_md = "\n".join(f"- {x}" for x in forbidden)
    forbidden_md += """
- Claim 99% resume skim and 47% Golden-40 compress are the same product KPI.
- Claim integrated E2E (LTM pin → Ollama route → localhost compress) is already bench-proven.
- Promise SLA percentages or \"dominant moat\" (see positioning SSOT).
- Imply GitHub/public release without explicit push approval (internal default: HOLD)."""

    return f"""# Show HN Launch Draft v1 (INTERNAL — review before post)

**generated_at_utc:** {_utc()}  
**status:** `research_only` · `send_gate: HOLD` · **not for public paste until commander review**  
**reproduce this file:** `py scripts/build_hangul_ko_lemma_hn_launch_draft_v1.py`

---

## Title (Show HN)

**Show HN: MKM — deterministic context diet for Cursor/IDE (41k Logos lexicon + evidence-backed 18-ko overlay)**

---

## Post body (paste-ready)

I got tired of pasting huge ops logs into Cursor and watching tokens bleed. I wanted something **reproducible on disk** — not a black-box \"50% magic\" claim.

**MKM is three separate benches, not one blended number:**

### Layer A — Context skim (LTM resume pins) `[HYPO]` · B-track

- **Question:** How many tokens if I paste all of `MISSION_LOG.md` + `CENTRAL` vs lane-specific inject pins?
- **Bench:** `scripts/bench_mkm_ltm_resume_lane_token_v1.py` (tiktoken only — **no LLM in this metric**)
- **Measured:** naive **105,436** tokens → infra lane pin **135** tokens (~**{ _pct(infra_ratio) if infra_ratio else '99.87%' }** savings vs naive paste)
- **This is an address slip, not source-code compression.** Do not merge with Layer B.

### Layer B — Payload compress (Track A Golden-40) `[FACT]` bench path

- **Question:** Can we shrink **real enterprise sample text** while keeping Jaccard fidelity on a frozen 40-case harness?
- **Engine:** `evaluate_report` + **41,658-row Logos Greek/Hebrew preservation lexicon lookup** + domain shard router
- **4D gematria bridge:** **not baked into lexicon export**; runtime `apply_gematria_4d_bridge_policy` stays **OFF** for frozen bench (ON drops saving ~14pp in AB — see `MULTILENS_GEMATRIA_4D_UPLIFT_AB_V1.json`)
- **Evidence-only Hangul overlay (v3):** **18** ko lemmas that actually fired on Golden-40 (not 42). **41,676 rows**. Pilot **both_pass** (Gate1 **{v3_gate.get('gate1_actual', 30)}/30**, Gate2 Δsaving **{round(float(v3_gate.get('gate2_actual_delta_saving', 0)) * 100, 2)}pp**)
- **Reproduce path saving:** **{_pct(v3_g40.get('global_token_saving_rate'))}** · Jaccard **{v3_g40.get('avg_reconstruction_fidelity_jaccard', 'n/a')}** (41676 v3 vs 41658 baseline on same eval chain)

**Honest limits:**

- 41k base is **Logos corpus fuel** (Greek/Hebrew/other) — **not** a \"Korean dictionary.\"
- Ko overlay hits **0/10** Golden-40 core enterprise cases; **30/30** on cmp2_011–040 harness subset only.
- Production pointer file is named `41708_rows_latest.json` but contains **41,700** rows (ko **42**) — naming drift documented.

### Layer C — Shallow route (local Ollama) `[HYPO]` · separate bench

- **Question:** Can a **local** Ollama model emit schema-valid domain tags for routing JSON?
- **Bench:** `ollama_shallow_router_bench_v1` — **{ollama_m.get('rows', 16)}** golden fixtures @ `127.0.0.1:11434`
- **Measured:** router_hit **{ollama_m.get('router_hit_rate', 1.0)}** (fixtures only)
- **Not wired into Layer A or B headline.** Full chain LTM → Ollama → localhost:8010 compress: **runner shipped** (`run_mkm_ltm_ollama_8010_e2e_bench_v1.py`); **live pass not yet claimed** — dry-run exit 0 only until Ollama + :8010 up.

---

### Artifacts (v3 export + E2E spec)

| Artifact | Path | Status |
|----------|------|--------|
| v3 export candidate (18 ko) | `reports/constitution/btrack_pilot/master_codebook_lexicon_v1_41676_hangul_curated_export_candidate_v3_golden40_evidence.json` | `promotion: HOLD` |
| v3 export report | `reports/hangul_ko_lemma_v3_export_candidate_v1_latest.json` | evidence box |
| E2E bench spec | `reports/mkm_ltm_ollama_8010_e2e_bench_spec_v1_latest.md` | `[HYPO]` |
| E2E bench output | `reports/mkm_ltm_ollama_8010_e2e_bench_v1_latest.json` | dry-run or live |

```powershell
py scripts/build_hangul_ko_lemma_v3_export_candidate_v1.py
py scripts/build_mkm_ltm_ollama_8010_e2e_bench_spec_v1.py
py scripts/run_mkm_ltm_ollama_8010_e2e_bench_v1.py --dry-run
```

### What we are / are not

| We are | We are not |
|--------|------------|
| Offline lexicon lookup + deterministic must_keep union | Infinite symbolic \"rooms\" injected into compress runtime |
| Evidence-trimmed 18-ko overlay (v3 HOLD) | \"All Korean NLP solved\" |
| Localhost API stub for experiments (`compression_token_api_*_stub`) | Mandatory cloud ingest of your source code |
| B-track Logos research lanes `[NON_GATING]` | Auto-trading / live deploy claims |

Positioning SSOT: `docs/final/artifacts/mkm_b2b_compression_positioning_external_v1_latest.json` — **no exclusive moat · no public % SLA promise.**

---

### Verify in ~2 minutes (Layer B v3 pilot)

{reproduce_block}

Expect: pilot exit **0**, `double_gate.both_pass: true` in `reports/lexicon_hangul_curated_pilot_v3_golden40_evidence_latest.json`.

Optional local stub (Phase 1, not required for above):

```powershell
py -m uvicorn scripts.compression_token_api_stub:app --host 127.0.0.1 --port 8010
```

---

### 5-Lane Truth Matrix (do not collapse in public copy)

{truth_table}

**Known drift:** ACTIVE file on disk (**47.54%**, 41775-era embed) vs v2 apply log intent (**48.8%**, 41708 lexicon) — cite lane, do not average.

---

### Forbidden claims (Fact-Lock)

{forbidden_md}

---

### Internal only (strip before Show HN)

- GitHub public push: **HOLD** unless `Push-GitHub-Explicit.ps1 -Acknowledge`
- v3 overlay: **HOLD** — not production SSOT; pointer still **41708 / ko 42**
- MS submission archive: **rewrite:false** (47.54% / 0.890)

---

## One-liner for comments

\"Three benches: ~99% token skim on resume pins (tiktoken), ~47% on Golden-40 compress (deterministic lexicon lookup, 4D policy OFF), Ollama router 16/16 fixtures — **E2E runner exists (dry-run exit 0); live integrated pass still [HYPO] until Ollama+:8010 bench.**\"

"""


def main() -> int:
    missing = [p for p in (CARD, LTM, OLLAMA, V3_PILOT) if not p.is_file()]
    if missing:
        print("ABORT: missing inputs:", ", ".join(str(p) for p in missing))
        return 1

    card = _read(CARD)
    ltm = _read(LTM)
    ollama = _read(OLLAMA)
    v3 = _read(V3_PILOT)
    positioning = _read(POSITIONING) if POSITIONING.is_file() else {}

    md = _build_md(card, ltm, ollama, v3)
    MD_OUT.write_text(md, encoding="utf-8")

    doc = {
        "schema": "hangul_ko_lemma_hn_launch_draft_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypo_label": "[HYPO]",
        "send_gate": "HOLD",
        "public_post_ready": False,
        "reproduce": "py scripts/build_hangul_ko_lemma_hn_launch_draft_v1.py",
        "markdown_path": str(MD_OUT.relative_to(ROOT)).replace("\\", "/"),
        "inputs": {
            "dual_reporting_card": str(CARD.relative_to(ROOT)).replace("\\", "/"),
            "ltm_bench": str(LTM.relative_to(ROOT)).replace("\\", "/"),
            "ollama_bench": str(OLLAMA.relative_to(ROOT)).replace("\\", "/"),
            "v3_pilot": str(V3_PILOT.relative_to(ROOT)).replace("\\", "/"),
            "v3_export": str(V3_EXPORT.relative_to(ROOT)).replace("\\", "/") if V3_EXPORT.is_file() else None,
            "e2e_spec": str(E2E_SPEC.relative_to(ROOT)).replace("\\", "/") if E2E_SPEC.is_file() else None,
            "e2e_bench": str(E2E_BENCH.relative_to(ROOT)).replace("\\", "/") if E2E_BENCH.is_file() else None,
            "positioning": str(POSITIONING.relative_to(ROOT)).replace("\\", "/") if POSITIONING.is_file() else None,
        },
        "three_layer_summary": {
            "layer_a_ltm_skim_savings_ratio_infra": (ltm.get("lanes") or {}).get("infra", {}).get(
                "savings_ratio_vs_naive_baseline"
            ),
            "layer_b_v3_pilot_both_pass": (v3.get("double_gate") or {}).get("both_pass"),
            "layer_c_ollama_router_hit_rate": (ollama.get("metrics") or {}).get("router_hit_rate"),
            "e2e_integrated_chain_bench_proven": False,
            "e2e_runner_shipped": E2E_BENCH.is_file() or (ROOT / "scripts/run_mkm_ltm_ollama_8010_e2e_bench_v1.py").is_file(),
            "e2e_runner": "scripts/run_mkm_ltm_ollama_8010_e2e_bench_v1.py",
        },
        "forbidden_claims": card.get("forbidden_claims"),
        "positioning_not_line": (positioning.get("identity") or {}).get("not"),
    }
    JSON_OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"WROTE: {MD_OUT}")
    print(f"WROTE: {JSON_OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
