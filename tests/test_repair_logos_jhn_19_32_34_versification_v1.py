"""Jhn.19.32–34 versification repair (offline tmp JSONL)."""

from __future__ import annotations

import json
from pathlib import Path


def _merged_row(vid: str, text: str) -> dict:
    return {
        "verse_id": vid,
        "source_ref": f"Jhn {vid.split('.')[-1]}",
        "edition": "SBLGNT",
        "text": text,
        "original_text": text,
        "greek_value": 1,
        "total_value": 1,
    }


MERGED_ORIG = (
    "οὖν ἦλθον οἱ στρατιῶται καὶ μὲν κατέαξαν τὰ σκέλη τοῦ πρώτου καὶ τοῦ ἄλλου "
    "τοῦ συσταυρωθέντος αὐτῷ δὲ ἐπὶ τὸν Ἰησοῦν ἐλθόντες ὡς εἶδον ἤδη αὐτὸν τεθνηκότα "
    "οὐ κατέαξαν αὐτοῦ τὰ σκέλη ἀλλ’ εἷς τῶν στρατιωτῶν λόγχῃ αὐτοῦ τὴν πλευρὰν ἔνυξεν "
    "καὶ ἐξῆλθεν εὐθὺς αἷμα καὶ ὕδωρ"
)


def test_split_merged_original() -> None:
    from scripts.repair_logos_jhn_19_32_34_versification_v1 import _split_merged_original

    parts = _split_merged_original(MERGED_ORIG)
    assert parts is not None
    v32, v33, v34 = parts
    assert "αἷμα" not in v32 and "ὕδωρ" not in v32
    assert "τεθνηκότα" in v33
    assert "αἷμα" in v34 and "ὕδωρ" in v34


def test_repair_jsonl_write(tmp_path: Path) -> None:
    from scripts.repair_logos_jhn_19_32_34_versification_v1 import repair_jsonl

    p = tmp_path / "corpus.jsonl"
    rows = [_merged_row(v, MERGED_ORIG) for v in ("Jhn.19.32", "Jhn.19.33", "Jhn.19.34")]
    p.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")

    dry = repair_jsonl(p, write=False)
    assert dry["needs_repair"] is True
    assert dry["preview"]["Jhn.19.34"]["has_blood_water"] is True
    assert dry["preview"]["Jhn.19.32"]["has_blood_water"] is False

    applied = repair_jsonl(p, write=True)
    assert applied["repaired"] is True

    by_id = {}
    for line in p.read_text(encoding="utf-8").splitlines():
        o = json.loads(line)
        by_id[o["verse_id"]] = o
    assert by_id["Jhn.19.32"]["original_text"] != by_id["Jhn.19.34"]["original_text"]
    assert "αἷμα" in by_id["Jhn.19.34"]["original_text"]
