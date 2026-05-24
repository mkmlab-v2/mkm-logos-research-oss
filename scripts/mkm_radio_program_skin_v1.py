"""O-P31c program skins — shared factory, different public copy guards."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, List, Tuple

ScanFn = Callable[[str], List[str]]
DisclaimerOkFn = Callable[[str], bool]


@dataclass(frozen=True)
class ProgramSkin:
    skin_id: str
    disclaimer_text_ko: str
    closing_cta_ko: str
    disclaimer_required_snippets: Tuple[str, ...]
    scan_forbidden: ScanFn
    disclaimer_ok: DisclaimerOkFn


def _load_mkm():
    from scripts import mkm_radio_dialogue_guard_v1 as g

    return ProgramSkin(
        skin_id="mkm_radio",
        disclaimer_text_ko=g.DISCLAIMER_TEXT_KO,
        closing_cta_ko=g.CLOSING_CTA_KO,
        disclaimer_required_snippets=tuple(g.DISCLAIMER_REQUIRED_SNIPPETS),
        scan_forbidden=g.scan_forbidden,
        disclaimer_ok=g.disclaimer_ok,
    )


def _load_tkm_health():
    from scripts import tkm_health_dialogue_guard_v1 as g

    return ProgramSkin(
        skin_id="tkm_health_24h",
        disclaimer_text_ko=g.DISCLAIMER_TEXT_KO,
        closing_cta_ko=g.CLOSING_CTA_KO,
        disclaimer_required_snippets=tuple(g.DISCLAIMER_REQUIRED_SNIPPETS),
        scan_forbidden=g.scan_forbidden,
        disclaimer_ok=g.disclaimer_ok,
    )


_SKINS = {
    "mkm_radio": _load_mkm,
    "tkm_health_24h": _load_tkm_health,
}


def resolve_skin_id(doc: dict) -> str:
    explicit = str(doc.get("program_skin") or "").strip()
    if explicit in _SKINS:
        return explicit
    style = str(doc.get("program_style") or "")
    if style.startswith("health_") or style == "health_shorts_5m":
        return "tkm_health_24h"
    return "mkm_radio"


def get_skin(doc: dict) -> ProgramSkin:
    return _SKINS[resolve_skin_id(doc)]()
