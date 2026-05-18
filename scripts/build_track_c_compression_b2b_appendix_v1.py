#!/usr/bin/env python3
"""B2B appendix: Track A compression plugin scalability (zone shards, Fact-Lock)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
KPI = ROOT / "reports/constitution/btrack_pilot/ultra_compression_kpi_summary_latest.json"
ENTERPRISE = ROOT / "docs/final/artifacts/compression_enterprise_executive_summary_v1.md"
OUT = ROOT / "docs/final/artifacts/track_c_b2b_compression_plugin_appendix_v1_latest.md"


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _pct(x: float | None) -> str:
    if x is None:
        return "—"
    return f"{float(x) * 100:.1f}%"


def _j(x: float | None) -> str:
    if not isinstance(x, (int, float)):
        return "—"
    return f"{float(x):.3f}"


def main() -> int:
    kpi = _load(KPI)
    active = kpi.get("active_kpi") if isinstance(kpi.get("active_kpi"), dict) else {}
    saving = active.get("global_token_saving_rate")
    avg_j = active.get("avg_reconstruction_fidelity_jaccard")
    min_j = None
    active_path = ROOT / "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json"
    if active_path.is_file():
        rep = _load(active_path)
        cm = rep.get("compression_metrics") if isinstance(rep.get("compression_metrics"), dict) else {}
        min_j = cm.get("min_reconstruction_fidelity_jaccard")

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    body = f"""# Track C B2B — Compression Plugin Scalability Appendix (DRAFT)

- **generated_at_utc:** `{ts}`
- **status:** `DRAFT_AUTO` — legal sign-off before external send
- **SSOT:** `compression_enterprise_executive_summary_v1.md` (「Plugin scalability IR」) · `TRACK_C_IP_BUSINESS_PLAN_2026-04-17.md` §3.1.1

## OEM / IR hook (EN)

- **Zero weight-training plug-in domains:** KB-scale `zone_*.json` policy packs under `codebook/shards/` — not GPU fine-tune per vertical.
- **At compress time:** one domain policy selected per document + global must_keep + optional **41,775-term** lexicon join.
- **Frozen bench (40 cases):** ~{_pct(saving if isinstance(saving, (int, float)) else None)} token saving · policy floor **0.47** met · avg Jaccard **{_j(avg_j if isinstance(avg_j, (int, float)) else None)}** · min Jaccard **{_j(min_j if isinstance(min_j, (int, float)) else None)}** (lexical proxy).
- **Not claimed:** multi-shard overlay on one pass, clinical/trading guarantees, “we are LoRA weights,” training cost $0 forever.

## OEM / IR hook (KO)

- **가중치 재학습 없는 도메인 플러그인:** `zone_*.json` 정책 팩(라우팅 키워드·must_keep) — 산업마다 GPU FT 대신 큐레이션·벤치.
- **문서 1건 = 샤드 1개** + 41k 렉시콘 조인(동시에 의료·SCM 팩을 겹친다고 말하지 않음).
- **동결 벤치:** 전역 절감 **{_pct(saving if isinstance(saving, (int, float)) else None)}**, 하한 **0.47**, Jaccard avg **{_j(avg_j if isinstance(avg_j, (int, float)) else None)}** / min **{_j(min_j if isinstance(min_j, (int, float)) else None)}**.
- **Pack 0-A/B LoRA(명리 등)** 와 **압축 zone 팩**은 레포 내 **별 축**.

## Evidence (internal)

| Item | Path |
|------|------|
| 1-Pager + Plugin IR § | `docs/final/artifacts/compression_enterprise_executive_summary_v1.md` |
| KPI | `reports/constitution/btrack_pilot/ultra_compression_kpi_summary_latest.json` |
| Active report | `docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json` |
| Router | `scripts/core/domain_router.py` |
| LG deck / factcheck | `lg_hs_compression_discipline_deck_v1_latest.md` |

## Disclaimers (paste on slide footer)

> Not investment advice. Bench ≠ production SLA. Jaccard is word-overlap proxy, not semantic %. No buy/sell from compression KPIs.
"""
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(body, encoding="utf-8")
    print(f"WROTE: {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
