#!/usr/bin/env python3
"""Build LENS_LOGOS NotebookLM Fact-Lock guard snippet (NL briefing priority).

Output: docs/final/artifacts/notebooklm_lens_logos_nl_fact_lock_guard_v1_latest.md
Audit:  reports/notebooklm_lens_logos_nl_sync_audit_v1_latest.json
"""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_MD = ROOT / "docs/final/artifacts/notebooklm_lens_logos_nl_fact_lock_guard_v1_latest.md"
OUT_AUDIT = ROOT / "reports/notebooklm_lens_logos_nl_sync_audit_v1_latest.json"
NOTEBOOK_UUID = "93e825c7-7d48-41f7-aedf-33e5fa59c2db"

GUARD_BODY = """# LENS_LOGOS NotebookLM Fact-Lock guard (PRIORITY · read first)

generated_utc: {utc}
target_notebook: 11 · 성경 렌즈 (`LENS_LOGOS`)
notebook_uuid: `93e825c7-7d48-41f7-aedf-33e5fa59c2db`
data_lane: lens_logos · `[NON_GATING]` · `research_only` · `send_gate: HOLD`

## Answer order (mandatory)

1. **This file** + `LOGOS_NOTEBOOK_META_GUIDE.md`
2. **Gate artifacts** (`shadow_lane_gematria_gate`, `logos_theory_implementation_wiring`, `mkm_theory_mathematization_canon` §5·§7)
3. **Tier0 nl_proxy papers** (성서게마트리아 · 성경 숫자) — scholarly `[FACT]` / theology
4. **HAAN fusion briefs** — cross-lane `[HYPO]` only
5. **Web pages / YouTube / pasted memos** — third-party reference; **never** MKM implementation FACT

## MKM implementation FACT (disk SSOT)

| Claim | Verdict | SSOT |
|-------|---------|------|
| 4D vector SSOT | **S-L-K-M** (`gematria_bridge_v1`) | `scripts/core/gematria_to_4d_bridge.py` |
| E_i, P_f, D_d, H_c | **Pedagogical alias only — NOT SSOT** | `gematria_thermo_alias_v1.py` · `LOGOS_NOTEBOOK_META_GUIDE` |
| `schemas/cosmic_code_anchor.json` | **Not implemented (greenfield forbidden)** | `logos_cosmic_meta_architecture_draft_v1_latest.json` |
| Gematria → Track A compression | **Policy OFF** | `apply_gematria_4d_bridge_policy: false` |
| Track A / live promotion | **Forbidden** | `shadow_lane_gematria_gate` · `promotion_to_a_track_allowed: false` |
| 사상동역학 (repo) | **B-track market psych axis + stress labels** | `mkm_theory_mathematization_canon_v1` §5 |
| 병증약리 full clinical predictor | **Not implemented** | symptom weights = reference only |
| Hallucination 0% | **Not evidenced** | refuse absolute claims |
| 666 → 364-week system error | **Not in code SSOT** | refuse unless artifact cited |
| Phos/Gefen 금화교역 auto-resolve | **Not in code SSOT** | `[HYPO]` narrative only |

## NL smoke — must refuse overclaim

- "게마트리아 4D·사상동역학이 레포에 완벽 통합·헌법 박제?" → **No** — partial B-track PoC + draft; not production canon.
- "E_i/P_f가 운영 SSOT?" → **No** — S-L-K-M only.
- "Track A·실매매에 승격됐나?" → **No** — permanent air-gap.
- "성경 신학적 진리를 MKM 4D로 대체?" → **No** — papers = authorial/theological; MKM = coordinate harness `[HYPO]`.

## Scholarly papers (Tier0 nl_proxy) — do not conflate with MKM engine

- **성서게마트리아:** Kuhnau gematria is partial; cannot fully explain biblical arrangement.
- **성경 숫자:** 14/153/666 = symbolic theology; warn against excessive mysticism.

## Reproduce

```powershell
py scripts/build_notebooklm_lens_logos_nl_fact_lock_guard_v1.py
py scripts/build_notebooklm_lens_source_packs_v1.py
powershell -File scripts/Push-NotebooklmLensPacks_v1.ps1 -Lens LENS_LOGOS -Refresh
```
"""


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _nlm_source_stats() -> dict:
    try:
        raw = subprocess.check_output(
            ["nlm", "source", "list", NOTEBOOK_UUID],
            cwd=ROOT,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        items = json.loads(raw)
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc)}
    by_type: dict[str, int] = {}
    titles = []
    for it in items:
        t = str(it.get("type") or "unknown")
        by_type[t] = by_type.get(t, 0) + 1
        titles.append(str(it.get("title") or ""))
    guard_hits = {
        "LOGOS_NOTEBOOK_META_GUIDE": any("LOGOS_NOTEBOOK_META_GUIDE" in x for x in titles),
        "fact_lock_guard": any("fact_lock_guard" in x.lower() for x in titles),
        "shadow_lane_gematria": any("shadow_lane_gematria" in x for x in titles),
        "theory_mathematization_canon": any("mkm_theory_mathematization" in x for x in titles),
        "logos_theory_implementation_wiring": any("logos_theory_implementation" in x for x in titles),
    }
    return {
        "ok": True,
        "total_sources": len(items),
        "by_type": by_type,
        "guard_hits": guard_hits,
        "web_page_count": by_type.get("web_page", 0),
    }


def main() -> int:
    utc = _utc()
    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_AUDIT.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text(GUARD_BODY.format(utc=utc), encoding="utf-8")
    audit = {
        "schema": "notebooklm_lens_logos_nl_sync_audit_v1",
        "generated_at_utc": utc,
        "notebook_uuid": NOTEBOOK_UUID,
        "guard_md": str(OUT_MD.relative_to(ROOT)).replace("\\", "/"),
        "nlm": _nlm_source_stats(),
        "drift_notes": [
            "NL may contain many web_page sources (Bible software etc.) — not MKM SSOT.",
            "Fact-Lock answers must prioritize guard md + meta guide over web synthesis.",
        ],
    }
    OUT_AUDIT.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "guard_md": str(OUT_MD), "audit": str(OUT_AUDIT)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
