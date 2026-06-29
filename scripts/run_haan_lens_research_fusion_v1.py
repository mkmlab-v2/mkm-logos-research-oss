#!/usr/bin/env python3
"""HAAN paper digest → NL proxy upgrade + lens research fusion (B-track).

Upgrades stub nl_proxy from Tier0 PAPER_DIGEST, builds NL query sets,
myeongri observation log lines, and cross-lens pointer sidecar.
research_only · send_gate HOLD · no Track A merge
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

RAW = ROOT / "docs/research/raw"
ARTIFACTS = ROOT / "docs/final/artifacts"
REPORTS = ROOT / "reports/constitution/btrack_pilot"
BATCH = REPORTS / "haan_library_downloads_batch_v1_latest.json"
MYEONGNI_LOG = ROOT / "data/myeongni/insight_observation_log.jsonl"

LENS_PACK = {
    "logos": "LENS_LOGOS",
    "myeongri": "LENS_MYEONGNI",
    "ijeoma": "IJEOMA_BTRACK",
    "ijeoma_logos_bridge": "IJEOMA_BTRACK,LENS_LOGOS",
}

NL_QUERIES: dict[str, list[dict[str, str]]] = {
    "logos": [
        {
            "id": "logos_q1",
            "question_ko": "요한계시록 12–14장 박해·교회론 논문(Tier0)의 핵심 주장 3개와 repo Logos verse subgraph 앵커 후보를 구분해줘. [NON_GATING]",
            "tier0_hint": "logos_요한계시록_12-14장",
        },
        {
            "id": "logos_q2",
            "question_ko": "천년왕국·19–20장 상관 논문 vs eschatology coordinate cluster — 종말 프레임 diff만. 실매매·게이트 승격 금지.",
            "tier0_hint": "logos_천년왕국",
        },
        {
            "id": "logos_q3",
            "question_ko": "게마트리아·숫자 논문 주장 vs B-track shadow lane — 승격 없이 diff 표만.",
            "tier0_hint": "logos_성경에_나타난_숫자",
        },
    ],
    "myeongri": [
        {
            "id": "myeongri_q1",
            "question_ko": "연해자평·적천수·궁통보감 육친론 정의 충돌 지점만 표로 — 실무 적용은 [HYPO].",
            "tier0_hint": "myeongri_명리학_육친론",
        },
        {
            "id": "myeongri_q2",
            "question_ko": "타로 4원소 vs 명리 오행 비교 논문 — 오행 coordinate hit와 주장 diff.",
            "tier0_hint": "myeongri_타로",
        },
        {
            "id": "myeongri_q3",
            "question_ko": "계획행동이론×사주 상담 논문 — MYEONGRI_INSIGHT_SSOT observation log 형식 가설 1줄 초안.",
            "tier0_hint": "myeongri_계획된_행동",
        },
    ],
    "ijeoma": [
        {
            "id": "ijeoma_q1",
            "question_ko": "philosophy vs clinical cluster — 東醫壽世保元 vs 格致藁 인용 빈도 diff (coordinate map 근거).",
            "tier0_hint": "ijeoma_동무_이제마의_심성론",
        },
        {
            "id": "ijeoma_q2",
            "question_ko": "천유초·闡幽 언급은 grep/scout만 — 본문 mock 금지. 하안 28편 중 2차 인용만 맵.",
            "tier0_hint": "cheonyucho",
        },
        {
            "id": "ijeoma_q3",
            "question_ko": "루가 복음 bridge 논문 — Logos 편집사관 vs 사상체질 cross-lens [HYPO] brief 5줄.",
            "tier0_hint": "ijeoma_logos_bridge",
        },
    ],
}

OBSERVATION_LINES: list[dict[str, Any]] = [
    {
        "inputs_summary": "HAAN myeongri: 육친론 3고서 비교 Tier0 + classical_corpus 435 hits",
        "insight_one_liner": "[HYPO] 연해자평·적천수·궁통보감 육친 정의가 상이 — 현대 상담 SSOT는 단일 고서 계승 전제를 반증 후보로 둠.",
        "falsification_hook": "동일 사주 10건에 세 고서 육친 매핑이 80% 이상 일치하면 단일 SSOT 가설 유지.",
        "snapshot_refs": [
            "docs/research/raw/myeongri_명리학_육친론_비교연구_*_PAPER_DIGEST_tier0_v1.md",
            "docs/final/artifacts/myeongri_corpus_coordinate_map_v1_latest.json",
        ],
    },
    {
        "inputs_summary": "HAAN myeongri: 타로-오행 비교 Tier0 + ohaeng_axis hits",
        "insight_one_liner": "[HYPO] 타로 4원소↔오행 대응은 명리 quant block과 1:1 동형이 아님 — 비교는 서사 벤치만.",
        "falsification_hook": "myeongni_b_track_quant_block 오행 분포와 논문 대응표 상관 |r|<0.5면 비동형 확정(벤치).",
        "snapshot_refs": ["docs/research/raw/myeongri_타로_4원소와_명리학_오행의_비교연구_*_PAPER_DIGEST_tier0_v1.md"],
    },
    {
        "inputs_summary": "HAAN myeongri: TPB×사주 상담 Tier0",
        "insight_one_liner": "[HYPO] 계획행동이론 프레임은 명리 상담 의사결정의 보조 서사층 — 육친 단독 설명력 대체 아님.",
        "falsification_hook": "상담 사례에서 TPB 변수 없이 육친만으로 의사결정 재현률이 동일하면 TPB 층 불필요.",
        "snapshot_refs": [
            "docs/research/raw/myeongri_계획된_행동이론을_이용한_사주_명리학_상담_*_PAPER_DIGEST_tier0_v1.md"
        ],
    },
]


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _slugify(name: str) -> str:
    slug = re.sub(r"[^\w\-]+", "_", name, flags=re.UNICODE).strip("_")
    slug = re.sub(r"_+", "_", slug)
    return (slug or "paper")[:72]


def _find_tier0_for_item(item: dict[str, Any]) -> Path | None:
    lens = str(item.get("lens") or "")
    stem = Path(str(item.get("file") or "")).stem
    prefix = {"ijeoma_logos_bridge": "ijeoma_logos_bridge", "logos": "logos", "myeongri": "myeongri", "ijeoma": "ijeoma"}.get(
        lens, lens
    )
    direct = RAW / f"{_slugify(f'{prefix}_{stem}')}_PAPER_DIGEST_tier0_v1.md"
    if direct.is_file():
        return direct
    candidates = sorted(RAW.glob(f"{prefix}_*{stem[:20]}*_PAPER_DIGEST_tier0_v1.md"))
    if candidates:
        return candidates[0]
    slug_part = _slugify(stem)[:24]
    for p in RAW.glob(f"{prefix}_*_PAPER_DIGEST_tier0_v1.md"):
        if slug_part in _slugify(p.stem):
            return p
    return None


def _extract_section(md: str, heading: str) -> str:
    pat = re.compile(rf"### {re.escape(heading)}\s*\n\s*\n(.*?)(?=\n### |\n## |\Z)", re.DOTALL)
    m = pat.search(md)
    return re.sub(r"\s+", " ", (m.group(1) if m else "")).strip()[:2000]


def _extract_coords(md: str) -> list[dict[str, Any]]:
    coords: list[dict[str, Any]] = []
    for m in re.finditer(r"### fact_id: (coord_\w+)\s*\n(?:.*?\n)*?- value: (\d+)", md):
        coords.append({"fact_id": m.group(1), "value": int(m.group(2))})
    return coords


def upgrade_nl_proxy(*, item: dict[str, Any], tier0: Path) -> str | None:
    proxy_rel = item.get("nl_proxy")
    if not isinstance(proxy_rel, str):
        return None
    proxy_path = ROOT / proxy_rel.replace("\\", "/")
    md = tier0.read_text(encoding="utf-8", errors="replace")
    title_m = re.search(r"^#\s+Tier 0 — Paper digest ·\s*(.+)$", md, re.M)
    title = (title_m.group(1).strip() if title_m else tier0.stem)[:200]
    backend_m = re.search(r"\*\*extract_backend:\*\* (\S+)", md)
    chars_m = re.search(r"### fact_id: source_text_char_count.*?- value: (\d+)", md, re.DOTALL)
    abstract = _extract_section(md, "abstract_or_lead")
    conclusion = _extract_section(md, "conclusion")
    coords = _extract_coords(md)
    lens = str(item.get("lens") or "")

    lines = [
        f"# NL Proxy — HAAN_LIBRARY (digest-upgraded)",
        "",
        f"**generated:** {_utc()} · `research_only` · `send_gate: HOLD`",
        f"**lens:** {LENS_PACK.get(lens, lens)}",
        f"**source_type:** library_capture_haan_2026-06-28 + paper_digest_v1",
        f"**disk_path:** `{item.get('disk_path')}`",
        f"**tier0:** `{tier0.relative_to(ROOT).as_posix()}`",
        f"**sha256:** `{item.get('sha256', '')}`",
        f"**extract_backend:** {backend_m.group(1) if backend_m else 'unknown'}",
        f"**text_chars:** {chars_m.group(1) if chars_m else 'unknown'}",
        "",
        "## Bibliographic",
        "",
        title,
        "",
        "## Reading digest (from Tier0 — verify against PDF)",
        "",
        "### abstract_or_lead",
        abstract or "(empty)",
        "",
        "### conclusion",
        conclusion or "(empty)",
        "",
        "## Lens coordinates (regex hits)",
        "",
    ]
    if coords:
        for c in coords[:8]:
            lines.append(f"- `{c['fact_id']}`: {c['value']}")
    else:
        lines.append("(no coordinate hits)")
    lines.extend(
        [
            "",
            "## MKM boundaries",
            "",
            "- `[CANON]`·Track A·실매매·macro gating 승격 없음",
            "- Logos = `[NON_GATING]` assistive only",
            "- Full excerpt: Tier0 path above",
            "",
        ]
    )
    proxy_path.parent.mkdir(parents=True, exist_ok=True)
    proxy_path.write_text("\n".join(lines), encoding="utf-8")
    return proxy_path.relative_to(ROOT).as_posix()


def _top_papers_from_map(lens: str, *, limit: int = 5) -> list[dict[str, Any]]:
    map_path = ARTIFACTS / f"{lens}_corpus_coordinate_map_v1_latest.json"
    if not map_path.is_file():
        return []
    doc = json.loads(map_path.read_text(encoding="utf-8"))
    papers = sorted(
        doc.get("papers") or [],
        key=lambda p: sum((p.get("coordinate_hits") or {}).values()),
        reverse=True,
    )
    out: list[dict[str, Any]] = []
    for p in papers[:limit]:
        out.append(
            {
                "tier0": p.get("tier0"),
                "title_guess": p.get("title_guess"),
                "coordinate_hits": p.get("coordinate_hits"),
                "fact_count": p.get("fact_count"),
            }
        )
    return out


def append_myeongni_observations(*, dry_run: bool = False) -> int:
    if not MYEONGNI_LOG.parent.exists():
        MYEONGNI_LOG.parent.mkdir(parents=True, exist_ok=True)
    existing_hooks: set[str] = set()
    if MYEONGNI_LOG.is_file():
        for line in MYEONGNI_LOG.read_text(encoding="utf-8", errors="replace").splitlines():
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if row.get("note") == "run_haan_lens_research_fusion_v1.py":
                hook = row.get("falsification_hook")
                if isinstance(hook, str):
                    existing_hooks.add(hook)
    lines: list[str] = []
    for row in OBSERVATION_LINES:
        if row.get("falsification_hook") in existing_hooks:
            continue
        entry = {
            "ts_utc": _utc(),
            "hypothesis_tier": "B",
            "boundary_ack": True,
            **row,
            "note": "run_haan_lens_research_fusion_v1.py",
        }
        lines.append(json.dumps(entry, ensure_ascii=False))
    if dry_run:
        return len(lines)
    with MYEONGNI_LOG.open("a", encoding="utf-8") as f:
        for line in lines:
            f.write(line + "\n")
    return len(lines)


def build_crossref_pointers(top_ijeoma: list[dict[str, Any]]) -> dict[str, Any]:
    pointers: list[dict[str, str]] = []
    for p in top_ijeoma[:5]:
        tier0 = str(p.get("tier0") or "")
        if not tier0:
            continue
        pointers.append(
            {
                "tier0": tier0,
                "title_guess": str(p.get("title_guess") or "")[:120],
                "link_type": "paper_digest_pointer",
                "note": "SASANG_CROSS_REF_DRAFT 본문 수정 없음 — Tier0 서지 포인터만",
            }
        )
    bridge = RAW / "ijeoma_logos_bridge_루가_복음_편집사관에_대한_이제마의_사상체질에_의한_시험적_고찰_PAPER_DIGEST_tier0_v1.md"
    if bridge.is_file():
        pointers.append(
            {
                "tier0": bridge.relative_to(ROOT).as_posix(),
                "title_guess": "루가 복음 bridge",
                "link_type": "cross_lens_logos_ijeoma",
                "note": "[HYPO] Logos–사상 bridge — Track A 합선 금지",
            }
        )
    return {
        "schema": "haan_sasang_paper_crossref_pointers_v1",
        "generated_at_utc": _utc(),
        "send_gate": "HOLD",
        "research_only": True,
        "pointers": pointers,
        "reproduce": "py scripts/run_haan_lens_research_fusion_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--skip-log", action="store_true")
    args = ap.parse_args()

    if not BATCH.is_file():
        print(json.dumps({"ok": False, "error": f"missing {BATCH}"}, ensure_ascii=False))
        return 2

    batch = json.loads(BATCH.read_text(encoding="utf-8"))
    upgraded: list[dict[str, Any]] = []
    missing_tier0: list[str] = []

    for item in batch.get("items") or []:
        tier0 = _find_tier0_for_item(item)
        if tier0 is None:
            missing_tier0.append(str(item.get("file")))
            continue
        if args.dry_run:
            upgraded.append({"file": item.get("file"), "tier0": tier0.relative_to(ROOT).as_posix(), "dry_run": True})
            continue
        proxy = upgrade_nl_proxy(item=item, tier0=tier0)
        upgraded.append(
            {
                "file": item.get("file"),
                "lens": item.get("lens"),
                "tier0": tier0.relative_to(ROOT).as_posix(),
                "nl_proxy": proxy,
            }
        )

    lanes: dict[str, Any] = {}
    for lens_key in ("logos", "myeongri", "ijeoma"):
        map_file = ARTIFACTS / f"{lens_key}_corpus_coordinate_map_v1_latest.json"
        top = _top_papers_from_map(lens_key)
        lanes[lens_key] = {
            "nl_queries": NL_QUERIES.get(lens_key, []),
            "top_papers_by_coordinate_hits": top,
            "coordinate_map": map_file.relative_to(ROOT).as_posix() if map_file.is_file() else None,
            "nl_notebook_pack": f"reports/notebooklm_lens_packs_v1/{'LENS_LOGOS' if lens_key == 'logos' else 'LENS_MYEONGNI' if lens_key == 'myeongri' else 'IJEOMA_BTRACK'}",
        }

    ijeoma_top = _top_papers_from_map("ijeoma", limit=8)
    crossref = build_crossref_pointers(ijeoma_top)

    fusion = {
        "schema": "haan_lens_research_fusion_v1",
        "generated_at_utc": _utc(),
        "send_gate": "HOLD",
        "research_only": True,
        "upgraded_proxy_count": len(upgraded),
        "missing_tier0_count": len(missing_tier0),
        "lanes": lanes,
        "upgraded_proxies": upgraded,
        "missing_tier0_files": missing_tier0[:10],
        "reproduce": [
            "py scripts/run_haan_lens_research_fusion_v1.py",
            "py scripts/build_notebooklm_lens_source_packs_v1.py",
            "py scripts/build_haan_lens_coordinate_maps_v1.py",
        ],
    }

    query_sets = {
        "schema": "haan_lens_nl_query_sets_v1",
        "generated_at_utc": _utc(),
        "send_gate": "HOLD",
        "research_only": True,
        "logos": NL_QUERIES["logos"],
        "myeongri": NL_QUERIES["myeongri"],
        "ijeoma": NL_QUERIES["ijeoma"],
        "usage": "NotebookLM LENS_* notebooks — paste one question per session; cite Tier0 path in answer",
    }

    if args.dry_run:
        print(json.dumps({"ok": True, "dry_run": True, "would_upgrade": len(upgraded), "missing": len(missing_tier0)}, ensure_ascii=False))
        return 0

    REPORTS.mkdir(parents=True, exist_ok=True)
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    fusion_path = REPORTS / "haan_lens_research_fusion_v1_latest.json"
    query_path = REPORTS / "haan_lens_nl_query_sets_v1_latest.json"
    crossref_path = ARTIFACTS / "haan_sasang_paper_crossref_pointers_v1_latest.json"
    fusion_path.write_text(json.dumps(fusion, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    query_path.write_text(json.dumps(query_sets, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    crossref_path.write_text(json.dumps(crossref, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    log_count = 0 if args.skip_log else append_myeongni_observations()

    print(
        json.dumps(
            {
                "ok": True,
                "upgraded": len(upgraded),
                "missing_tier0": len(missing_tier0),
                "observation_log_appended": log_count,
                "fusion": str(fusion_path),
                "queries": str(query_path),
                "crossref_pointers": str(crossref_path),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
