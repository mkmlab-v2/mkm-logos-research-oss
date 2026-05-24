#!/usr/bin/env python3
"""Build K-Startup majung paste assistant (external browser companion)."""
from __future__ import annotations

import html
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PASTE = ROOT / "reports" / "kstartup_majung_paste_ready"
ORDER = [
    ("Step1 · 과제내용", "bmo0902_step1_gwaje_nae_yong_paste.txt", True),
    ("문제·필요성", "bmo0902_need_problem_paste.txt", True),
    ("해결·차별", "bmo0902_solution_diff_paste.txt", True),
    ("Microsoft/Azure", "bmo0902_microsoft_synergy_paste.txt", True),
    ("KPI·데모", "bmo0902_kpi_demo_paste.txt", True),
    ("사업화·시장", "bmo0902_business_market_paste.txt", True),
    ("면책 하단", "bmo0902_disclaimer_paste.txt", True),
]
OUT = ROOT / "reports" / "demo" / "kstartup_majung_paste_assistant_v1.html"


def main() -> int:
    sections: list[dict[str, str]] = []
    for title, name, required in ORDER:
        p = PASTE / name
        if not p.is_file():
            if required:
                raise SystemExit(f"missing required paste: {p}")
            continue
        body = p.read_text(encoding="utf-8")
        sections.append({"title": title, "name": name, "chars": len(body), "body": body})

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    parts = [
        "<!DOCTYPE html><html lang='ko'><head><meta charset='utf-8'/>",
        "<meta name='viewport' content='width=device-width,initial-scale=1'/>",
        "<title>K-Startup Majung Paste Assistant</title>",
        "<style>",
        "body{font-family:system-ui,sans-serif;background:#0a0b0d;color:#e8eaef;margin:0;padding:1.5rem;max-width:900px}",
        "h1{font-size:1.1rem} .meta{color:#8b919d;font-size:.85rem;margin-bottom:1.5rem}",
        "section{margin:1.25rem 0;padding:1rem;border:1px solid rgba(255,255,255,.1);border-radius:12px}",
        "button{margin:.5rem .5rem .5rem 0;padding:.5rem 1rem;border-radius:8px;border:1px solid #0a84ff;background:#0d2847;color:#e8f4ff;cursor:pointer}",
        "pre{white-space:pre-wrap;font-size:.8rem;color:#aab;line-height:1.45;max-height:10rem;overflow:auto}",
        ".toast{position:fixed;bottom:1rem;right:1rem;background:#14532d;color:#ecfdf5;padding:.75rem 1rem;border-radius:8px;display:none}",
        "</style></head><body>",
        "<h1>K-Startup 마중 · BMO0902 붙여넣기 보조</h1>",
        f"<p class='meta'>생성: {html.escape(ts)} · 외부 Chrome/Edge 전용 · passni SSO 내장 브라우저 ❌</p>",
        "<p>PMS 양식 탭과 나란히 두고 <strong>클립보드 복사</strong> → 필드 붙여넣기. 매 화면 <strong>임시저장</strong>.</p>",
    ]
    for i, s in enumerate(sections):
        sid = f"s{i}"
        parts.append(
            f"<section id='{sid}'><h2>{html.escape(s['title'])} "
            f"<small>({s['chars']} chars)</small></h2>"
        )
        parts.append(f"<button type='button' data-copy='{sid}'>클립보드 복사</button>")
        parts.append(f"<pre id='{sid}-pre'>{html.escape(s['body'])}</pre></section>")

    parts.append(
        "<div id='toast' class='toast'>복사됨</div><script>"
        "document.querySelectorAll('[data-copy]').forEach(btn=>{"
        "btn.onclick=()=>{const id=btn.dataset.copy;const t=document.getElementById(id+'-pre').textContent;"
        "navigator.clipboard.writeText(t).then(()=>{const toast=document.getElementById('toast');"
        "toast.style.display='block';setTimeout(()=>toast.style.display='none',1200);});};});"
        "</script></body></html>"
    )
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("".join(parts), encoding="utf-8")
    print(json_out := __import__("json").dumps({"out": str(OUT), "sections": len(sections)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
