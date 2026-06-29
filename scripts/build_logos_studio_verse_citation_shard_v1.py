#!/usr/bin/env python3
"""Build Logos Studio verse citation shard — KRV body + insight card context.

  py scripts/build_logos_studio_verse_citation_shard_v1.py

Outputs:
  docs/final/artifacts/logos_studio_verse_citation_shard_v1_latest.json
  projects/no1kmedi/public/data/logos_studio/verse_citation_shard_v1.json
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INSIGHT = ROOT / "docs/final/artifacts/showroom_qa_node_insight_cards_v1_latest.json"
READING = ROOT / "docs/final/artifacts/showroom_logos_job_reading_pack_slice_v1_latest.json"
OUT_ART = ROOT / "docs/final/artifacts/logos_studio_verse_citation_shard_v1_latest.json"
OUT_PUB = ROOT / "projects/no1kmedi/public/data/logos_studio/verse_citation_shard_v1.json"

# 개역개정 (KRV) — Job·Psalm·Num demo spine only · research sidecar floor
KRV_TEXT_KO: dict[str, str] = {
    "Ps.23.3": "그가 나의 영혼을 살리시고 그의 이름을 위하여 내게 의의 길을 가르키시리로다",
    "Ps.27.14": "여호와를 기다리라 담대하고 굳세라 여호와를 기다리라",
    "Jer.30.7": "그 날은 있을지라 모든 사람이 견디기 어려운 날이라 야곱의 환난과 같이 없었고 또 그 후에는 없으리라",
    "Jer.31.4": "너희가 처녀 이스rael이여 내가 다시 너를 건축하리니 네가 다시 기쁨으로 나오며 네가 다시 궁정을 이루며 네가 다시 춤을 추리라",
    "Lam.3.22": "여호와의 자비와 긍휼은 무궁하시므로 우리가 진멸되지 아니함이니이다",
    "Job.1.6": "하루는 하나님의 아들들이 와서 여호와 앞에 서고 사단도 그 가운데 와서 서니라",
    "Job.1.8": (
        "여호와께서 사단에게 이르시되 네가 내 종 Job을 유심히 보았느냐 "
        "그와 같이 순전하고 정직하여 하나님을 경외하며 악에서 떠난 자가 세상에 없느니라"
    ),
    "Job.1.12": (
        "여호와께서 사단에게 이르시되 보라 그의 모든 소유가 네 손에 있으니 "
        "다만 그에게만 네 손을 대지 말라 하시매 사단이 여호와 앞에서 물러가니라"
    ),
    "Job.1.21": (
        "이르기를 내가 모태에서 적신이 나왔사온즉 또한 적신이 그리로 돌아가옵니다 "
        "여호와께서 주셨사오니 여호와께서 가져 가셨사오니 "
        "여호와의 이름이 찬송을 받으실지니이다 하고"
    ),
    "Job.4.7": "생각하여 보라 무죄한 자가 죽은 일이 있었느냐 어디든지 정직한 자가 멸한 일이 있었느냐",
    "Job.8.20": "보는 것과 같이 악인은 빛이 없고 그의 장막의 횃불도 꺼지느니라",
    "Job.11.7": "네가 하나님을 찾아 그의 계를 알 수 있겠느냐 그의 지혜의 완전함을 알 수 있겠느냐",
    "Job.20.22": "그가 모든 행복 가운데서도 곤고를 만나면 재앙의 손이 그를 기다리리라",
    "Job.32.2": "브니엘의 아들 Elihu의 노가 Job에게 심히 발하매 Job이 자기를 의롭다 하기 때문이었고",
    "Job.33.12": "보라 하나님은 한 번 말씀하시고 두 번은 듣지 아니하시나니",
    "Job.37.14": "Job이여 이것을 듣고 잠잠하고 하나님의 오묘함을 깊이 생각해 보라",
    "Job.38.4": "네가 땅의 기초를 놓을 때에 어디 있었느냐 네가 깊이 깨달으면 그것을 알려 주라",
    "Job.38.26": "비가 없는 땅 곧 사람이 없는 광야에 비를 내리시며",
    "Job.40.15": "보라 Behemoth(베헤못)을 내가 만든 것 같이 너도 먹을 수 있느냐",
    "Job.41.1": "악어(Leviathan)를 갈고리로 끌어 올리겠느냐",
    "Job.42.5": "내가 주께 대하여 귀로 듣기만 하였사오나 이제는 눈으로 주를 봅나이다",
    "Job.42.10": "여호와께서 Job의 곤경을 돌이키사 Job에게 이전보다 갑절을 주시니",
    "Job.42.15": "이 땅의 모든 여자보다 Job의 딸들이 더욱 아름다웠더라",
    "Num.27.8": "이스라ael 자손에게 명하기를 사람이 죽어 자식이 없거든 그의 기업을 그의 딸에게 돌릴지니라",
}


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _clean_excerpt(raw: str, cap: int = 220) -> str:
    s = re.sub(r"\*\*", "", raw or "")
    s = re.sub(r"`[^`]+`", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    if len(s) > cap:
        s = s[: cap - 1].rstrip() + "…"
    return s


def _stage_by_ref(reading: dict) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for stage in reading.get("narrative_route_public") or []:
        for ref in stage.get("verse_refs") or []:
            out[ref] = {
                "stage_id": stage.get("stage_id"),
                "stage_label_ko": stage.get("label_ko"),
                "bottleneck_ko": stage.get("bottleneck_ko"),
            }
    return out


def main() -> int:
    insight = _load_json(INSIGHT)
    reading = _load_json(READING) if READING.is_file() else {}
    stage_map = _stage_by_ref(reading)
    cards = insight.get("cards") or {}

    verses: dict[str, dict] = {}
    seen: set[str] = set()

    for key, card in cards.items():
        if card.get("kind") not in ("verse", "psalm_verse"):
            continue
        ref = card.get("ref") or key.split("::")[-1]
        if not ref or ref in seen:
            continue
        seen.add(ref)
        stage = stage_map.get(ref, {})
        text_ko = KRV_TEXT_KO.get(ref)
        if not text_ko:
            continue
        verses[ref] = {
            "ref": ref,
            "text_ko": text_ko,
            "translation_id": "krv",
            "stage_id": stage.get("stage_id") or card.get("stage_id"),
            "stage_label_ko": stage.get("stage_label_ko"),
            "bottleneck_ko": card.get("bottleneck_ko") or stage.get("bottleneck_ko"),
            "verse_note_ko": _clean_excerpt(card.get("excerpt_ko") or ""),
            "governance": card.get("governance") or "[HYPO][NON_GATING]",
        }

    for ref, text_ko in KRV_TEXT_KO.items():
        if ref in verses:
            continue
        stage = stage_map.get(ref, {})
        verses[ref] = {
            "ref": ref,
            "text_ko": text_ko,
            "translation_id": "krv",
            "stage_id": stage.get("stage_id"),
            "stage_label_ko": stage.get("stage_label_ko"),
            "bottleneck_ko": stage.get("bottleneck_ko"),
            "verse_note_ko": None,
            "governance": "[HYPO][NON_GATING]",
        }

    doc = {
        "schema_version": "logos_studio_verse_citation_shard_v1",
        "generated_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "research_only": True,
        "hypothesis_tier": "B",
        "send_gate": "HOLD",
        "translation_note_ko": "개역개정(KRV) citation floor — 신학·인과 단답·Track A 근거 아님.",
        "verse_count": len(verses),
        "verses": verses,
        "reproducible_command": "py scripts/build_logos_studio_verse_citation_shard_v1.py",
    }

    OUT_ART.parent.mkdir(parents=True, exist_ok=True)
    OUT_PUB.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(doc, ensure_ascii=False, indent=2) + "\n"
    OUT_ART.write_text(payload, encoding="utf-8")
    OUT_PUB.write_text(payload, encoding="utf-8")
    print(json.dumps({"ok": True, "verse_count": len(verses), "out": str(OUT_PUB)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
