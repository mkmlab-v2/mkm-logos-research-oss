#!/usr/bin/env python3
"""Commander daily Logos anchor — fuse 명리·체질·날씨 → theme verse [NON_GATING][가설].

B-track only. Does not gate trading or prophecy. Optional ANN-lite second hit via
MKM_COMMANDER_LOGOS_ANN_LITE=1 (requires logos_vector_index_ann_lite_v1.sqlite).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MAP = ROOT / "data" / "lifestyle" / "logos_daily_theme_map_v1.json"
THEME_ROOT = ROOT / "docs" / "research" / "logos_metaphor_db_v1"
DEFAULT_OUT = ROOT / "reports" / "commander_daily_logos_anchor_latest.json"
ANN_SQLITE = ROOT / "docs" / "final" / "artifacts" / "logos_vector_index_ann_lite_v1.sqlite"
INSIGHT_BUNDLE = ROOT / "docs" / "final" / "artifacts" / "logos_insight_bundle_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> Dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _truthy(name: str, *, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None or not str(raw).strip():
        return default
    return str(raw).strip().lower() in ("1", "true", "yes", "on")


def _find_month_row(report: Dict[str, Any], year: int, month: int) -> Optional[Dict[str, Any]]:
    mf = report.get("monthly_fortune") or {}
    for row in mf.get("rows") or []:
        if int(row.get("year", 0)) == year and int(row.get("month", 0)) == month:
            return row
    return None


def _stable_pick(candidates: List[str], seed: str) -> str:
    if not candidates:
        return ""
    h = int(hashlib.sha256(seed.encode("utf-8")).hexdigest(), 16)
    return candidates[h % len(candidates)]


def _load_theme(stem: str, theme_dir: Path) -> Optional[Dict[str, Any]]:
    path = theme_dir / f"{stem}.json"
    if not path.is_file():
        return None
    doc = _read_json(path)
    if doc.get("schema") != "mkm_logos_research_thin_slice_v0.2.1":
        return None
    return doc


def _koreanize_telegram(s: str) -> str:
    repl = (
        ("[HYPO]", "[가설]"),
        ("deploy discipline", "배포 규율"),
        ("change advisory", "변경 자문"),
        ("prudent NO_GO", "신중 거절"),
        ("Proverbs Path", ""),
        ("NON_GATING", ""),
    )
    out = s
    for old, new in repl:
        out = out.replace(old, new)
    if "(" in out and ")" in out:
        # drop English parenthetical in theme titles when Korean prefix exists
        idx = out.find("(")
        if idx > 2 and any("\uac00" <= c <= "\ud7a3" for c in out[:idx]):
            out = out[:idx].strip()
    return " ".join(out.split())


def _clip(s: str, n: int = 96) -> str:
    t = " ".join(str(s).split())
    if len(t) <= n:
        return t
    return t[: n - 1] + "…"


def _score_theme_stems(
    *,
    map_doc: Dict[str, Any],
    mo_tg: str,
    weather_band: str,
    sasang: str,
    weak_el: str,
    calendar_kst: str,
) -> Tuple[str, List[str], str]:
    """Return (chosen_stem, match_reasons, seed)."""
    reasons: List[str] = []
    votes: Dict[str, int] = {}

    def _vote(bucket: str, key: str, weight: int) -> None:
        stems = ((map_doc.get(bucket) or {}).get(key) or []) if key else []
        if stems:
            reasons.append(f"{bucket}:{key}")
            for s in stems:
                votes[s] = votes.get(s, 0) + weight

    if mo_tg:
        _vote("ten_god_month", mo_tg, 3)
    if weather_band:
        _vote("weather_band", weather_band, 2)
    if sasang:
        _vote("sasang", sasang, 2)
    if weak_el:
        _vote("weakest_element", weak_el, 1)

    if not votes:
        defaults = list(map_doc.get("default_themes") or [])
        stem = _stable_pick(defaults, calendar_kst)
        return stem, ["default"], calendar_kst

    best = max(votes.values())
    tied = sorted([s for s, v in votes.items() if v == best])
    seed = f"{calendar_kst}|{'|'.join(reasons)}"
    stem = _stable_pick(tied, seed)
    return stem, reasons, seed


def _build_fusion_query(
    *,
    mo_tg: str,
    weather_band: str,
    sasang: str,
    dom: str,
    weak: str,
    headline_ko: str,
) -> str:
    parts = [
        f"월운 십신 {mo_tg}",
        f"날씨 {weather_band}",
        f"체질 {sasang}",
        f"오행 우세 {dom} 약 {weak}",
        headline_ko[:120],
        "지혜 균형 페이싱 회복",
    ]
    return " ".join(p for p in parts if p and p.strip())


def _insight_bundle_supplement() -> List[str]:
    """P2: optional Logos insight bundle citation (B-track, non-gating)."""
    if not _truthy("MKM_COMMANDER_LOGOS_INSIGHT_BUNDLE", default=True):
        return []
    doc = _read_json(INSIGHT_BUNDLE)
    if doc.get("schema") != "logos_insight_bundle_v1":
        return []
    lines: List[str] = []
    pack = doc.get("citation_pack") or []
    for row in pack[:2]:
        if not isinstance(row, dict):
            continue
        ref = row.get("verse_id") or row.get("verse_ref") or "—"
        snip = row.get("snippet") or row.get("evidence_snippet") or ""
        if snip:
            lines.append(f"  인사이트 인용 [가설]: {ref} — {_clip(str(snip), 72)}")
    if not lines:
        unc = doc.get("uncertainty") or {}
        band = unc.get("uncertainty_band") or "mid"
        lines.append(f"  Logos 관측 밴드 [가설]: {band} (인용팩 비어 있음 — 테마 앵커 우선)")
    return lines


def _ann_lite_hits(query: str, *, top_k: int = 2) -> List[Dict[str, Any]]:
    if not ANN_SQLITE.is_file():
        return []
    proc = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "query_logos_vector_index_ann_lite_v1.py"),
            "--sqlite",
            str(ANN_SQLITE),
            "--query",
            query,
            "--top-k",
            str(top_k),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=120,
    )
    if proc.returncode != 0:
        return []
    try:
        doc = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return []
    return list(doc.get("hits") or [])[:top_k]


def build_logos_anchor(
    profile: Dict[str, Any],
    report: Dict[str, Any],
    *,
    lifestyle: Optional[Dict[str, Any]] = None,
    myeongni_headline_ko: str = "",
    map_path: Path = DEFAULT_MAP,
    calendar_kst: Optional[str] = None,
    use_ann: Optional[bool] = None,
) -> Dict[str, Any]:
    map_doc = _read_json(map_path)
    if map_doc.get("schema") != "logos_daily_theme_map_v1":
        raise ValueError(f"expected logos_daily_theme_map_v1: {map_path}")

    theme_dir = ROOT / str(map_doc.get("theme_dir") or "docs/research/logos_metaphor_db_v1")
    now = datetime.now()
    cal = calendar_kst or now.strftime("%Y-%m-%d")
    year, month = now.year, now.month

    sasang = ((profile.get("sasang_reference") or {}).get("label")) or "태양인"
    mo = _find_month_row(report, year, month) or {}
    mo_tg = str(mo.get("wolwoon_stem_ten_god") or "").strip()
    dom = ((report.get("structure_analysis") or {}).get("element_profile") or {}).get(
        "dominant_element_visible"
    )
    weak = ((report.get("structure_analysis") or {}).get("element_profile") or {}).get(
        "weakest_element_visible"
    )
    lifestyle = lifestyle or {}
    weather_band = str(lifestyle.get("weather_band") or "mild")

    stem, reasons, seed = _score_theme_stems(
        map_doc=map_doc,
        mo_tg=mo_tg,
        weather_band=weather_band,
        sasang=sasang,
        weak_el=str(weak or ""),
        calendar_kst=cal,
    )
    theme = _load_theme(stem, theme_dir)
    anchor = (theme or {}).get("golden_anchor") or {}
    satellite = None
    nodes = (theme or {}).get("semantic_nodes") or []
    if nodes:
        satellite = max(nodes, key=lambda n: float(n.get("impact_weight") or 0))

    fusion_query = _build_fusion_query(
        mo_tg=mo_tg,
        weather_band=weather_band,
        sasang=sasang,
        dom=str(dom or ""),
        weak=str(weak or ""),
        headline_ko=myeongni_headline_ko,
    )

    ann_hits: List[Dict[str, Any]] = []
    if use_ann if use_ann is not None else _truthy("MKM_COMMANDER_LOGOS_ANN_LITE", default=False):
        ann_hits = _ann_lite_hits(fusion_query, top_k=2)

    match_ko = " · ".join(
        x
        for x in [
            f"월운 {mo_tg}" if mo_tg else "",
            f"날씨 {weather_band}",
            f"{sasang}",
            f"약 오행 {weak}" if weak else "",
        ]
        if x
    )

    telegram_lines: List[str] = [
        "",
        "▸ 성경 앵커 (Logos) [NON_GATING][가설]",
        f"  융합 맥락: {match_ko}",
    ]
    if theme and anchor:
        theme_label = _koreanize_telegram(str(anchor.get("theme") or stem))
        telegram_lines.append(f"  테마: {theme_label} — {', '.join(reasons)}")
        telegram_lines.append(
            f"  앵커: {anchor.get('ref', '—')} — {_clip(str(anchor.get('text') or ''), 88)}"
        )
        if satellite:
            telegram_lines.append(
                f"  연결: {satellite.get('ref', '—')} — {_clip(str(satellite.get('text') or ''), 72)}"
            )
        insight = str((theme or {}).get("commander_insight") or "").strip()
        if insight:
            telegram_lines.append(f"  해설: {_clip(_koreanize_telegram(insight), 100)}")
    else:
        telegram_lines.append(f"  (테마 파일 없음: {stem})")

    for extra in _insight_bundle_supplement():
        telegram_lines.append(extra)

    if ann_hits:
        telegram_lines.append("  ANN 보조 [가설]:")
        for h in ann_hits[:2]:
            vid = h.get("verse_id") or "—"
            score = h.get("score")
            sc = f" {score:.3f}" if isinstance(score, (int, float)) else ""
            telegram_lines.append(f"    · {vid}{sc}")

    telegram_lines.append("  경계: 시장 예언·실매매·임상 단정 없음 · 2차 성경 레짐 보조만")

    return {
        "schema": "commander_daily_logos_anchor_v1",
        "hypothesis_tier": "B",
        "non_gating": True,
        "boundary_ack": True,
        "generated_at_utc": _utc_now(),
        "calendar_kst": cal,
        "theme_stem": stem,
        "match_reasons": reasons,
        "match_seed": seed,
        "fusion_query": fusion_query,
        "golden_anchor": {
            "node_id": anchor.get("node_id"),
            "ref": anchor.get("ref"),
            "text": anchor.get("text"),
            "theme": anchor.get("theme"),
        },
        "satellite_node": (
            {
                "node_id": satellite.get("node_id"),
                "ref": satellite.get("ref"),
                "text": satellite.get("text"),
            }
            if satellite
            else None
        ),
        "ann_lite_hits": ann_hits,
        "telegram_append_lines": telegram_lines,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--profile-json", type=Path, required=True)
    ap.add_argument("--report-json", type=Path, required=True)
    ap.add_argument("--lifestyle-json", type=Path, default=None)
    ap.add_argument("--map-json", type=Path, default=DEFAULT_MAP)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--use-ann-lite", action="store_true")
    ap.add_argument("--stdout-only", action="store_true")
    args = ap.parse_args()

    profile = _read_json(args.profile_json)
    report = _read_json(args.report_json)
    lifestyle = _read_json(args.lifestyle_json) if args.lifestyle_json else None

    payload = build_logos_anchor(
        profile,
        report,
        lifestyle=lifestyle,
        map_path=args.map_json,
        use_ann=args.use_ann_lite,
    )
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    if args.stdout_only:
        for ln in payload.get("telegram_append_lines") or []:
            print(ln)
    else:
        print(f"WROTE: {args.out_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
