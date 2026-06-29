#!/usr/bin/env python3
"""Build human_gate curation queue for Logos motif slots 041–100 (pathology/survival).

NL = reference only. Fact-Lock = this script + registry merge after human approve.

Reproducible:
  py scripts/build_logos_motif_human_gate_queue_v1.py
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "docs/final/artifacts/logos_motif_registry_top100_v1.json"
OUT = ROOT / "docs/final/artifacts/logos_motif_human_gate_queue_v1_latest.json"

# Slots 041–100: 30 pathology + 30 survival (candidate metadata only; enabled=false until merge)
CANDIDATES: list[dict[str, Any]] = [
    {"slot": 41, "bias": "pathology", "stem": "fire", "lemma": {"greek": "πυρ"}, "verse": "Heb.12.29", "ko": "불 — 정결·심판"},
    {"slot": 42, "bias": "pathology", "stem": "plague", "lemma": {"greek": "πληγη"}, "verse": "Rev.15.1", "ko": "재앙 — 긴장·파열"},
    {"slot": 43, "bias": "pathology", "stem": "locust", "lemma": {"greek": "ακρις"}, "verse": "Rev.9.3", "ko": "메뚜기 — 침식"},
    {"slot": 44, "bias": "pathology", "stem": "hail", "lemma": {"greek": "χαλαζα"}, "verse": "Rev.16.21", "ko": "우박 — 충격"},
    {"slot": 45, "bias": "pathology", "stem": "famine", "lemma": {"greek": "λιμος"}, "verse": "Rev.6.8", "ko": "기근 — 고갈"},
    {"slot": 46, "bias": "pathology", "stem": "weeping", "lemma": {"greek": "κλαυθμος"}, "verse": "Mat.2.18", "ko": "애곡 — 압력"},
    {"slot": 47, "bias": "pathology", "stem": "ashes", "lemma": {"greek": "σποδος"}, "verse": "Mat.11.21", "ko": "재 — 회개·쇠약"},
    {"slot": 48, "bias": "pathology", "stem": "chaff", "lemma": {"greek": "αχυρον"}, "verse": "Mat.3.12", "ko": "겨 — 선별·소멸"},
    {"slot": 49, "bias": "pathology", "stem": "furnace", "lemma": {"greek": "καμινος"}, "verse": "Mat.13.42", "ko": "풀무 — 극열"},
    {"slot": 50, "bias": "pathology", "stem": "storm", "lemma": {"greek": "θυελλα"}, "verse": "Mat.8.24", "ko": "폭풍 — 동요"},
    {"slot": 51, "bias": "pathology", "stem": "chains", "lemma": {"greek": "αλυσις"}, "verse": "Rev.20.1", "ko": "사슬 — 구속"},
    {"slot": 52, "bias": "pathology", "stem": "bondage", "lemma": {"greek": "δουλεια"}, "verse": "Gal.4.3", "ko": "속박 — 압박"},
    {"slot": 53, "bias": "pathology", "stem": "leprosy", "lemma": {"greek": "λεπρα"}, "verse": "Mat.8.3", "ko": "나병 — 경계·분리"},
    {"slot": 54, "bias": "pathology", "stem": "blindness", "lemma": {"greek": "τυφλος"}, "verse": "Jhn.9.1", "ko": "맹목 — 가림"},
    {"slot": 55, "bias": "pathology", "stem": "deaf", "lemma": {"greek": "κωφος"}, "verse": "Mar.7.32", "ko": "귀막 — 단절"},
    {"slot": 56, "bias": "pathology", "stem": "wound", "lemma": {"greek": "πληγη"}, "verse": "Isa.53.5", "verse_note": "LXX ref candidate", "ko": "상처 — 치유 tension"},
    {"slot": 57, "bias": "pathology", "stem": "tribulation", "lemma": {"greek": "θλιψις"}, "verse": "Rev.2.10", "ko": "환난 — 압력"},
    {"slot": 58, "bias": "pathology", "stem": "persecution", "lemma": {"greek": "διωγμος"}, "verse": "Mat.5.10", "ko": "박해 — 강도"},
    {"slot": 59, "bias": "pathology", "stem": "curse", "lemma": {"greek": "καταρα"}, "verse": "Gal.3.13", "ko": "저주 — 역전 tension"},
    {"slot": 60, "bias": "pathology", "stem": "wrath", "lemma": {"greek": "οργη"}, "verse": "Rom.1.18", "ko": "진노 — 열역학 spike"},
    {"slot": 61, "bias": "pathology", "stem": "dark_cloud", "lemma": {"greek": "νεφελη"}, "verse": "Mat.17.5", "ko": "구름 — 은폐"},
    {"slot": 62, "bias": "pathology", "stem": "earthquake", "lemma": {"greek": "σεισμος"}, "verse": "Rev.6.12", "ko": "지진 — 구조 흔들림"},
    {"slot": 63, "bias": "pathology", "stem": "pestilence", "lemma": {"greek": "λοιμος"}, "verse": "Rev.6.8", "ko": "전염 — 확산"},
    {"slot": 64, "bias": "pathology", "stem": "bitterness", "lemma": {"greek": "πικρια"}, "verse": "Heb.12.15", "ko": "쓴뿌리 — 부식"},
    {"slot": 65, "bias": "pathology", "stem": "stumbling", "lemma": {"greek": "σκανδαλον"}, "verse": "Mat.18.7", "ko": "거 stumbling — 마찰"},
    {"slot": 66, "bias": "pathology", "stem": "desolation", "lemma": {"greek": "ερημωσις"}, "verse": "Mat.24.15", "ko": "황폐 — 공백"},
    {"slot": 67, "bias": "pathology", "stem": "exile", "lemma": {"hebrew": "גלות"}, "verse": "Psa.137.1", "ko": "포로 — 이 displacement"},
    {"slot": 68, "bias": "pathology", "stem": "flood_judgment", "lemma": {"greek": "κατακλυσμος"}, "verse": "2Pe.2.5", "ko": "대홍수 — 압도"},
    {"slot": 69, "bias": "pathology", "stem": "millstone", "lemma": {"greek": "μυλος"}, "verse": "Mat.18.6", "ko": "맷돌 — 중량"},
    {"slot": 70, "bias": "pathology", "stem": "fire_unquenchable", "lemma": {"greek": "ασβεστος"}, "verse": "Mar.9.43", "ko": "꺼지지 않는 불"},
    {"slot": 71, "bias": "survival", "stem": "shadow", "lemma": {"hebrew": "צל"}, "verse": "Psa.91.1", "ko": "그늘 — 피난"},
    {"slot": 72, "bias": "survival", "stem": "fortress", "lemma": {"hebrew": "מצודה"}, "verse": "Psa.18.2", "ko": "요새 — 방어"},
    {"slot": 73, "bias": "survival", "stem": "tower", "lemma": {"greek": "πυργος"}, "verse": "Mat.21.33", "ko": "탑 — 경계"},
    {"slot": 74, "bias": "survival", "stem": "well", "lemma": {"greek": "πηγη"}, "verse": "Jhn.4.6", "ko": "우물 — 수원"},
    {"slot": 75, "bias": "survival", "stem": "spring", "lemma": {"greek": "πηγη"}, "verse": "Rev.21.6", "ko": "샘 — 생명원"},
    {"slot": 76, "bias": "survival", "stem": "pasture", "lemma": {"greek": "νομη"}, "verse": "Jhn.10.9", "ko": "목장 — 양육"},
    {"slot": 77, "bias": "survival", "stem": "fold", "lemma": {"greek": "αυλη"}, "verse": "Jhn.10.16", "ko": "우리 — 경계"},
    {"slot": 78, "bias": "survival", "stem": "garment", "lemma": {"greek": "ιματιον"}, "verse": "Mat.9.20", "ko": "옷 — 보호"},
    {"slot": 79, "bias": "survival", "stem": "wing", "lemma": {"hebrew": "כנף"}, "verse": "Psa.91.4", "ko": "날개 — 덮음"},
    {"slot": 80, "bias": "survival", "stem": "nest", "lemma": {"greek": "νοσσια"}, "verse": "Mat.23.37", "ko": "보금자리"},
    {"slot": 81, "bias": "survival", "stem": "honey", "lemma": {"greek": "μελι"}, "verse": "Pro.24.13", "verse_note": "LXX candidate", "ko": "꿀 — 양육"},
    {"slot": 82, "bias": "survival", "stem": "milk", "lemma": {"greek": "γala"}, "verse": "1Pe.2.2", "ko": "젖 — 양육"},
    {"slot": 83, "bias": "survival", "stem": "cloak", "lemma": {"greek": "ιματιον"}, "verse": "Mat.5.40", "ko": "외투 — 보온"},
    {"slot": 84, "bias": "survival", "stem": "staff", "lemma": {"greek": "ραβδος"}, "verse": "Heb.11.21", "ko": "지팡이 — 지지"},
    {"slot": 85, "bias": "survival", "stem": "tent", "lemma": {"greek": "σκηνη"}, "verse": "Heb.11.9", "ko": "장막 — 이동 거처"},
    {"slot": 86, "bias": "survival", "stem": "harbor", "lemma": {"greek": "ορμος"}, "verse": "Act.27.12", "ko": "항구 — 대피"},
    {"slot": 87, "bias": "survival", "stem": "anchor_rope", "lemma": {"greek": "αγκυρα"}, "verse": "Heb.6.19", "ko": "닻 — 고정"},
    {"slot": 88, "bias": "survival", "stem": "green_pasture", "lemma": {"hebrew": "דשא"}, "verse": "Psa.23.2", "ko": "푸른 초장"},
    {"slot": 89, "bias": "survival", "stem": "still_waters", "lemma": {"hebrew": "מי"}, "verse": "Psa.23.2", "ko": "잔잔한 물"},
    {"slot": 90, "bias": "survival", "stem": "cup", "lemma": {"greek": "ποτηριον"}, "verse": "Psa.23.5", "verse_note": "LXX candidate", "ko": "잔 — 공급"},
    {"slot": 91, "bias": "survival", "stem": "table", "lemma": {"greek": "τραπεζα"}, "verse": "Psa.23.5", "verse_note": "LXX candidate", "ko": "상 — 준비"},
    {"slot": 92, "bias": "survival", "stem": "rod_staff", "lemma": {"hebrew": "שבט"}, "verse": "Psa.23.4", "ko": "막대 — 인도"},
    {"slot": 93, "bias": "survival", "stem": "healing", "lemma": {"greek": "ιασις"}, "verse": "Luk.4.18", "ko": "치유 — 회복"},
    {"slot": 94, "bias": "survival", "stem": "deliverance", "lemma": {"greek": "ρυσις"}, "verse": "Rom.11.26", "ko": "구원 — 해방"},
    {"slot": 95, "bias": "survival", "stem": "stronghold", "lemma": {"greek": "οχυρωμα"}, "verse": "2Co.10.4", "ko": "요새 — 방어"},
    {"slot": 96, "bias": "survival", "stem": "breastplate", "lemma": {"greek": "θωραξ"}, "verse": "Eph.6.14", "ko": "흉배 — 방어"},
    {"slot": 97, "bias": "survival", "stem": "helmet", "lemma": {"greek": "περικεφαλαια"}, "verse": "Eph.6.17", "ko": "투구 — 보호"},
    {"slot": 98, "bias": "survival", "stem": "shelter", "lemma": {"greek": "σκηνωμα"}, "verse": "2Pe.1.13", "ko": "거처 — 완충"},
    {"slot": 99, "bias": "survival", "stem": "living_water", "lemma": {"greek": "υδωρ"}, "verse": "Jhn.4.10", "ko": "생수 — 생존원"},
    {"slot": 100, "bias": "survival", "stem": "daily_bread", "lemma": {"greek": "επιουσιος"}, "verse": "Mat.6.11", "ko": "오늘 양식 — 생존"},
]


def build_queue(registry_path: Path = REGISTRY) -> dict[str, Any]:
    generated_at_utc = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    reg = json.loads(registry_path.read_text(encoding="utf-8")) if registry_path.is_file() else {}
    used_stems = {
        e.get("file_stem")
        for e in reg.get("entries", [])
        if e.get("enabled") and e.get("file_stem")
    }
    entries: list[dict[str, Any]] = []
    for c in CANDIDATES:
        slot_id = f"motif_{c['slot']:03d}"
        stem = c["stem"]
        entries.append(
            {
                "slot_id": slot_id,
                "slot_num": c["slot"],
                "status": "human_gate_proposed",
                "enabled": False,
                "primitive_bias": c["bias"],
                "proposed_file_stem": stem,
                "proposed_anchor_id": f"cosmic_anchor_{stem}_{c['verse'].replace('.', '_').lower()}",
                "proposed_verse_refs": [c["verse"]],
                "motif_lemma": c["lemma"],
                "logos_summary_ko": f"{c['ko']} — [{c['bias']}] human_gate candidate",
                "source": "human_gate_queue_v1",
                "nl_reference_only": True,
                "conflict_with_enabled_stem": stem in used_stems,
                "verse_note": c.get("verse_note"),
            }
        )
    pathology_n = sum(1 for e in entries if e["primitive_bias"] == "pathology")
    survival_n = sum(1 for e in entries if e["primitive_bias"] == "survival")
    return {
        "schema": "logos_motif_human_gate_queue_v1",
        "version": "1.0.0",
        "generated_at_utc": generated_at_utc,
        "hypothesis_class": "HYPO",
        "research_only": True,
        "non_gating": True,
        "forbidden_synthesis": True,
        "track_a_blocked": True,
        "registry_path": registry_path.relative_to(ROOT).as_posix() if registry_path.is_file() else None,
        "registry_enabled_count": reg.get("enabled_count"),
        "queue_slot_range": "motif_041..motif_100",
        "queue_count": len(entries),
        "pathology_count": pathology_n,
        "survival_count": survival_n,
        "merge_policy": "human_gate: commander approves batch → apply_logos_motif_human_gate_merge_v1 (future)",
        "entries": entries,
        "reproducible_command": "py scripts/build_logos_motif_human_gate_queue_v1.py",
        "notes_ko": "NL 참고만. enabled=true 승격은 지휘관 human_gate 후 별도 merge.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    queue = build_queue()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(queue, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {OUT}")
    print(f"  queue={queue['queue_count']} pathology={queue['pathology_count']} survival={queue['survival_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
