#!/usr/bin/env python3
"""Add graph-chapter verse_anchor presets until target count (Phase A2 → 50).

Reproduce:
  py scripts/merge_logos_studio_graph_chapter_presets_v1.py --target-count 50
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.logos_studio_preset_graph_helpers_v1 import chapter_node_ids  # noqa: E402
from scripts.logos_verse_ref_canonical_v1 import canonical_verse_ref  # noqa: E402

DEFAULT_PRESETS = ROOT / "docs/final/artifacts/showroom_meaning_topology_qa_presets_v1_latest.json"
DEFAULT_GRAPH = ROOT / "docs/final/artifacts/showroom_meaning_topology_graph_slice_v1_latest.json"
TARGET_ROADMAP = 50
STUB_PREFIX = "showroom_router_stub_verse::"

# Curated chapter slots — skip Gen.6 (BigSet anchors cover it).
CHAPTER_ROADMAP: list[tuple[str, int, str, list[str]]] = [
    ("Gen", 1, "창조 질서와 시작 (Genesis 1)", ["창조", "genesis 1", "gen 1", "질서", "creation", "시작"]),
    ("Gen", 3, "에덴·타락 경계 (Genesis 3)", ["에덴", "타락", "genesis 3", "gen 3", "fall", "boundary"]),
    ("Gen", 11, "바벨 탑과 언어 분산 (Genesis 11)", ["바벨", "babel", "genesis 11", "언어", "분산"]),
    ("Gen", 12, "아브라함 언약 출발 (Genesis 12)", ["아브라함", "abraham", "언약", "genesis 12", "covenant"]),
    ("Gen", 14, "멜기세덱·살렘 (Genesis 14)", ["멜기세덱", "melchizedek", "genesis 14", "살렘"]),
    ("Gen", 19, "소돔·고모라 심판 (Genesis 19)", ["소돔", "sodom", "고모라", "genesis 19", "심판"]),
    ("Gen", 22, "이삭 바인딩 (Genesis 22)", ["이삭", "isaac", "바인딩", "genesis 22", "번제"]),
    ("Gen", 27, "야곱·에서 축복 (Genesis 27)", ["야곱", "jacob", "에서", "esau", "genesis 27"]),
    ("Gen", 28, "벧엘 사다리 (Genesis 28)", ["벧엘", "bethel", "사다리", "genesis 28", "ladder"]),
    ("Exod", 12, "유월절·출애굽 (Exodus 12)", ["유월절", "passover", "exodus 12", "출애굽"]),
    ("Exod", 14, "홍해 건넘 (Exodus 14)", ["홍해", "red sea", "exodus 14", "바다"]),
    ("Exod", 20, "십계명 (Exodus 20)", ["십계명", "ten commandments", "exodus 20", "율법"]),
    ("Deut", 32, "모세의 노래·엘로힘 배분 (Deuteronomy 32)", ["deuteronomy 32", "신명기 32", "엘로힘", "nations"]),
    ("Dan", 3, "다니엘 3장 · 풀무불 (Daniel 3)", ["다니엘 3", "daniel 3", "dan 3", "풀무불", "furnace"]),
    ("Dan", 4, "다니엘 4장 · 느부갓네살 (Daniel 4)", ["다니엘 4", "daniel 4", "dan 4", "느부갓네살", "tree"]),
    ("Dan", 5, "다니엘 5장 · 벽 글 (Daniel 5)", ["다니엘 5", "daniel 5", "dan 5", "벨사살", "mene"]),
    ("Dan", 6, "다니엘 6장 · 사자 굴 (Daniel 6)", ["다니엘 6", "daniel 6", "dan 6", "사자굴", "lions"]),
    ("Dan", 7, "다니엘 7장 · 짐승 환상 (Daniel 7)", ["다니엘 7", "daniel 7", "dan 7", "짐승", "beasts"]),
    ("Dan", 8, "다니엘 8장 · 숫양·숫염소 (Daniel 8)", ["다니엘 8", "daniel 8", "dan 8", "숫양", "ram"]),
    ("Dan", 9, "다니엘 9장 · 70이레 (Daniel 9)", ["다니엘 9", "daniel 9", "dan 9", "70", "weeks"]),
    ("Dan", 10, "다니엘 10장 · 천사 전쟁 (Daniel 10)", ["다니엘 10", "daniel 10", "prince", "천사"]),
    ("Dan", 11, "다니엘 11장 · 왕들 전쟁 (Daniel 11)", ["다니엘 11", "daniel 11", "kings", "왕"]),
    ("Dan", 12, "다니엘 12장 · 부활·종말 (Daniel 12)", ["다니엘 12", "daniel 12", "resurrection", "종말"]),
    ("Job", 2, "욥기 2장 · 고난 심화 (Job 2)", ["욥기 2", "job 2", "고난", "suffering"]),
    ("Job", 38, "욥기 38장 · 창조 반문 (Job 38)", ["욥기 38", "job 38", "whirlwind", "창조"]),
    ("Job", 42, "욥기 42장 · 회복 (Job 42)", ["욥기 42", "job 42", "회복", "restoration"]),
    ("Ps", 23, "시편 23편 · 목자 (Psalm 23)", ["시편 23", "psalm 23", "목자", "shepherd"]),
    ("Ps", 89, "시편 89편 · 다윗 언약 (Psalm 89)", ["시편 89", "psalm 89", "다윗", "covenant"]),
    ("Ps", 103, "시편 103편 · 긍휼 (Psalm 103)", ["시편 103", "psalm 103", "긍휼", "mercy"]),
    ("Jer", 31, "예레미야 31장 · 새 언약 (Jeremiah 31)", ["예레미야 31", "jeremiah 31", "새 언약", "new covenant"]),
    ("Acts", 2, "사도행전 2장 · 오순절 (Acts 2)", ["사도행전 2", "acts 2", "오순절", "pentecost"]),
    ("Acts", 7, "사도행전 7장 · 스데반 (Acts 7)", ["사도행전 7", "acts 7", "스데반", "stephen"]),
    ("John", 1, "요한복음 1장 · 말씀 (John 1)", ["요한복음 1", "john 1", "말씀", "logos"]),
    ("Rev", 12, "요한계시록 12장 · 용과 여자 (Revelation 12)", ["계시록 12", "revelation 12", "rev 12", "용", "dragon"]),
    ("Rev", 20, "요한계시록 20장 · 천년 (Revelation 20)", ["계시록 20", "revelation 20", "rev 20", "천년", "millennium"]),
    ("Gal", 4, "갈라디아서 4장 · 아가르·사라 (Galatians 4)", ["갈라디아서 4", "galatians 4", "gal 4", "아가르"]),
    ("Num", 24, "민수기 24장 · 발람 (Numbers 24)", ["민수기 24", "numbers 24", "발람", "balaam"]),
    ("Judg", 6, "사사기 6장 · 기드온 (Judges 6)", ["사사기 6", "judges 6", "기드온", "gideon"]),
    ("1Sam", 17, "사무엘상 17장 · 다윗·골리앗 (1 Samuel 17)", ["사무엘상 17", "1 samuel 17", "다윗", "goliath"]),
    ("Ruth", 1, "룻기 1장 · 나오미·룻 (Ruth 1)", ["룻기 1", "ruth 1", "나오미", "naomi"]),
    ("Isa", 6, "이사야 6장 · 세리아프 (Isaiah 6)", ["이사야 6", "isaiah 6", "세리아프", "seraph"]),
    ("Isa", 53, "이사야 53장 · 고난받는 종 (Isaiah 53)", ["이사야 53", "isaiah 53", "종", "suffering servant"]),
    ("Matt", 5, "마태복음 5장 · 팔복 (Matthew 5)", ["마태복음 5", "matthew 5", "팔복", "beatitudes"]),
    ("Matt", 28, "마태복음 28장 · 부활 (Matthew 28)", ["마태복음 28", "matthew 28", "부활", "resurrection"]),
    ("Luke", 15, "누가복음 15장 · 잃은 양 (Luke 15)", ["누가복음 15", "luke 15", "탕자", "prodigal"]),
    ("Rom", 8, "로마서 8장 · 성령·확신 (Romans 8)", ["로마서 8", "romans 8", "성령", "spirit"]),
    ("1Cor", 13, "고린도전서 13장 · 사랑 (1 Corinthians 13)", ["고린도전서 13", "1 corinthians 13", "사랑", "love"]),
    ("Heb", 11, "히브리서 11장 · 믿음의 영웅 (Hebrews 11)", ["히브리서 11", "hebrews 11", "믿음", "faith"]),
    ("Rev", 1, "요한계시록 1장 · 요한의 환상 (Revelation 1)", ["계시록 1", "revelation 1", "환상", "vision"]),
    ("Josh", 1, "여호수아 1장 · 강 건넘 (Joshua 1)", ["여호수아 1", "joshua 1", "용기", "courage"]),
    ("1Kgs", 3, "열왕기상 3장 · 솔로몬 지혜 (1 Kings 3)", ["열왕기상 3", "1 kings 3", "지혜", "wisdom"]),
    ("Neh", 8, "느헤미야 8장 · 율법 낭독 (Nehemiah 8)", ["느헤미야 8", "nehemiah 8", "율법", "law"]),
    ("Esth", 4, "에스더 4장 · 왕후를 위한 때 (Esther 4)", ["에스더 4", "esther 4", "모르드개", "mordecai"]),
    ("Hos", 11, "호세아 11장 · 사랑의 회복 (Hosea 11)", ["호세아 11", "hosea 11", "사랑", "love"]),
    ("Mic", 5, "미가 5장 · 베들레헴 (Micah 5)", ["미가 5", "micah 5", "베들레헴", "bethlehem"]),
    ("Zech", 9, "스가랴 9장 · 왕의 입성 (Zechariah 9)", ["스가랴 9", "zechariah 9", "입성", "king"]),
    ("Mal", 4, "말라기 4장 · 엘리야의 날 (Malachi 4)", ["말라기 4", "malachi 4", "엘리야", "elijah"]),
    ("Mark", 4, "마가복음 4장 · 비유 (Mark 4)", ["마가복음 4", "mark 4", "비유", "parable"]),
    ("Luke", 2, "누가복음 2장 · 성탄 (Luke 2)", ["누가복음 2", "luke 2", "성탄", "nativity"]),
]


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _chapter_preset(
    book: str,
    chapter: int,
    prompt_ko: str,
    keywords: list[str],
    graph_doc: dict[str, Any],
) -> dict[str, Any] | None:
    highlights = chapter_node_ids(graph_doc, book, chapter)
    refs = sorted(
        {
            str(n.get("ref") or "")
            for n in graph_doc.get("nodes") or []
            if str(n.get("ref") or "").startswith(f"{book}.{chapter}.")
        }
    )[:6]
    if not refs:
        refs = [canonical_verse_ref(f"{book}.{chapter}.1")]
    if not highlights:
        highlights = [f"{STUB_PREFIX}{canonical_verse_ref(r)}" for r in refs if canonical_verse_ref(r)]
    if not highlights:
        return None
    pid = f"topic_{book.lower()}_{chapter}_anchor"
    return {
        "id": pid,
        "preset_kind": "verse_anchor",
        "prompt_ko": prompt_ko,
        "answer_ko": (
            f"[HYPO] 그래프 슬라이스 **{book}.{chapter}** 장 앵커 프리셋입니다. "
            f"연결 노드 {len(highlights)}개 · 큐레이션 데모 · research_only · NON_GATING."
        ),
        "answer_ko_product": (
            f"[HYPO] Graph slice {book}.{chapter} anchor · curated demo · NON_GATING."
        ),
        "highlight_node_ids": highlights[:48],
        "keywords": keywords + [f"{book.lower()}.{chapter}", f"{book} {chapter}"],
        "router_path_v1": {
            "schema_version": "logos_router_path_v1",
            "verse_refs": refs,
            "research_only": True,
            "send_gate": "HOLD",
        },
    }


def _discover_chapter_slots(graph_doc: dict[str, Any]) -> list[tuple[str, int, str, list[str]]]:
    """Build extra chapter slots from graph slice for roadmap fill."""
    from collections import defaultdict

    by_ch: dict[tuple[str, int], list[str]] = defaultdict(list)
    for n in graph_doc.get("nodes") or []:
        ref = str(n.get("ref") or "")
        parts = ref.split(".")
        if len(parts) < 3:
            continue
        book, ch_s = parts[0], parts[1]
        try:
            ch = int(ch_s)
        except ValueError:
            continue
        by_ch[(book, ch)].append(ref)
    out: list[tuple[str, int, str, list[str]]] = []
    for (book, ch), refs in sorted(by_ch.items(), key=lambda x: (x[0][0], x[0][1])):
        label = f"{book}.{ch} 구절 앵커"
        prompt = f"{book} {ch}장 그래프 앵커 ({book}.{ch})"
        kws = [f"{book.lower()}.{ch}", f"{book} {ch}", book.lower(), str(ch)]
        out.append((book, ch, prompt, kws))
    return out


def merge_chapter_presets(
    presets_doc: dict[str, Any],
    graph_doc: dict[str, Any],
    *,
    target_count: int = TARGET_ROADMAP,
) -> tuple[dict[str, Any], int]:
    presets = list(presets_doc.get("presets") or [])
    by_id = {str(p.get("id")): i for i, p in enumerate(presets) if p.get("id")}
    added = 0
    roadmap = list(CHAPTER_ROADMAP) + _discover_chapter_slots(graph_doc)
    seen_slots: set[tuple[str, int]] = set()
    for book, chapter, prompt_ko, keywords in roadmap:
        slot = (book, chapter)
        if slot in seen_slots:
            continue
        seen_slots.add(slot)
        if len(presets) >= target_count:
            break
        entry = _chapter_preset(book, chapter, prompt_ko, keywords, graph_doc)
        if not entry:
            continue
        pid = entry["id"]
        if pid in by_id:
            presets[by_id[pid]] = entry
            continue
        presets.append(entry)
        by_id[pid] = len(presets) - 1
        added += 1
    presets_doc["presets"] = presets
    presets_doc["graph_chapter_roadmap_target"] = target_count
    presets_doc["generated_at_utc"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return presets_doc, added


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--presets", type=Path, default=DEFAULT_PRESETS)
    ap.add_argument("--graph-json", type=Path, default=DEFAULT_GRAPH)
    ap.add_argument("--target-count", type=int, default=TARGET_ROADMAP)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    presets_doc = _load(args.presets)
    graph_doc = _load(args.graph_json)
    merged, added = merge_chapter_presets(presets_doc, graph_doc, target_count=args.target_count)
    total = len(merged.get("presets") or [])
    summary = {"added": added, "total_presets": total, "target_count": args.target_count}
    if total < args.target_count:
        summary["warning"] = f"below_target_by_{args.target_count - total}"
    if args.dry_run:
        print(json.dumps(summary, ensure_ascii=False))
        return 0 if total >= args.target_count else 1
    args.presets.write_text(json.dumps(merged, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    mvp = ROOT / "projects/bitcoin-trading/ops/windows-rehearsal/jemaai-cloud-mvp/showroom_meaning_topology_qa_presets_v1.json"
    mvp.parent.mkdir(parents=True, exist_ok=True)
    mvp.write_text(json.dumps(merged, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False))
    return 0 if total >= args.target_count else 1


if __name__ == "__main__":
    raise SystemExit(main())
