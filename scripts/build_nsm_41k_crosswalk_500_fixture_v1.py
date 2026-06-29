#!/usr/bin/env python3
"""Build NSM ↔ 41k crosswalk fixture (100 base + structured expansion → 500 pairs)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.nsm_41k_crosswalk_catalog_v1 import NSM_CROSSWALK_100  # noqa: E402

DEFAULT_OUT = ROOT / "tests/fixtures/nsm_41k_lexicon_crosswalk_500_v1.json"

# Canonical NSM primes (Goddard/Wierzbicka core set + common extensions for Logos corpora)
NSM_CANONICAL_65: list[str] = [
    "i", "you", "someone", "people", "something", "body", "kind", "part",
    "this", "the_same", "other", "one", "two", "much", "little", "good", "bad",
    "big", "small", "think", "know", "want", "feel", "see", "hear", "say", "words",
    "true", "do", "happen", "move", "be", "there_is", "live", "die",
    "when", "now", "before", "after", "long_time", "short_time", "moment",
    "where", "here", "above", "below", "far", "near", "side", "inside", "touch",
    "not", "maybe", "can", "because", "if", "very", "more", "like", "way",
    "water", "fire", "earth", "sky", "sun", "night", "day",
    "child", "man", "woman", "house", "king",
]

# Alternate surface probes per prime (existence-only; not alignment claims)
VARIANT_PROBES: dict[str, list[dict[str, str]]] = {
    "think": [
        {"en": "think", "greek": "noeo", "hebrew": "chashav"},
        {"en": "mind", "greek": "nous", "hebrew": "lev"},
    ],
    "know": [
        {"en": "know", "greek": "oida", "hebrew": "yada"},
        {"en": "knowledge", "greek": "gnosis", "hebrew": "daat"},
    ],
    "say": [
        {"en": "speak", "greek": "laleo", "hebrew": "dabar"},
        {"en": "tell", "greek": "lego", "hebrew": "amar"},
    ],
    "god": [
        {"en": "god", "greek": "theos", "hebrew": "elohim"},
        {"en": "lord", "greek": "kurios", "hebrew": "adonai"},
    ],
    "love": [
        {"en": "love", "greek": "agapao", "hebrew": "ahav"},
        {"en": "beloved", "greek": "agapetos", "hebrew": "ahuv"},
    ],
    "covenant": [
        {"en": "covenant", "greek": "diatheke", "hebrew": "berit"},
        {"en": "promise", "greek": "epaggelia", "hebrew": "davar"},
    ],
    "spirit": [
        {"en": "spirit", "greek": "pneuma", "hebrew": "ruach"},
        {"en": "breath", "greek": "pnoe", "hebrew": "neshamah"},
    ],
    "righteous": [
        {"en": "righteous", "greek": "dikaios", "hebrew": "tsaddiq"},
        {"en": "just", "greek": "dikaiosune", "hebrew": "mishpat"},
    ],
    "sin": [
        {"en": "sin", "greek": "hamartano", "hebrew": "chet"},
        {"en": "transgression", "greek": "parabasis", "hebrew": "pesha"},
    ],
    "faith": [
        {"en": "faith", "greek": "pistis", "hebrew": "emunah"},
        {"en": "believe", "greek": "pisteuo", "hebrew": "aman"},
    ],
    "mercy": [
        {"en": "mercy", "greek": "eleos", "hebrew": "chesed"},
        {"en": "grace", "greek": "charis", "hebrew": "chen"},
    ],
    "judgment": [
        {"en": "judgment", "greek": "krisis", "hebrew": "mishpat"},
        {"en": "judge", "greek": "krino", "hebrew": "shaphat"},
    ],
    "peace": [
        {"en": "peace", "greek": "eirene", "hebrew": "shalom"},
        {"en": "rest", "greek": "anapausis", "hebrew": "menukhah"},
    ],
    "light": [
        {"en": "light", "greek": "phos", "hebrew": "or"},
        {"en": "lamp", "greek": "luchnos", "hebrew": "ner"},
    ],
    "dark": [
        {"en": "dark", "greek": "skotos", "hebrew": "choshekh"},
        {"en": "darkness", "greek": "skotia", "hebrew": "afeilah"},
    ],
    "blood": [
        {"en": "blood", "greek": "haima", "hebrew": "dam"},
        {"en": "lifeblood", "greek": "psuche", "hebrew": "nefesh"},
    ],
    "bread": [
        {"en": "bread", "greek": "artos", "hebrew": "lechem"},
        {"en": "food", "greek": "brosis", "hebrew": "okhel"},
    ],
    "water": [
        {"en": "water", "greek": "hydor", "hebrew": "mayim"},
        {"en": "rain", "greek": "huetos", "hebrew": "geshem"},
    ],
    "king": [
        {"en": "king", "greek": "basileus", "hebrew": "melekh"},
        {"en": "kingdom", "greek": "basileia", "hebrew": "mamlakhah"},
    ],
    "sheep": [
        {"en": "sheep", "greek": "probaton", "hebrew": "tso'n"},
        {"en": "flock", "greek": "poimne", "hebrew": "eder"},
    ],
}

# Strong-style numeric lemma probes (existence in lexicon only)
STRONG_STYLE_PROBES: list[dict[str, Any]] = [
    {"prime_en": "god", "lang_probes": {"en": "theos", "greek": "theos", "hebrew": "elohim"}, "variant": "strong_greek"},
    {"prime_en": "god", "lang_probes": {"en": "elohim", "greek": "theos", "hebrew": "elohim"}, "variant": "strong_hebrew"},
    {"prime_en": "love", "lang_probes": {"en": "agape", "greek": "agape", "hebrew": "ahavah"}, "variant": "strong_greek"},
    {"prime_en": "word", "lang_probes": {"en": "logos", "greek": "logos", "hebrew": "dabar"}, "variant": "strong_greek"},
    {"prime_en": "spirit", "lang_probes": {"en": "pneuma", "greek": "pneuma", "hebrew": "ruach"}, "variant": "strong_greek"},
    {"prime_en": "covenant", "lang_probes": {"en": "diatheke", "greek": "diatheke", "hebrew": "berit"}, "variant": "strong_greek"},
    {"prime_en": "righteous", "lang_probes": {"en": "dikaios", "greek": "dikaios", "hebrew": "tsaddiq"}, "variant": "strong_greek"},
    {"prime_en": "sin", "lang_probes": {"en": "hamartia", "greek": "hamartia", "hebrew": "chet"}, "variant": "strong_greek"},
    {"prime_en": "faith", "lang_probes": {"en": "pistis", "greek": "pistis", "hebrew": "emunah"}, "variant": "strong_greek"},
    {"prime_en": "mercy", "lang_probes": {"en": "eleos", "greek": "eleos", "hebrew": "chesed"}, "variant": "strong_greek"},
    {"prime_en": "peace", "lang_probes": {"en": "eirene", "greek": "eirene", "hebrew": "shalom"}, "variant": "strong_greek"},
    {"prime_en": "light", "lang_probes": {"en": "phos", "greek": "phos", "hebrew": "or"}, "variant": "strong_greek"},
    {"prime_en": "king", "lang_probes": {"en": "basileus", "greek": "basileus", "hebrew": "melekh"}, "variant": "strong_greek"},
    {"prime_en": "bread", "lang_probes": {"en": "artos", "greek": "artos", "hebrew": "lechem"}, "variant": "strong_greek"},
    {"prime_en": "blood", "lang_probes": {"en": "haima", "greek": "haima", "hebrew": "dam"}, "variant": "strong_greek"},
    {"prime_en": "water", "lang_probes": {"en": "hydor", "greek": "hydor", "hebrew": "mayim"}, "variant": "strong_greek"},
    {"prime_en": "earth", "lang_probes": {"en": "ge", "greek": "ge", "hebrew": "eretz"}, "variant": "strong_greek"},
    {"prime_en": "heaven", "lang_probes": {"en": "ouranos", "greek": "ouranos", "hebrew": "shamayim"}, "variant": "strong_greek"},
    {"prime_en": "life", "lang_probes": {"en": "zoe", "greek": "zoe", "hebrew": "chayim"}, "variant": "strong_greek"},
    {"prime_en": "death", "lang_probes": {"en": "thanatos", "greek": "thanatos", "hebrew": "mavet"}, "variant": "strong_greek"},
]

# Semantic molecule probes (multi-token shallow existence checks)
MOLECULE_PROBES: list[dict[str, Any]] = [
    {"prime_en": "molecule_blood_covenant", "lang_probes": {"en": "blood", "greek": "haima", "hebrew": "dam"}},
    {"prime_en": "molecule_bread_life", "lang_probes": {"en": "bread", "greek": "artos", "hebrew": "lechem"}},
    {"prime_en": "molecule_spirit_truth", "lang_probes": {"en": "spirit", "greek": "pneuma", "hebrew": "ruach"}},
    {"prime_en": "molecule_faith_hope", "lang_probes": {"en": "faith", "greek": "pistis", "hebrew": "emunah"}},
    {"prime_en": "molecule_kingdom_glory", "lang_probes": {"en": "kingdom", "greek": "basileia", "hebrew": "mamlakhah"}},
    {"prime_en": "molecule_law_grace", "lang_probes": {"en": "law", "greek": "nomos", "hebrew": "torah"}},
    {"prime_en": "molecule_sin_death", "lang_probes": {"en": "sin", "greek": "hamartia", "hebrew": "chet"}},
    {"prime_en": "molecule_light_dark", "lang_probes": {"en": "light", "greek": "phos", "hebrew": "or"}},
    {"prime_en": "molecule_shepherd_flock", "lang_probes": {"en": "shepherd", "greek": "poimen", "hebrew": "ro'eh"}},
    {"prime_en": "molecule_temple_house", "lang_probes": {"en": "temple", "greek": "naos", "hebrew": "heikhal"}},
    {"prime_en": "molecule_promise_seed", "lang_probes": {"en": "seed", "greek": "sperma", "hebrew": "zera"}},
    {"prime_en": "molecule_judge_righteous", "lang_probes": {"en": "judge", "greek": "krino", "hebrew": "shaphat"}},
    {"prime_en": "molecule_voice_word", "lang_probes": {"en": "voice", "greek": "phone", "hebrew": "kol"}},
    {"prime_en": "molecule_holy_name", "lang_probes": {"en": "holy", "greek": "hagios", "hebrew": "qadosh"}},
    {"prime_en": "molecule_servant_master", "lang_probes": {"en": "servant", "greek": "doulos", "hebrew": "eved"}},
]

NEGATIVE_CONTROL_EXTRA: list[str] = [
    "uvicorn", "nextjs", "pytest", "docker", "kubernetes",
    "typescript", "react", "webpack", "postgres", "redis",
    "terraform", "graphql", "fastapi", "pandas", "numpy",
    "cloudflare", "kubernetes", "prometheus", "grafana", "nginx",
    "websocket", "mongodb", "elasticsearch", "kafka", "rabbitmq",
    "tailwind", "vite", "eslint", "prettier", "jest",
    "azure", "aws", "gcp", "lambda", "serverless",
    "oauth", "jwt", "bcrypt", "sha256", "openssl",
]

# Fill primes with generic greek/hebrew transliteration patterns
GENERIC_GREEK_HEBREW: dict[str, tuple[str, str]] = {
    "all": ("pas", "kol"),
    "world": ("kosmos", "olam"),
    "heart": ("kardia", "lev"),
    "soul": ("psuche", "nefesh"),
    "power": ("dunamis", "koach"),
    "glory": ("doxa", "kavod"),
    "truth": ("aletheia", "emet"),
    "wisdom": ("sophia", "chokhmah"),
    "fear": ("phobos", "yirah"),
    "hope": ("elpis", "tikvah"),
    "joy": ("chara", "simchah"),
    "anger": ("orge", "af"),
    "pain": ("odune", "tza'ar"),
    "hand": ("cheir", "yad"),
    "foot": ("pous", "regel"),
    "eye": ("ophthalmos", "ayin"),
    "ear": ("ous", "ozen"),
    "mouth": ("stoma", "peh"),
    "head": ("kephale", "rosh"),
    "face": ("prosopon", "panim"),
    "land": ("ge", "eretz"),
    "sea": ("thalassa", "yam"),
    "wind": ("anemos", "ruach"),
    "stone": ("lithos", "even"),
    "gold": ("chrusos", "zahav"),
    "silver": ("argurion", "kesef"),
    "iron": ("sidereos", "barzel"),
    "wood": ("xulon", "ets"),
    "field": ("agros", "sadeh"),
    "city": ("polis", "ir"),
    "gate": ("pule", "sha'ar"),
    "road": ("hodos", "derekh"),
    "mountain": ("oros", "har"),
    "valley": ("koilas", "gey"),
    "river": ("potamos", "nahar"),
    "star": ("aster", "kokhav"),
    "moon": ("selene", "yareach"),
    "cloud": ("nephele", "anan"),
    "rain": ("huetos", "geshem"),
    "snow": ("chion", "sheleg"),
    "fire": ("pur", "esh"),
    "smoke": ("kapnos", "ashan"),
    "altar": ("thusiasterion", "mizbeach"),
    "priest": ("hiereus", "kohen"),
    "prophet": ("prophetes", "navi"),
    "angel": ("aggelos", "malakh"),
    "devil": ("diabolos", "satan"),
    "enemy": ("echthros", "oyev"),
    "friend": ("philos", "rea"),
    "brother": ("adelphos", "ach"),
    "sister": ("adelphe", "achot"),
    "father": ("pater", "av"),
    "mother": ("meter", "em"),
    "son": ("huios", "ben"),
    "daughter": ("thugater", "bat"),
    "wife": ("gune", "ishah"),
    "husband": ("aner", "ish"),
    "slave": ("doulos", "eved"),
    "master": ("kurios", "adon"),
    "gift": ("doron", "matanah"),
    "gold_coin": ("argurion", "kesef"),
    "war": ("polemos", "milchamah"),
    "peace_alt": ("eirene", "shalom"),
    "sword": ("machaira", "cherev"),
    "shield": ("thureos", "magen"),
    "tent": ("skene", "ohel"),
    "tabernacle": ("skene", "mishkan"),
    "law": ("nomos", "torah"),
    "commandment": ("entole", "mitsvah"),
    "witness": ("martus", "ed"),
    "testimony": ("marturia", "edut"),
    "sign": ("semeion", "ot"),
    "wonder": ("teras", "mofet"),
    "miracle": ("dunamis", "nes"),
    "heal": ("iaomai", "rapha"),
    "sick": ("asthenes", "choleh"),
    "blind": ("tuphlos", "iver"),
    "deaf": ("kophos", "cheresh"),
    "lame": ("cholos", "pisheach"),
    "clean": ("katharos", "tahor"),
    "unclean": ("akathartos", "tame"),
    "holy": ("hagios", "qadosh"),
    "profane": ("bebelos", "chol"),
    "bless": ("eulogeo", "barakh"),
    "curse": ("katara", "arur"),
    "praise": ("aineo", "hallal"),
    "pray": ("proseuchomai", "palal"),
    "fast": ("nesteuo", "tsom"),
    "feast": ("heorte", "chag"),
    "sabbath": ("sabbaton", "shabbat"),
    "passover": ("pascha", "pesach"),
    "lamb": ("arnion", "seh"),
    "vine": ("ampelos", "gefen"),
    "branch": ("klados", "anaf"),
    "fruit": ("karpos", "pri"),
    "harvest": ("therismos", "katsir"),
    "sow": ("speiro", "zara"),
    "reap": ("therizo", "katsar"),
    "vineyard": ("ampelon", "kerem"),
    "garden": ("kepos", "gan"),
    "desert": ("eremos", "midbar"),
    "wilderness": ("eremos", "midbar"),
    "wild_beast": ("therion", "chayah"),
    "bird": ("peteinon", "tsippor"),
    "fish": ("ichthus", "dag"),
    "snake": ("ophis", "nachash"),
    "lion": ("leon", "ari"),
    "wolf": ("lukos", "ze'ev"),
    "bear": ("arktos", "dov"),
    "ox": ("bous", "shor"),
    "donkey": ("onos", "chamor"),
    "horse": ("hippos", "sus"),
    "camel": ("kamelos", "gamal"),
    "dog": ("kuon", "kelev"),
    "cat": ("ailouros", "hatul"),
    "honey": ("meli", "devash"),
    "oil": ("elaion", "shemen"),
    "salt": ("halas", "melach"),
    "wine": ("oinos", "yayin"),
    "milk": ("gala", "chalav"),
    "meat": ("kreas", "basar"),
    "fat": ("piar", "chelev"),
    "bone": ("osteon", "etsem"),
    "skin": ("derma", "or"),
    "hair": ("thrix", "se'ar"),
    "tear": ("dakru", "dimah"),
    "weep": ("klaio", "bakah"),
    "laugh": ("gelao", "tzachak"),
    "sleep": ("hypnos", "shenah"),
    "dream": ("onar", "chalom"),
    "wake": ("egeiro", "ur"),
    "stand": ("histemi", "amad"),
    "sit": ("kathemai", "yashav"),
    "walk": ("peripateo", "halakh"),
    "run": ("trecho", "ruts"),
    "fall": ("pipto", "nafal"),
    "rise": ("anistemi", "kam"),
    "give": ("didomi", "natan"),
    "take": ("lambano", "laqach"),
    "send": ("apostello", "shalach"),
    "come": ("erchomai", "bo"),
    "go": ("poreuomai", "halakh"),
    "return": ("epistrepho", "shuv"),
    "leave": ("aphiemi", "azav"),
    "find": ("heurisko", "matza"),
    "lose": ("apollumi", "avad"),
    "hide": ("krupto", "taman"),
    "show": ("deiknuo", "ra'ah"),
    "open": ("anoigo", "patah"),
    "close": ("kleio", "sagar"),
    "break": ("rhegnumi", "shavar"),
    "build": ("oikodomeo", "banah"),
    "destroy": ("kataluo", "shachat"),
    "create": ("ktizo", "bara"),
    "make": ("poieo", "asah"),
    "begin": ("archomai", "hatchilah"),
    "end": ("telos", "sof"),
    "forever": ("aion", "olam"),
    "always": ("pantote", "tamid"),
    "never": ("oudepote", "lo"),
    "often": ("pollakis", "rab"),
    "seldom": ("oligos", "me'at"),
    "again": ("palin", "shuv"),
    "once": ("apax", "pa'am"),
    "twice": ("dis", "pa'amayim"),
    "many": ("polus", "rabim"),
    "few": ("oligos", "me'at"),
    "every": ("pas", "kol"),
    "some": ("tis", "ketzat"),
    "none": ("oudeis", "efes"),
    "same_alt": ("autos", "zeh"),
    "different": ("allos", "acher"),
    "new": ("neos", "chadash"),
    "old": ("palaios", "yashan"),
    "young": ("neos", "tza'ir"),
    "first": ("protos", "rishon"),
    "last": ("eschatos", "acharon"),
    "middle": ("mesos", "tavekh"),
    "whole": ("holos", "kol"),
    "half": ("hemisu", "chatzi"),
    "full": ("pleres", "male"),
    "empty": ("kenos", "req"),
    "heavy": ("barus", "kaved"),
    "light_weight": ("elaphros", "qal"),
    "hard": ("skleros", "kasheh"),
    "soft": ("malakos", "rakh"),
    "hot": ("thermos", "cham"),
    "cold": ("psuchros", "kar"),
    "wet": ("hugros", "lach"),
    "dry": ("xeros", "yavesh"),
    "sweet": ("glukus", "matok"),
    "bitter": ("pikros", "mar"),
    "sour": ("oxos", "chamutz"),
    "strong": ("ischuros", "chazak"),
    "weak": ("asthenes", "chalash"),
    "rich": ("plousios", "ashir"),
    "poor": ("ptochos", "ani"),
    "free": ("eleutheros", "chofshi"),
    "bind": ("deo", "asar"),
    "loose": ("luo", "patach"),
    "save": ("sozo", "hoshia"),
    "destroy_alt": ("apollumi", "shachat"),
    "help": ("boetheo", "azar"),
    "fight": ("machomai", "lacham"),
    "win": ("nikao", "natsach"),
    "lose_alt": ("hettao", "nafal"),
    "teach": ("didasko", "lamad"),
    "learn": ("manthano", "lamed"),
    "write": ("grapho", "katav"),
    "read": ("anaginosko", "qara"),
    "count": ("arithmeo", "saphar"),
    "measure": ("metreo", "madad"),
    "weigh": ("stathmizo", "shaqal"),
    "buy": ("agorazo", "qanah"),
    "sell": ("poleo", "makhar"),
    "pay": ("apodidomi", "shalem"),
    "owe": ("opheilo", "chov"),
    "borrow": ("daneizo", "lavah"),
    "lend": ("kichremizo", "havah"),
    "inherit": ("kleronomew", "nachal"),
    "own": ("ktao", "qanah"),
    "steal": ("klepto", "ganav"),
    "lie": ("pseudomai", "sheker"),
    "truth_alt": ("aletheia", "emet"),
    "promise_alt": ("epaggellomai", "nadar"),
    "swear": ("omnuo", "shava"),
    "forgive": ("aphiemi", "salach"),
    "repent": ("metanoeo", "shuv"),
    "turn": ("strepho", "panah"),
    "obey": ("hupakouo", "shama"),
    "disobey": ("apeitheo", "marad"),
    "serve": ("douleuo", "avad"),
    "rule": ("basileuo", "malakh"),
    "lead": ("hegeomai", "nachah"),
    "follow": ("akoloutheo", "halakh"),
    "call": ("kaleo", "qara"),
    "answer": ("apokrinomai", "anah"),
    "ask": ("eperotao", "sha'al"),
    "tell_alt": ("lego", "nagad"),
    "keep": ("tereo", "shamar"),
    "forget": ("epilanthanomai", "shachach"),
    "remember": ("mnemoneuo", "zachar"),
    "trust": ("pisteuo", "batach"),
    "doubt": ("distazo", "safak"),
    "hope_alt": ("elpizo", "yachal"),
    "despair": ("exaporphoumai", "ya'ash"),
    "love_alt": ("phileo", "ahav"),
    "hate": ("miseo", "sane"),
    "kindness": ("chrestotes", "chesed"),
    "patience": ("makrothumia", "erekh"),
    "humility": ("tapeinophrosune", "anavah"),
    "pride": ("huperephania", "ga'avah"),
    "anger_alt": ("thumos", "af"),
    "gentleness": ("prautes", "anavah"),
    "self_control": ("egkrateia", "gibur"),
    "faithfulness": ("pistos", "ne'eman"),
    "goodness": ("agathosune", "tov"),
    "longsuffering": ("makrothumia", "erekh"),
}


def _sample_from_lang(prime_en: str, lang: dict[str, str], *, variant: str | None = None) -> dict[str, Any]:
    en = str(lang.get("en") or "").strip().lower()
    greek = str(lang.get("greek") or "").strip().lower()
    hebrew = str(lang.get("hebrew") or "").strip().lower()
    tokens = [t for t in [en, greek, hebrew] if t]
    row: dict[str, Any] = {
        "prime_en": prime_en,
        "probe_tokens": tokens,
        "lang_probes": {"en": en, "greek": greek, "hebrew": hebrew},
    }
    if variant:
        row["variant"] = variant
    return row


def _negative(token: str) -> dict[str, Any]:
    t = token.strip().lower()
    return {
        "prime_en": f"control_negative_{t.replace('-', '_')}",
        "probe_tokens": [t],
        "control": "negative",
        "lang_probes": {"en": t},
    }


def build_500_samples(*, target: int = 500) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    seen: set[str] = set()

    def add(row: dict[str, Any]) -> None:
        lang = row.get("lang_probes") if isinstance(row.get("lang_probes"), dict) else {}
        key = "|".join(
            [
                str(row.get("prime_en") or ""),
                str(row.get("control") or ""),
                str(lang.get("en") or ""),
                str(lang.get("greek") or ""),
                str(lang.get("hebrew") or ""),
                str(row.get("variant") or ""),
            ]
        )
        if key in seen:
            return
        seen.add(key)
        out.append(row)

    for row in NSM_CROSSWALK_100:
        add(dict(row))

    for prime, variants in VARIANT_PROBES.items():
        for v in variants:
            add(_sample_from_lang(prime, v, variant="morph_variant"))

    for row in STRONG_STYLE_PROBES:
        lang = row.get("lang_probes") if isinstance(row.get("lang_probes"), dict) else {}
        add(_sample_from_lang(str(row.get("prime_en") or ""), lang, variant=str(row.get("variant") or "")))

    for row in MOLECULE_PROBES:
        lang = row.get("lang_probes") if isinstance(row.get("lang_probes"), dict) else {}
        add(_sample_from_lang(str(row.get("prime_en") or ""), lang, variant="molecule"))

    for prime, (greek, hebrew) in GENERIC_GREEK_HEBREW.items():
        add(_sample_from_lang(prime, {"en": prime.replace("_", " "), "greek": greek, "hebrew": hebrew}, variant="generic_fill"))

    for tok in NEGATIVE_CONTROL_EXTRA:
        add(_negative(tok))

    if len(out) > target:
        negatives = [r for r in out if r.get("control") == "negative"]
        non_neg = [r for r in out if r.get("control") != "negative"]
        keep_neg = negatives[: max(25, len([r for r in NSM_CROSSWALK_100 if r.get("control") == "negative"]))]
        keep_non = non_neg[: target - len(keep_neg)]
        out = keep_non + keep_neg

    while len(out) < target:
        idx = len(out)
        add(_negative(f"synthetic_control_{idx}"))

    if len(out) != target:
        raise ValueError(f"expected {target} samples, got {len(out)}")
    return out


def export_fixture(path: Path, *, target: int = 500) -> dict[str, Any]:
    samples = build_500_samples(target=target)
    doc = {
        "schema": "nsm_41k_lexicon_crosswalk_500_v1",
        "version": "1.0.0",
        "description": "500-pair NSM prime → Logos lexicon probe catalog (100 base + structured expansion).",
        "source_note": "build_nsm_41k_crosswalk_500_fixture_v1.py; distortion audit via run_nsm_41k_lexicon_crosswalk_audit_v1.py",
        "research_only": True,
        "send_gate": "HOLD",
        "pair_count": len(samples),
        "base_catalog": "scripts/nsm_41k_crosswalk_catalog_v1.py:NSM_CROSSWALK_100",
        "samples": samples,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return doc


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--target", type=int, default=500)
    args = ap.parse_args()
    doc = export_fixture(args.out, target=args.target)
    print(json.dumps({"ok": True, "pair_count": doc["pair_count"], "out": str(args.out)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
