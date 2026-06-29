#!/usr/bin/env python3
"""Build 1-page [HYPO] E2E bench spec: LTM resume pin → Ollama route → localhost:8010 compress."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

LTM = ROOT / "reports/mkm_ltm_resume_lane_token_bench_v1_latest.json"
OLLAMA = ROOT / "reports/ollama_shallow_router_bench_v1_latest.json"
V3_EXPORT = ROOT / "reports/hangul_ko_lemma_v3_export_candidate_v1_latest.json"
HN_DRAFT = ROOT / "reports/hangul_ko_lemma_hn_launch_draft_v1_latest.json"
MD_OUT = ROOT / "reports/mkm_ltm_ollama_8010_e2e_bench_spec_v1_latest.md"
JSON_OUT = ROOT / "reports/mkm_ltm_ollama_8010_e2e_bench_spec_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rel(p: Path) -> str:
    return str(p.relative_to(ROOT)).replace("\\", "/")


def _pct(x: float | None) -> str:
    if x is None:
        return "n/a"
    return f"{round(float(x) * 100, 2)}%"


def _build_md(ltm: dict[str, Any], ollama: dict[str, Any], v3: dict[str, Any]) -> str:
    infra = (ltm.get("lanes") or {}).get("infra") or {}
    ollama_m = ollama.get("metrics") or {}
    v3_metrics = v3.get("metrics_snapshot") or {}

    return f"""# MKM LTM × Ollama × 8010 E2E Bench Spec v1 `[HYPO]`

**generated_at_utc:** {_utc()}  
**status:** `research_only` · `send_gate: HOLD` · **runner shipped — live requires Ollama + :8010**  
**reproduce spec:** `py scripts/build_mkm_ltm_ollama_8010_e2e_bench_spec_v1.py`  
**reproduce bench (dry-run):** `py scripts/run_mkm_ltm_ollama_8010_e2e_bench_v1.py --dry-run`

---

## Problem statement

Layers A/B/C pass **separate** benches today. HN draft discloses **E2E not bench-proven**. This spec defines the **single-chain** experiment to close that gap without collapsing KPIs.

| Layer | Today (component) | This E2E stage |
|-------|-------------------|----------------|
| A LTM skim | ~{_pct(infra.get('savings_ratio_vs_naive_baseline'))} token savings vs naive paste (tiktoken) | **Input size** after lane pin inject |
| C Ollama route | router_hit **{ollama_m.get('router_hit_rate', 1.0)}** on **{ollama_m.get('rows', 16)}** fixtures | **domain_tag** fed to compress stub |
| B compress @8010 | Golden-40 **{_pct(v3_metrics.get('global_token_saving_rate'))}** (41676 v3 lexicon, offline eval) | **POST /v1/compress** on pin-trimmed payload |

**Forbidden in E2E headline:** blend Layer A % with Layer B %; claim Track A promotion; imply live trading.

---

## Chain (target topology)

```text
[Fixture: ops log excerpt OR resume scenario]
    → (1) LTM lane pin select (infra|ms|oracle|web_ops)
    → (2) tiktoken count (pre/post pin) — Layer A metric
    → (3) Ollama shallow router @127.0.0.1:11434 — domain_tag JSON
    → (4) POST http://127.0.0.1:8010/v1/compress (stub live evaluate_report)
    → (5) Record: tokens_in, tokens_out, saving_rate, jaccard (if hydrate), latency_ms per hop
```

**Not in scope for v1 runner:** semantic_rag deep chain, gematria 4D bridge ON (default OFF per frozen bench), cloud keys.

---

## Prerequisites

| Service | Command / check |
|---------|-----------------|
| Ollama | `127.0.0.1:11434` · model `mkm-shallow-router-v1` (see `docs/final/artifacts/ollama_mkm_shallow_router_modelfile_v1.txt`) |
| Compress stub | `py -m uvicorn scripts.compression_token_api_stub:app --host 127.0.0.1 --port 8010` |
| Lexicon | v3 export candidate `{v3.get('candidate_path', 'reports/.../41676_...json')}` (**promotion: HOLD** — bench inject only) |
| Python deps | tiktoken, project `.venv`, FastAPI stub deps |

Health: `GET http://127.0.0.1:8010/health` → 2xx before bench.

---

## Fixture set (proposed)

1. **Resume scenarios (4):** mirror `mkm_ltm_resume_lane_token_bench_v1` lanes — infra, ms, oracle, web_ops.  
   Source text: `MISSION_LOG.md` + `CENTRAL_AGENT_MEMORY_V1.md` slice per lane inject pins.

2. **Router scenarios (16):** reuse `tests/fixtures/ollama_shallow_router_golden_v1.json`.

3. **Compress payloads (≥5):** subset of Golden-40 `MULTILENS_PERFORMANCE_EVAL_INPUT_V2.json` cases with Hangul hits (cmp2_011–040).

4. **Cross-product minimum:** **8 E2E rows** = 4 resume lanes × 2 compress cases (fixed seed).

---

## Metrics contract (per E2E row)

| field | source |
|-------|--------|
| `lane_id` | LTM bench lane |
| `pin_tokens` | tiktoken after inject |
| `naive_tokens` | tiktoken full paste baseline |
| `router_hit` | Ollama fixture expectation match |
| `domain_tag` | parsed shallow router output |
| `compress_tokens_in/out` | stub response / meter |
| `compress_saving_rate` | stub or offline reconcile |
| `jaccard` | optional `eval_context.hydrate_live_eval` |
| `latency_ms` | {{ltm_ms, ollama_ms, compress_ms, total_ms}} |
| `integrity_flags` | hydration failures, circuit break |

**Aggregate report schema (future):** `mkm_ltm_ollama_8010_e2e_bench_v1` → `reports/mkm_ltm_ollama_8010_e2e_bench_v1_latest.json`

**Dual reporting block required in output:**

- `raw`: per-hop metrics as measured  
- `repair_v2`: N/A until repair layer exists  
- `delta`: document any post-processor uplift separately  

---

## Pass / fail gates (draft)

| gate | threshold | note |
|------|-----------|------|
| G0 services | Ollama + 8010 health OK | hard |
| G1 router | router_hit ≥ 0.95 on embedded 16-fixture subset | component parity |
| G2 compress | stub returns 2xx; saving_rate ≥ 0.35 on Hangul cases | floor, not SLA |
| G3 fidelity | jaccard ≥ 0.85 when hydrate enabled | optional v1 |
| G4 no KPI collapse | E2E headline **must** report pin savings and compress savings **separately** | Fact-Lock |

---

## Implementation status

| item | status |
|------|--------|
| Component benches A/B/C | **DONE** (see input artifacts) |
| Integrated runner script | **DONE** — `scripts/run_mkm_ltm_ollama_8010_e2e_bench_v1.py` |
| pytest smoke | **DONE** — `tests/test_mkm_ltm_ollama_8010_e2e_bench_v1.py` (dry-run) |
| Live E2E pass | **Phase 1 R&D** — requires Ollama @11434 + stub @8010 |

**Runner:** `scripts/run_mkm_ltm_ollama_8010_e2e_bench_v1.py`  
**Output:** `reports/mkm_ltm_ollama_8010_e2e_bench_v1_latest.json`  
**Dry-run:** `--dry-run` writes 8-row schema shell without network (exit 0).

---

## Reproduce (component baselines only — today)

```powershell
# Layer A
py scripts/bench_mkm_ltm_resume_lane_token_v1.py

# Layer C (requires Ollama live)
py scripts/run_ollama_shallow_router_bench_v1.py

# Layer B v3 export candidate (HOLD)
py scripts/build_hangul_ko_lemma_v3_export_candidate_v1.py

# E2E dry-run (no services)
py scripts/run_mkm_ltm_ollama_8010_e2e_bench_v1.py --dry-run

# E2E live (Ollama + stub required)
py -m uvicorn scripts.compression_token_api_stub:app --host 127.0.0.1 --port 8010
py scripts/run_mkm_ltm_ollama_8010_e2e_bench_v1.py
```

---

## References

- HN draft: `reports/hangul_ko_lemma_hn_launch_draft_v1_latest.md`
- LTM bench: `reports/mkm_ltm_resume_lane_token_bench_v1_latest.json`
- Ollama bench: `reports/ollama_shallow_router_bench_v1_latest.json`
- v3 export: `reports/hangul_ko_lemma_v3_export_candidate_v1_latest.json`
- Existing partial E2E (Ollama→semantic_rag, **not** LTM→8010): `scripts/run_ollama_shallow_to_semantic_rag_e2e_v1.py`

---

**Boundary:** `[HYPO]` research spec · no Track A promotion · no public SLA % · E2E headline must not replace component truth matrix.
"""


def main() -> int:
    missing = [p for p in (LTM, OLLAMA) if not p.is_file()]
    if missing:
        print("ABORT: missing", ", ".join(_rel(p) for p in missing))
        return 1

    ltm = json.loads(LTM.read_text(encoding="utf-8"))
    ollama = json.loads(OLLAMA.read_text(encoding="utf-8"))
    v3 = json.loads(V3_EXPORT.read_text(encoding="utf-8")) if V3_EXPORT.is_file() else {}
    hn = json.loads(HN_DRAFT.read_text(encoding="utf-8")) if HN_DRAFT.is_file() else {}

    md = _build_md(ltm, ollama, v3)
    MD_OUT.write_text(md, encoding="utf-8")

    infra = (ltm.get("lanes") or {}).get("infra") or {}
    doc = {
        "schema": "mkm_ltm_ollama_8010_e2e_bench_spec_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypo_label": "[HYPO]",
        "send_gate": "HOLD",
        "integrated_runner_shipped": True,
        "runner_path": "scripts/run_mkm_ltm_ollama_8010_e2e_bench_v1.py",
        "runner_output": "reports/mkm_ltm_ollama_8010_e2e_bench_v1_latest.json",
        "reproduce": "py scripts/build_mkm_ltm_ollama_8010_e2e_bench_spec_v1.py",
        "markdown_path": _rel(MD_OUT),
        "component_benches_proven": {
            "layer_a_ltm_skim": {
                "artifact": _rel(LTM),
                "infra_savings_ratio": infra.get("savings_ratio_vs_naive_baseline"),
            },
            "layer_b_golden40_v3": {
                "artifact": _rel(V3_EXPORT) if V3_EXPORT.is_file() else None,
                "promotion": v3.get("promotion", "HOLD"),
                "global_token_saving_rate": (v3.get("metrics_snapshot") or {}).get(
                    "global_token_saving_rate"
                ),
            },
            "layer_c_ollama_router": {
                "artifact": _rel(OLLAMA),
                "router_hit_rate": (ollama.get("metrics") or {}).get("router_hit_rate"),
                "rows": (ollama.get("metrics") or {}).get("rows"),
            },
        },
        "e2e_integrated_chain_bench_proven": hn.get("three_layer_summary", {}).get(
            "e2e_integrated_chain_bench_proven", False
        ),
        "proposed_runner": "scripts/run_mkm_ltm_ollama_8010_e2e_bench_v1.py",
        "proposed_output": "reports/mkm_ltm_ollama_8010_e2e_bench_v1_latest.json",
        "gates_draft": {
            "G0_services_health": "ollama_11434_and_8010_health",
            "G1_router_hit_min": 0.95,
            "G2_compress_saving_floor": 0.35,
            "G3_jaccard_min_optional": 0.85,
            "G4_no_kpi_collapse": True,
        },
        "forbidden_e2e_headline": [
            "Blend Layer A ~99% with Layer B ~47% as one product KPI.",
            "Claim Track A promotion from E2E smoke.",
            "Replace 5-lane truth matrix with single E2E number.",
        ],
    }
    JSON_OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"WROTE: {MD_OUT}")
    print(f"WROTE: {JSON_OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
