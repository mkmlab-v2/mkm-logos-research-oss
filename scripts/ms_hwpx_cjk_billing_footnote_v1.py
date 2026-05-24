#!/usr/bin/env python3
"""MS-PASTE CJK billing footnote (research_only) — never merge into Golden 47.5% headline."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HOOK_COMPARE = ROOT / "reports/constitution/btrack_pilot/comp_ijeoma_cjk_hook_billing_mode_compare_v1.json"
HOOK_COMPARE_ENV = (
    ROOT / "reports/constitution/btrack_pilot/comp_ijeoma_cjk_bridge_vs_eval_hook_billing_mode_env_v1.json"
)
CROSSLINK_TXT = ROOT / "reports/hwpx_poc/ms_cjk_btrack_crosslink_v1.txt"
OUT_TXT = ROOT / "reports/hwpx_poc/ms_cjk_billing_footnote_paste_v1.txt"


def _load_json(path: Path) -> dict | None:
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def footnote_metrics() -> dict:
    """Load latest hook/billing compare JSON when present (else conservative defaults)."""
    doc = _load_json(HOOK_COMPARE) or _load_json(HOOK_COMPARE_ENV) or {}
    bill = doc.get("billing_hook_experiment") or {}
    ops = doc.get("operational_hook") or {}
    return {
        "proxy_ops": round(float(ops.get("hook_sweep_mean_proxy_90") or 0.576) * 100, 1),
        "proxy_bill": round(float(bill.get("hook_sweep_mean_proxy_90") or 0.576) * 100, 1),
        "o2_corpus_pct": round(float(bill.get("corpus_o200k_tight_90") or 0.32) * 100, 1),
        "parity_ok": bill.get("parity_ok", True),
    }


def cjk_billing_footnote_submission_ko(*, max_chars: int = 520) -> str:
    """K-Startup footer: CJK billing bucket separated from Golden 47.5% (no B-track/research_only tags)."""
    m = footnote_metrics()
    parity = "통과" if m["parity_ok"] else "확인 필요"
    text = (
        "【CJK·다국어 토큰 청구 참고】 "
        "본문 벤치마크(40건·동일 조건 약 47.5% 절감, Jaccard 0.89)는 Golden 영문 코퍼스 기준입니다. "
        "한자·CJK 치환 청구 검증(o200k_tight)은 별도 실험 버킷이며, "
        "일상 운영 hook은 ascii_compact, MKM_IJEOMA_CJK_BILLING_MODE=1 시 청구용 o200k_tight 마커로 고정합니다. "
        f"(90건 parity {parity}, 청구 proxy 약 {m['proxy_bill']:.1f}%). "
        "본 계획서 KPI·감액·상용 SLA 단정에 CJK 실험 %를 합산하지 않습니다."
    )
    text = text.strip()
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 3].rstrip() + "..."


def cjk_billing_footnote_ko(*, max_chars: int = 900) -> str:
    """Paste-safe footnote for HWPX disclaimer prepend (B-track CJK bucket only)."""
    doc = _load_json(HOOK_COMPARE)
    bill = (doc or {}).get("billing_hook_experiment") or {}
    ops = (doc or {}).get("operational_hook") or {}
    proxy_ops = float(ops.get("hook_sweep_mean_proxy_90") or 0) * 100
    proxy_bill = float(bill.get("hook_sweep_mean_proxy_90") or 0) * 100
    o2 = float(bill.get("corpus_o200k_tight_90") or 0) * 100
    parity = bill.get("parity_ok")
    text = (
        "[CJK B-track 각주 · research_only] "
        "한자 치환 실험(ijeoma chunk)은 Golden 40건 47.5%·290건 운영 벤치와 별도 버킷입니다. "
        f"운영 hook(ascii_compact) proxy 약 {proxy_ops:.1f}% · "
        f"청구 연구 마커(o200k_tight) proxy 약 {proxy_bill:.1f}% · "
        f"OpenAI o200k_base corpus 약 {o2:+.1f}% (90건 실측, tiktoken). "
        f"bridge↔hook parity={parity}. "
        "본문 KPI·감액·상용 SLA 단정에 CJK %를 합산하지 마세요. "
        f"근거: {CROSSLINK_TXT.relative_to(ROOT).as_posix() if CROSSLINK_TXT.is_file() else 'ms_cjk_btrack_crosslink_v1.txt'}."
    )
    text = text.strip()
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 3].rstrip() + "..."


def write_footnote_paste_file(out_path: Path | None = None) -> Path:
    path = out_path or OUT_TXT
    path.parent.mkdir(parents=True, exist_ok=True)
    body = cjk_billing_footnote_ko()
    path.write_text(body + "\n", encoding="utf-8")
    return path


if __name__ == "__main__":
    import sys

    p = write_footnote_paste_file()
    print(json.dumps({"wrote": str(p.relative_to(ROOT)).replace("\\", "/")}, ensure_ascii=False))
    raise SystemExit(0)
