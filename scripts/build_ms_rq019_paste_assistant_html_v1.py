#!/usr/bin/env python3
"""Build local MS RQ-019 paste assistant (copy buttons, no form URL required)."""
from __future__ import annotations

import html
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PASTE = ROOT / "reports" / "ms_rq019_paste_ready"
ORDER = [
    ("K1 문제", "k1_problem_paste.txt", True),
    ("K2 방법", "k2_method_paste.txt", True),
    ("K2 투 트랙 (선택)", "k2_two_track_architecture_paste.txt", False),
    ("K3 차별", "k3_differentiation_paste.txt", True),
    ("면책 하단", "disclaimer_footer_paste.txt", True),
    ("FinOps L1 (선택)", "finops_l1_official_status_paste.txt", False),
    ("K3 Visual Path (선택)", "k3_visual_reasoning_path_appendix_paste.txt", False),
    ("TECH MOAT (선택)", "technical_moat_sector_paste.txt", False),
    ("수리 SSOT (선택)", "math_formula_ssot_moat_appendix_paste.txt", False),
    ("O-P5 한 줄", "op5_ms_paste_one_liner.txt", False),
]
OUT = ROOT / "reports" / "demo" / "ms_rq019_paste_assistant_v1.html"
FUSION = ROOT / "reports" / "hwpx_poc" / "ms_ma_jung_fusion_check_latest.json"
HWPX_DL = Path(r"C:\Users\PRO\Downloads\별첨1-2_마중_사업계획서_MKM_공고329.hwp")


def _fusion_banner() -> str:
    if not FUSION.is_file():
        return ""
    try:
        f = json.loads(FUSION.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return ""
    paste = f.get("paste_vs_hwpx_prefix_match") or {}
    ok = all(paste.values()) if paste else False
    infra = (f.get("infra") or {}).get("paste_pack") or {}
    lines = [
        "<div style='margin:1rem 0;padding:1rem;border:1px solid rgba(110,231,183,.35);"
        "border-radius:12px;background:rgba(6,78,59,.25)'>",
        "<strong>융합 상태 (HWPX + paste + live)</strong><ul style='margin:.5rem 0 0 1rem;"
        "font-size:.85rem;color:#aab'>",
        f"<li>HWPX↔paste K1/K2/K3: <strong>{'일치' if ok else '불일치'}</strong></li>",
        f"<li>paste pack: ok={infra.get('ok')} · wire/v6 HTTP {((infra.get('urls') or {}).get('wire_v3') or {}).get('http')}</li>",
        f"<li>별첨 HWPX: <code>{html.escape(str(HWPX_DL))}</code> (한컴은 .hwp)</li>",
        "<li>O-P5·personadiary: 토큰 불필요 · CF API 403=자동화만</li>",
        "<li>수동: 실명·T4 합계 00백만·※삭제·기술분야 체크</li>",
        "</ul></div>",
    ]
    return "".join(lines)


def main() -> int:
    sections: list[dict[str, str]] = []
    for title, name, required in ORDER:
        p = PASTE / name
        if not p.is_file():
            if required:
                raise SystemExit(f"missing required paste: {p}")
            continue
        sections.append(
            {
                "title": title,
                "name": name,
                "chars": len(p.read_text(encoding="utf-8")),
                "body": p.read_text(encoding="utf-8"),
            }
        )

    gif = PASTE / "ms_rq019_oracle_v6_visual_path_10s.gif"
    meta = {
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "gif": str(gif) if gif.is_file() else "",
        "op5": "https://jema12.com/studio → v6 (CF rule jema12-studio-oracle-v6)",
    }

    parts = [
        "<!DOCTYPE html><html lang='ko'><head><meta charset='utf-8'/>",
        "<meta name='viewport' content='width=device-width,initial-scale=1'/>",
        "<title>MS RQ-019 Paste Assistant</title>",
        "<style>",
        "body{font-family:system-ui,sans-serif;background:#0a0b0d;color:#e8eaef;margin:0;padding:1.5rem;max-width:900px}",
        "h1{font-size:1.1rem} .meta{color:#8b919d;font-size:.85rem;margin-bottom:1.5rem}",
        "section{margin:1.25rem 0;padding:1rem;border:1px solid rgba(255,255,255,.1);border-radius:12px}",
        "button{margin:.5rem .5rem .5rem 0;padding:.5rem 1rem;border-radius:8px;border:1px solid #c5a057;background:#1a1510;color:#f5e6c8;cursor:pointer}",
        "button.ok{border-color:#6ee7b7;color:#d1fae5}",
        "pre{white-space:pre-wrap;font-size:.8rem;color:#aab;line-height:1.45;max-height:8rem;overflow:auto}",
        ".toast{position:fixed;bottom:1rem;right:1rem;background:#14532d;color:#ecfdf5;padding:.75rem 1rem;border-radius:8px;display:none}",
        "</style></head><body>",
        "<h1>MS RQ-019 · 양식 붙여넣기 보조</h1>",
        f"<p class='meta'>생성: {html.escape(meta['generated_at_utc'])} · O-P5: {html.escape(meta['op5'])}</p>",
        "<p>MS 제출 포털을 <strong>다른 탭</strong>에서 연 뒤, 각 섹션 <strong>클립보드 복사</strong> → 양식 필드에 붙여넣기.</p>",
        _fusion_banner(),
        "<p class='meta'><strong>이중 제출:</strong> K-Startup 웹 필드 = 아래 paste · "
        "별첨1-2 HWPX = Downloads <code>별첨1-2_마중_…공고329.hwp</code> (이미 채움, paste와 본문 정합).</p>",
    ]
    for i, s in enumerate(sections):
        sid = f"s{i}"
        body_esc = html.escape(s["body"])
        parts.append(f"<section id='{sid}'><h2>{html.escape(s['title'])} <small>({s['chars']} chars · {html.escape(s['name'])})</small></h2>")
        parts.append(f"<button type='button' data-copy='{sid}'>클립보드 복사</button>")
        parts.append(f"<pre id='{sid}-pre'>{body_esc}</pre></section>")

    if meta["gif"]:
        parts.append(f"<section><h2>GIF (K3 부록)</h2><p class='meta'>{html.escape(meta['gif'])}</p><p>파일 탐색기에서 드래그·첨부.</p></section>")

    parts.append(
        "<div id='toast' class='toast'>복사됨</div><script>"
        "document.querySelectorAll('[data-copy]').forEach(btn=>{"
        "btn.onclick=()=>{const id=btn.dataset.copy;const t=document.getElementById(id+'-pre').textContent;"
        "navigator.clipboard.writeText(t).then(()=>{const toast=document.getElementById('toast');"
        "toast.style.display='block';btn.classList.add('ok');setTimeout(()=>toast.style.display='none',1200);});};});"
        "</script></body></html>"
    )

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("".join(parts), encoding="utf-8")
    print(json.dumps({"out": str(OUT), "sections": len(sections)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
