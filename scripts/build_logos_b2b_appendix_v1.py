#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Emit Track C B2B Logos lens appendix MD from metaphor DB themes (NON_GATING, DRAFT)."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT / "docs/research/logos_metaphor_db_v1"
DEFAULT_SCHEMA = ROOT / "docs/final/schemas/mkm_logos_research_thin_slice_v0.2.1.schema.json"
DEFAULT_OUT = ROOT / "docs/final/artifacts/track_c_b2b_logos_lens_appendix_v1_latest.md"
DEFAULT_MANIFEST = ROOT / "docs/final/artifacts/logos_corpus_manifest_v1_latest.json"
DEFAULT_SLICE = (
    ROOT
    / "projects/bitcoin-trading/ops/windows-rehearsal/jemaai-cloud-mvp/showroom_logos_research_slice_v0.json"
)


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _validate(doc: dict[str, Any], schema_path: Path) -> None:
    jsonschema = __import__("jsonschema")
    schema = _load(schema_path)
    jsonschema.Draft7Validator(schema).validate(doc)


def _manifest_line(root: Path, rel: str) -> str:
    p = root / rel
    return f"`{rel}` — {'present' if p.is_file() else 'MISSING'}"


def build_appendix(
    *,
    db_dir: Path,
    schema_path: Path,
    manifest_path: Path,
    slice_path: Path,
    generated_at: str,
) -> str:
    themes_paths = sorted(db_dir.glob("theme_*.json"))
    if not themes_paths:
        raise FileNotFoundError(f"no theme_*.json in {db_dir}")

    themes: list[dict[str, Any]] = []
    for path in themes_paths:
        doc = _load(path)
        _validate(doc, schema_path)
        anchor = doc["golden_anchor"]
        themes.append(
            {
                "file": path.name,
                "theme": anchor["theme"],
                "ref": anchor["ref"],
                "node_id": anchor["node_id"],
                "node_count": len(doc.get("semantic_nodes") or []),
            }
        )

    table_rows = "\n".join(
        f"| {t['theme']} | {t['ref']} | `{t['node_id']}` | {t['node_count']} | `{t['file']}` |"
        for t in themes
    )

    manifest_note = _manifest_line(ROOT, "docs/final/artifacts/logos_corpus_manifest_v1_latest.json")
    graph_note = _manifest_line(ROOT, "docs/final/artifacts/logos_corpus_graph_bundle_v1_latest.json")
    vector_policy_note = _manifest_line(ROOT, "docs/final/artifacts/LOGOS_VECTOR_INDEX_POLICY_V1.json")
    vector_manifest_note = _manifest_line(
        ROOT, "docs/final/artifacts/logos_vector_index_manifest_v1_latest.json"
    )
    policy_readiness_note = _manifest_line(
        ROOT, "docs/final/artifacts/logos_track_b_policy_readiness_v1_latest.json"
    )
    deep_fusion_note = _manifest_line(
        ROOT, "docs/final/artifacts/logos_track_b_deep_fusion_job_v1_latest.json"
    )
    ann_lite_note = _manifest_line(ROOT, "docs/final/artifacts/logos_vector_index_ann_lite_v1_latest.json")
    commander_note = _manifest_line(
        ROOT, "docs/final/artifacts/logos_track_b_commander_deep_report_latest.json"
    )
    shadow_note = _manifest_line(ROOT, "docs/final/artifacts/logos_shadow_insight_latest.json")
    falsification_note = _manifest_line(
        ROOT, "docs/final/artifacts/logos_falsification_benchmark_latest.json"
    )
    distill_latest_note = _manifest_line(
        ROOT, "docs/final/artifacts/logos_deep_research_distill_latest.json"
    )
    slice_note = _manifest_line(
        ROOT,
        "projects/bitcoin-trading/ops/windows-rehearsal/jemaai-cloud-mvp/showroom_logos_research_slice_v0.json",
    )
    showroom_url = "https://jemaai.cloud/public_showroom_logos_research_v1.html"

    sample = themes[0]
    return f"""# [DRAFT] B2B 매크로 경보 — 부록: 문화·서사 관측 레이어 (Logos)

- **generated_at_utc:** `{generated_at}`
- **schema:** `track_c_b2b_logos_lens_appendix_v1`
- **status:** `DRAFT_AUTO` — legal sign-off before external send

**본문 SSOT:** `docs/final/artifacts/track_c_2026_h2_macro_risk_alert_report_mvp_v1.md` · `track_c_b2b_macro_alert_offer_onepager_latest.md`  
**본 부록 역할:** 유료 본문 **대체 아님** · `[NON_GATING]` · 아티팩트·스냅샷 근거형만.

---

## 1. 목적·범위

- 엔터프라이즈 매크로·리스크 경보 **본체**는 1차 실물 레짐·운영 게이트·재현 가능 JSON이다.
- 본 부록은 **고난도 텍스트 코퍼스**에서 추출한 **구조화 서사 스냅샷**을 “스트레스 테스트 베드”로만 제공한다.
- **비실행:** 주문·사이징·API 키·임상 판단·Track A 자동 합선에 사용하지 않음.

---

## 2. 이번 호 근거 아티팩트

| 항목 | 상태 |
|------|------|
| 코퍼스 매니페스트 (슬라이스 1) | {manifest_note} |
| 코퍼스·그래프 번들 (슬라이스 2) | {graph_note} |
| 벡터 정책·매니페스트 (슬라이스 3) | {vector_policy_note} · {vector_manifest_note} |
| 정책 준비도 (슬라이스 4) | {policy_readiness_note} (`overall_ok` 스냅샷) |
| 딥 퓨전 잡·증류 템플릿 (슬라이스 5) | {deep_fusion_note} · ANN 라이트 {ann_lite_note} |
| 지휘관 심층 리포트 골격 | {commander_note} · MD `reports/logos_track_b_commander_deep_report_latest.md` |
| 섀도우 인사이트 (Track C 부속) | {shadow_note} |
| 반증 벤치마크 (대조군) | {falsification_note} |
| 증류 스냅샷 (latest) | {distill_latest_note} |
| 쇼룸 슬라이스 JSON | {slice_note} |
| 공개 데모 (스냅샷) | `{showroom_url}` |
| 메타포 DB | `docs/research/logos_metaphor_db_v1/theme_*.json` ({len(themes)} themes) |

---

## 3. 테마 카탈로그 (v0.2.1)

| 테마 | 앵커 구절 | node_id | cross-nodes | 파일 |
|------|-----------|---------|-------------|------|
{table_rows}

**예시 요약 ({sample['theme']}):** 앵커 {sample['ref']} — cross-node {sample['node_count']}개. `research_metaphor_*` 필드는 교육용 은유이며 운영 `NO_GO`·`LOCKED_MODE`와 **동일하지 않음**.

---

## 4. 한계·면책

- `[HYPO]` · `hypo_research_only` · 종교적 정답·투자 확정·실시간 무지연 주장 없음
- 지연 스냅샷; 실시간 트레이딩 피드 아님
- Phase N(주석·사본학·2차 문헌 스택)은 RQ-015 백로그 — 본 부록 범위 밖

---

## 5. 문의·확장

- 전체 테마 JSON·주간 스냅샷: **엔터프라이즈 부록·API** 별도 계약
- PoC: LG/가전 등 — **본선 매크로 PoC와 범위 분리** 명시

---

## Regenerate

```powershell
py scripts/build_logos_b2b_appendix_v1.py
py scripts/build_showroom_logos_research_slice_v1.py
```
"""


def main() -> int:
    ap = argparse.ArgumentParser(description="Build Track C B2B Logos lens appendix")
    ap.add_argument("--db-dir", type=Path, default=DEFAULT_DB)
    ap.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA)
    ap.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    ap.add_argument("--slice-json", type=Path, default=DEFAULT_SLICE)
    ap.add_argument("--out-md", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    if not args.schema.is_file():
        print(f"schema missing: {args.schema}", file=sys.stderr)
        return 2
    if not args.db_dir.is_dir():
        print(f"db dir missing: {args.db_dir}", file=sys.stderr)
        return 2

    generated_at = datetime.now(timezone.utc).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")
    try:
        md = build_appendix(
            db_dir=args.db_dir,
            schema_path=args.schema,
            manifest_path=args.manifest,
            slice_path=args.slice_json,
            generated_at=generated_at,
        )
    except Exception as exc:  # noqa: BLE001
        print(f"build failed: {exc}", file=sys.stderr)
        return 1

    args.out_md.parent.mkdir(parents=True, exist_ok=True)
    args.out_md.write_text(md, encoding="utf-8")
    print(f"Wrote {args.out_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
