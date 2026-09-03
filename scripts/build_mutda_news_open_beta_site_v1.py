#!/usr/bin/env python3
"""Build MUTDA News OPEN_BETA static site from sealed EP01 + format artifacts.

Reads:
  docs/final/artifacts/mkm_mutda_series_ep01_v1_latest.json
  docs/final/artifacts/mkm_mutda_series_format_v1_latest.json
Writes:
  projects/mutda-news-open-beta-v1/public/**

PRODUCT_DONE is never claimed. OPEN_BETA surface only.
"""
from __future__ import annotations

import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EP01_PATH = ROOT / "docs" / "final" / "artifacts" / "mkm_mutda_series_ep01_v1_latest.json"
FORMAT_PATH = ROOT / "docs" / "final" / "artifacts" / "mkm_mutda_series_format_v1_latest.json"
OUT_DIR = ROOT / "projects" / "mutda-news-open-beta-v1" / "public"
SITE_ORIGIN = "https://mutda.ai"
PROVENANCE_EP01 = "docs/final/artifacts/mkm_mutda_series_ep01_v1_latest.json"
PROVENANCE_FORMAT = "docs/final/artifacts/mkm_mutda_series_format_v1_latest.json"

SHARED_CSS = """
:root {
  --ink:#0b1c22; --ink-soft:#24363d; --paper:#f3f6f7; --line:rgba(11,28,34,.12);
  --teal:#0f6b66; --teal-deep:#0a4f4b; --sand:#c9a66b; --danger:#8a3a2a;
  --ok:#1f6b4a; --muted:#5b6d74; --max:1120px;
}
*{box-sizing:border-box}
html{scroll-behavior:smooth}
body{
  margin:0;font-family:"IBM Plex Sans KR",sans-serif;color:var(--ink);
  background:
    radial-gradient(1100px 650px at 10% -8%,rgba(15,107,102,.16),transparent 55%),
    radial-gradient(800px 480px at 92% 6%,rgba(201,166,107,.12),transparent 50%),
    linear-gradient(180deg,#eef3f4 0%,var(--paper) 45%,#e9eff1 100%);
  min-height:100vh;
}
.beta{background:var(--teal-deep);color:#e8f4f3;font-size:12px;padding:8px 16px;text-align:center}
.beta strong{color:var(--sand);letter-spacing:.04em}
header.top{
  max-width:var(--max);margin:0 auto;padding:16px 20px 0;
  display:flex;justify-content:space-between;gap:12px;align-items:center;flex-wrap:wrap;
}
.brand{font-family:"Noto Serif KR",serif;font-size:26px;font-weight:700;color:var(--ink);text-decoration:none}
.nav{display:flex;flex-wrap:wrap;gap:8px}
.nav a{
  border:1px solid var(--line);background:rgba(255,255,255,.55);border-radius:999px;
  padding:8px 12px;font:500 13px "IBM Plex Sans KR",sans-serif;color:var(--ink-soft);text-decoration:none;
}
.nav a[aria-current="page"]{background:var(--ink);color:#fff;border-color:var(--ink)}
.hero{max-width:var(--max);margin:0 auto;padding:36px 20px 12px;display:grid;gap:22px}
@media(min-width:960px){.hero{grid-template-columns:1.05fr .95fr;align-items:center}}
.hero h1{font-family:"Noto Serif KR",serif;font-size:clamp(32px,5vw,50px);line-height:1.18;margin:0;letter-spacing:-.03em}
.tagline{margin:14px 0 0;font-weight:600;font-size:17px;max-width:36ch;color:var(--teal-deep)}
.sub{margin:8px 0 0;color:var(--ink-soft);font-size:14px;line-height:1.55;max-width:42ch}
.badge{
  display:inline-block;margin-top:12px;font-size:11px;font-weight:700;letter-spacing:.08em;
  padding:4px 9px;border-radius:6px;border:1px solid rgba(15,107,102,.35);
  color:var(--teal-deep);background:rgba(15,107,102,.08);
}
.cta-row{display:flex;flex-wrap:wrap;gap:8px;margin-top:16px}
.btn{
  border:0;border-radius:12px;padding:0 16px;min-height:46px;display:inline-flex;align-items:center;
  cursor:pointer;font:600 13px "IBM Plex Sans KR",sans-serif;text-decoration:none;
}
.btn-primary{background:var(--teal);color:#fff}
.btn-ghost{background:transparent;border:1px solid var(--line);color:var(--ink-soft)}
.flow{background:rgba(255,255,255,.62);border:1px solid var(--line);border-radius:18px;padding:14px}
.flow .lbl{font-size:11px;letter-spacing:.06em;color:var(--muted);font-weight:600;margin-bottom:8px}
.step{display:grid;grid-template-columns:78px 1fr;gap:8px;padding:8px 0;border-top:1px dashed var(--line);font-size:14px;color:var(--ink-soft)}
.step b{font-family:"Noto Serif KR",serif;color:var(--teal-deep);font-size:13px}
.today,.page{max-width:var(--max);margin:0 auto;padding:8px 20px 48px}
.today h2,.page h1,.page h2{font-family:"Noto Serif KR",serif}
.today h2{font-size:22px;margin:8px 0 6px}
.lead{margin:0 0 14px;color:var(--muted);font-size:13px}
.issue-row{border-top:1px solid var(--line);padding:14px 0;display:grid;gap:8px}
.issue-row h3{margin:0;font-family:"Noto Serif KR",serif;font-size:18px}
.meta{font-size:12px;color:var(--muted)}
.row-cta{display:flex;flex-wrap:wrap;gap:8px;align-items:center}
.brief-head{max-width:var(--max);margin:0 auto;padding:28px 20px 6px}
.eyebrow{color:var(--teal);font-size:12px;font-weight:600;letter-spacing:.06em}
.brief-head h1{font-family:"Noto Serif KR",serif;font-size:clamp(24px,3.8vw,34px);margin:8px 0;max-width:28ch}
.layer{max-width:var(--max);margin:0 auto;padding:20px;border-top:1px solid var(--line)}
.layer h2{font-family:"Noto Serif KR",serif;font-size:20px;margin:0 0 6px}
.purpose{margin:0 0 12px;color:var(--muted);font-size:13px}
.prose{font-size:15px;line-height:1.65;color:var(--ink-soft);max-width:62ch}
.prose p{margin:0 0 12px}
.prose ul{margin:0 0 12px;padding-left:1.2em}
.lens-note{
  display:inline-block;margin-bottom:10px;font-size:12px;font-weight:600;color:#7a4d12;
  background:rgba(201,166,107,.2);padding:5px 9px;border-radius:8px;
}
.lens-grid{display:grid;gap:8px 16px;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));margin-bottom:12px}
.decision-box{background:rgba(255,255,255,.55);border:1px solid var(--line);border-radius:14px;padding:14px}
.decision-box p{margin:0 0 10px;font-size:14px;line-height:1.55;color:var(--ink-soft)}
.decision-box .warn{color:var(--danger);font-weight:600;font-size:13px}
.opt{padding:10px 0;border-top:1px dashed var(--line);font-size:13px;color:var(--ink-soft)}
.disclaimer{
  max-width:var(--max);margin:0 auto;padding:12px 20px 8px;font-size:12px;line-height:1.55;color:var(--muted);
  border-top:1px solid var(--line);
}
.provenance{max-width:var(--max);margin:0 auto;padding:0 20px 8px;font-size:11px;color:var(--muted)}
footer.page{max-width:var(--max);margin:0 auto;padding:12px 20px 36px;color:var(--muted);font-size:12px;line-height:1.5}
footer.page a{color:var(--teal-deep)}
.ask-seed{
  background:rgba(255,255,255,.7);border:1px solid var(--line);border-radius:14px;padding:16px;
  font-size:14px;line-height:1.6;color:var(--ink-soft);max-width:62ch;white-space:pre-wrap;
}
.slots{display:grid;gap:12px;margin-top:16px;max-width:62ch}
.slot{
  background:rgba(255,255,255,.72);border:1px solid var(--line);border-radius:14px;padding:14px;
}
.slot h3{margin:0 0 6px;font-family:"Noto Serif KR",serif;font-size:16px;color:var(--teal-deep)}
.slot p{margin:0;font-size:14px;line-height:1.55;color:var(--ink-soft)}
.ask-box{max-width:62ch;margin-top:12px}
.ask-box label{display:block;font-size:12px;font-weight:600;color:var(--muted);margin-bottom:6px}
.ask-box textarea{
  width:100%;min-height:96px;border:1px solid var(--line);border-radius:12px;padding:12px;
  font:400 14px "IBM Plex Sans KR",sans-serif;color:var(--ink);background:#fff;resize:vertical;
}
.ask-box .actions{display:flex;flex-wrap:wrap;gap:8px;margin-top:10px}
.stub-note{font-size:12px;color:var(--muted);margin-top:10px;max-width:62ch;line-height:1.5}
"""


def _esc(s: object) -> str:
    return html.escape(str(s if s is not None else ""), quote=True)


def _md_lite_to_html_v2(text: str) -> str:
    raw = (text or "").replace("\r\n", "\n").strip()
    if not raw:
        return ""

    def boldify(s: str) -> str:
        out: list[str] = []
        pos = 0
        for m in re.finditer(r"\*\*(.+?)\*\*", s):
            out.append(_esc(s[pos : m.start()]))
            out.append(f"<strong>{_esc(m.group(1))}</strong>")
            pos = m.end()
        out.append(_esc(s[pos:]))
        return "".join(out)

    parts: list[str] = []
    lines = raw.split("\n")
    i = 0
    para: list[str] = []

    def flush() -> None:
        nonlocal para
        if para:
            parts.append("<p>" + " ".join(para) + "</p>")
            para = []

    while i < len(lines):
        line = lines[i].rstrip()
        if not line.strip():
            flush()
            i += 1
            continue
        if line.startswith("#### "):
            flush()
            parts.append(
                "<h3 style=\"font-family:'Noto Serif KR',serif;font-size:16px;margin:16px 0 8px\">"
                + boldify(line[5:].strip())
                + "</h3>"
            )
            i += 1
            continue
        if re.match(r"^\d+\.\s+", line):
            flush()
            items: list[str] = []
            while i < len(lines) and re.match(r"^\d+\.\s+", lines[i].rstrip()):
                item = re.sub(r"^\d+\.\s+", "", lines[i].rstrip())
                items.append(f"<li>{boldify(item)}</li>")
                i += 1
            parts.append("<ul>" + "".join(items) + "</ul>")
            continue
        para.append(boldify(line.strip()))
        i += 1
    flush()
    return "\n".join(parts)


def _shell(title: str, description: str, path: str, body: str, *, og: bool = False, nav_current: str = "") -> str:
    og_block = ""
    if og:
        og_block = f"""
<meta property="og:type" content="website" />
<meta property="og:url" content="{SITE_ORIGIN}/" />
<meta property="og:title" content="{_esc(title)}" />
<meta property="og:description" content="{_esc(description)}" />
<meta property="og:locale" content="ko_KR" />
<meta name="twitter:card" content="summary" />
<meta name="twitter:title" content="{_esc(title)}" />
<meta name="twitter:description" content="{_esc(description)}" />
"""
    def nav_attr(key: str) -> str:
        return ' aria-current="page"' if nav_current == key else ""

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>{_esc(title)}</title>
<meta name="description" content="{_esc(description)}" />
<meta name="robots" content="index,follow" />
{og_block}
<link rel="canonical" href="{SITE_ORIGIN}{path}" />
<link rel="preconnect" href="https://fonts.googleapis.com" />
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+KR:wght@400;500;600;700&family=Noto+Serif+KR:wght@500;700&display=swap" rel="stylesheet" />
<link rel="stylesheet" href="/assets/site.css" />
</head>
<body>
<div class="beta"><strong>OPEN_BETA</strong> · 묻다 뉴스 · 교육·참고 전용 · 제품 완료 선언 없음</div>
<header class="top">
  <a class="brand" href="/">묻다.ai</a>
  <nav class="nav" aria-label="주요">
    <a href="/"{nav_attr("home")}>홈</a>
    <a href="/news/"{nav_attr("news")}>뉴스</a>
    <a href="/bible/"{nav_attr("bible")}>성경 묻다</a>
    <a href="/ask/"{nav_attr("ask")}>Ask</a>
    <a href="/about/"{nav_attr("about")}>About</a>
  </nav>
</header>
{body}
<footer class="page">
  <div>주식회사 목소리네트워크</div>
  <div>MKM LAB · secondary / research assist</div>
  <div style="margin-top:6px">OPEN_BETA · PRODUCT_DONE=false · Ask는 <a href="https://jema-ai.com/ask" rel="noopener">jema-ai.com/ask</a>에서 이어갑니다</div>
</footer>
</body>
</html>
"""


def build() -> list[str]:
    ep01 = json.loads(EP01_PATH.read_text(encoding="utf-8"))
    fmt = json.loads(FORMAT_PATH.read_text(encoding="utf-8"))

    title_ko = str(ep01.get("title_ko") or "")
    news_hook = str(ep01.get("news_hook_ko") or "")
    education = str(ep01.get("education_body_ko") or "")
    observe_3 = ep01.get("observe_3") or []
    ask_prompt = str(ep01.get("ask_prompt_ko") or "")
    ask_cta = ep01.get("ask_cta") or {}
    clinic_cta = ep01.get("clinic_cta") or {}
    disclaimer = str(ep01.get("disclaimer_ko") or fmt.get("disclaimer_ko") or "")
    ask_url = str(ask_cta.get("url") or (fmt.get("host_surface") or {}).get("ask_url") or "https://jema-ai.com/ask")
    ask_label = str(ask_cta.get("label_ko") or "한의학 묻다 열기")
    clinic_label = str(clinic_cta.get("label_ko") or "광명백제한의원")
    clinic_url = str(clinic_cta.get("url") or "https://baekje.jema-ai.com/")
    clinic_phone = str(clinic_cta.get("phone") or "02-2688-7700")
    series_title = str(fmt.get("series_title_ko") or "한의학 묻다 시리즈")
    tagline = "사실을 나누고 판단을 돕는 AI"

    # FACT → CAUSE → LENS → DECISION field map (no diagnosis / prescription)
    fact_html = (
        f'<div class="prose"><p>{_esc(news_hook)}</p>'
        f'<p class="meta">news_role={_esc(ep01.get("news_role") or "curated_theme_hook_only")} · 큐레이션 테마 훅만 (포털 피드 아님)</p></div>'
    )
    observe_lis = "".join(f"<li>{_esc(x)}</li>" for x in observe_3)
    cause_html = (
        '<div class="prose">'
        "<p>뉴스·수치를 들었을 때 바로 약 이름이나 체질 단정으로 가지 않도록, "
        "먼저 관찰 축을 정리합니다. (원인 단정·진단 아님)</p>"
        f"<ul>{observe_lis}</ul>"
        f"{_md_lite_to_html_v2(education)}"
        "</div>"
    )
    lens_html = """
<div class="lens-note">Interpretive · empirical evidence 아님 · [NON_GATING]</div>
<p class="purpose">렌즈는 해석·교육용입니다. Final Action·진단·처방으로 쓰이지 않습니다.</p>
<div class="lens-grid">
  <div><strong>사상</strong><br/><span class="meta">[NON_GATING] advisory</span></div>
  <div><strong>명리</strong><br/><span class="meta">[NON_GATING] advisory</span></div>
  <div><strong>성경(Logos)</strong><br/><span class="meta">[NON_GATING] advisory</span></div>
</div>
<p class="meta">Macro/Regime는 렌즈명이 아닙니다. 본 편은 일반 건강 교육 범위입니다.</p>
"""
    decision_html = f"""
<div class="decision-box">
  <p class="warn">금지: 진단·처방·효과 보장·개인 수치 해석을 이 사이트에서 확정하지 않습니다.</p>
  <p>목적에 따라 다음 경로만 안내합니다. 「올바른 의료 의견」 선포는 하지 않습니다.</p>
  <div class="opt"><strong>A · 일반 개념 정리</strong> — {_esc(ask_label)} (<a href="{_esc(ask_url)}" rel="noopener">{_esc(ask_url)}</a>). Ask는 mutda.ai에 호스팅되지 않습니다.</div>
  <div class="opt"><strong>B · 개인 상태·복약·체질</strong> — {_esc(clinic_label)} 대면·전화({_esc(clinic_phone)})·상담 · <a href="{_esc(clinic_url)}" rel="noopener">{_esc(clinic_url)}</a></div>
  <div class="opt"><strong>C · 응급</strong> — 119·응급실</div>
</div>
"""

    written: list[str] = []

    def write(rel: str, content: str) -> None:
        path = OUT_DIR / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8", newline="\n")
        written.append(str(path.relative_to(ROOT)).replace("\\", "/"))

    write("assets/site.css", SHARED_CSS.strip() + "\n")

    # Home
    home_body = f"""
<section class="hero">
  <div>
    <h1>묻다.ai</h1>
    <p class="tagline">{_esc(tagline)}</p>
    <span class="badge">OPEN_BETA</span>
    <p class="sub">{_esc(series_title)} · 사실을 구조로 나누고, 판단은 독자에게 남깁니다.</p>
    <div class="cta-row">
      <a class="btn btn-primary" href="/news/">오늘 뉴스 보기</a>
      <a class="btn btn-ghost" href="/bible/">성경 묻다 — Beta</a>
      <a class="btn btn-ghost" href="/news/ep01/">EP01 열기</a>
    </div>
  </div>
  <aside class="flow">
    <div class="lbl">코어 루프 · EP01</div>
    <div class="step"><b>FACT</b><span>뉴스 테마 훅 (큐레이션)</span></div>
    <div class="step"><b>CAUSE</b><span>관찰 세 가지 · 교육 본문</span></div>
    <div class="step"><b>LENS</b><span>[NON_GATING] · 해석≠증거</span></div>
    <div class="step"><b>DECISION</b><span>Ask / 진찰 / 응급 경로</span></div>
  </aside>
</section>
<section class="today">
  <h2>오늘 묻다</h2>
  <p class="lead">OPEN_BETA · 발행 이슈 1–3건 (현재 EP01)</p>
  <article class="issue-row">
    <h3><a href="/news/ep01/" style="color:inherit;text-decoration:none">{_esc(title_ko)}</a></h3>
    <div class="meta">EP01 · FACT→CAUSE→LENS→DECISION · 교육·참고</div>
    <div class="row-cta">
      <a class="btn btn-ghost" href="/news/ep01/">읽기</a>
      <a class="btn btn-primary" href="{_esc(ask_url)}" rel="noopener">{_esc(ask_label)}</a>
    </div>
  </article>
  <article class="issue-row">
    <h3><a href="/bible/" style="color:inherit;text-decoration:none">성경 묻다 — Beta</a></h3>
    <div class="meta">consumer Beta · 5칸 답변 셸 · logos.jema-ai.com 연구면 KEEP</div>
    <div class="row-cta">
      <a class="btn btn-primary" href="/bible/">성경 묻다 열기</a>
      <a class="btn btn-ghost" href="https://logos.jema-ai.com" rel="noopener">Logos 연구 워크스페이스</a>
    </div>
  </article>
</section>
"""
    write(
        "index.html",
        _shell(
            "묻다.ai — OPEN_BETA",
            tagline,
            "/",
            home_body,
            og=True,
            nav_current="home",
        ),
    )

    # News list
    news_list_body = f"""
<div class="brief-head">
  <div class="eyebrow">OPEN_BETA · NEWS</div>
  <h1>뉴스 목록</h1>
  <p class="lead">큐레이션 테마 훅만 제공합니다. 전체 뉴스 포털이 아닙니다.</p>
</div>
<section class="page">
  <article class="issue-row">
    <h3><a href="/news/ep01/" style="color:inherit;text-decoration:none">{_esc(title_ko)}</a></h3>
    <div class="meta">EP01 · {_esc(ep01.get("episode_id") or "MUTDA_EP01")}</div>
    <p class="sub" style="margin:0">{_esc(news_hook[:160])}{"…" if len(news_hook) > 160 else ""}</p>
    <div class="row-cta"><a class="btn btn-primary" href="/news/ep01/">FACT→CAUSE→LENS→DECISION</a></div>
  </article>
</section>
"""
    write(
        "news/index.html",
        _shell("뉴스 — 묻다.ai OPEN_BETA", "묻다 뉴스 목록", "/news/", news_list_body, nav_current="news"),
    )

    # EP01 detail
    ep_body = f"""
<div class="brief-head">
  <div class="eyebrow">OPEN_BETA · EP01 · MUDDA</div>
  <h1>{_esc(title_ko)}</h1>
  <p class="meta">교육·참고 · 진단·처방 아님</p>
</div>
<div class="layer" id="l-fact">
  <h2>① FACT</h2>
  <p class="purpose">뉴스에서 들은 테마를 훅으로만 둡니다.</p>
  {fact_html}
</div>
<div class="layer" id="l-cause">
  <h2>② CAUSE</h2>
  <p class="purpose">관찰 축·교육 본문 (원인 단정 아님)</p>
  {cause_html}
</div>
<div class="layer" id="l-lens">
  <h2>③ LENS</h2>
  {lens_html}
</div>
<div class="layer" id="l-decision">
  <h2>④ DECISION</h2>
  <p class="purpose">목적 조건부 경로만 · 정답 선포 금지</p>
  {decision_html}
</div>
<div class="disclaimer"><strong>고지</strong> — {_esc(disclaimer)}</div>
<p class="provenance">provenance={_esc(PROVENANCE_EP01)} · format={_esc(PROVENANCE_FORMAT)}</p>
"""
    write(
        "news/ep01/index.html",
        _shell(f"{title_ko} — 묻다.ai", news_hook[:120], "/news/ep01/", ep_body, nav_current="news"),
    )

    # Bible ask Beta — consumer adapter shell (local stub; logos research KEEP)
    bible_body = """
<div class="brief-head">
  <div class="eyebrow">OPEN_BETA · BIBLE</div>
  <h1>성경 묻다 — Beta</h1>
  <p class="lead">소비자 Beta 표면입니다. 완성 제품·연구 워크스페이스 대체가 아닙니다.</p>
  <span class="badge">Beta</span>
</div>
<section class="page">
  <div class="ask-box">
    <label for="bible-q">질문</label>
    <textarea id="bible-q" name="q" maxlength="800" placeholder="예: 시편 23편이 말하는 신뢰는 무엇인가요?"></textarea>
    <div class="actions">
      <button type="button" class="btn btn-primary" id="bible-ask-btn">묻기</button>
      <button type="button" class="btn btn-ghost" id="bible-more-btn" hidden>더 묻기</button>
      <a class="btn btn-ghost" href="https://logos.jema-ai.com" rel="noopener">Logos 연구면</a>
    </div>
    <p class="stub-note">로컬 데모 응답만 표시합니다. 라이브 Logos API·Destiny 배포는 연결하지 않습니다. logos.jema-ai.com은 유지됩니다.</p>
  </div>
  <div class="slots" id="bible-slots" hidden aria-live="polite">
    <article class="slot" data-slot="passage"><h3>본문</h3><p id="slot-passage">—</p></article>
    <article class="slot" data-slot="context"><h3>문맥</h3><p id="slot-context">—</p></article>
    <article class="slot" data-slot="reading"><h3>해석</h3><p id="slot-reading">—</p></article>
    <article class="slot" data-slot="alt"><h3>다른 관점</h3><p id="slot-alt">—</p></article>
    <article class="slot" data-slot="evidence"><h3>근거</h3><p id="slot-evidence">—</p></article>
  </div>
</section>
<script src="/assets/bible_ask_stub_v1.js" defer></script>
"""
    write(
        "bible/index.html",
        _shell(
            "성경 묻다 — Beta · 묻다.ai",
            "성경 묻다 — Beta · 5칸 답변 셸",
            "/bible/",
            bible_body,
            nav_current="bible",
        ),
    )

    bible_stub_js = r"""
(function () {
  var STUB = {
    mode: "local_stub",
    live_api: false,
    logos_keep: "https://logos.jema-ai.com",
    slots: {
      passage: "데모 본문 앵커만 표시합니다. 실제 구절 잠금은 Logos 연구면에서 이어가세요.",
      context: "문맥 슬롯은 로컬 셸용입니다. 역사·문학 문맥 엔진은 여기 라이브 연결되지 않습니다.",
      reading: "해석은 [NON_GATING] 참고용입니다. 단일 교리·완성 선언을 하지 않습니다.",
      alt: "다른 관점 슬롯은 학파·독법을 병기하는 자리입니다. 승자를 고르지 않습니다.",
      evidence: "근거 슬롯은 citation 자리입니다. 현재는 로컬 데모 문구만 채웁니다."
    }
  };
  function fill(q) {
    var qTrim = (q || "").trim();
    document.getElementById("slot-passage").textContent =
      qTrim ? ("질문 반영(데모): " + qTrim.slice(0, 120) + " · " + STUB.slots.passage) : STUB.slots.passage;
    document.getElementById("slot-context").textContent = STUB.slots.context;
    document.getElementById("slot-reading").textContent = STUB.slots.reading;
    document.getElementById("slot-alt").textContent = STUB.slots.alt;
    document.getElementById("slot-evidence").textContent = STUB.slots.evidence;
    document.getElementById("bible-slots").hidden = false;
    document.getElementById("bible-more-btn").hidden = false;
  }
  function onAsk() {
    var ta = document.getElementById("bible-q");
    fill(ta ? ta.value : "");
  }
  function onMore() {
    var ta = document.getElementById("bible-q");
    if (ta) {
      ta.value = (ta.value || "").trim() + (ta.value && ta.value.trim() ? " · " : "") + "이어서: 근거 구절을 더 좁혀 주세요";
      ta.focus();
    }
  }
  document.addEventListener("DOMContentLoaded", function () {
    var ask = document.getElementById("bible-ask-btn");
    var more = document.getElementById("bible-more-btn");
    if (ask) ask.addEventListener("click", onAsk);
    if (more) more.addEventListener("click", onMore);
  });
})();
""".lstrip()
    write("assets/bible_ask_stub_v1.js", bible_stub_js)

    # Ask seed page — does NOT claim Ask lives on mutda
    ask_body = f"""
<div class="brief-head">
  <div class="eyebrow">OPEN_BETA · ASK SEED</div>
  <h1>Ask 시드 프롬프트</h1>
  <p class="lead">Ask 제품은 mutda.ai에 없습니다. 아래 시드를 복사해 jema-ai.com/ask에서 이어가세요.</p>
  <span class="badge">OPEN_BETA</span>
</div>
<section class="page">
  <div class="ask-seed">{_esc(ask_prompt)}</div>
  <div class="cta-row" style="margin-top:16px">
    <a class="btn btn-primary" href="{_esc(ask_url)}" rel="noopener">{_esc(ask_label)}</a>
    <a class="btn btn-ghost" href="/news/ep01/">EP01로 돌아가기</a>
  </div>
  <p class="meta" style="margin-top:14px">ask_prompt_ko · EP01 artifact seed</p>
</section>
"""
    write(
        "ask/index.html",
        _shell("Ask 시드 — 묻다.ai OPEN_BETA", "Ask는 jema-ai.com/ask에서", "/ask/", ask_body, nav_current="ask"),
    )

    # About
    about_body = """
<div class="brief-head">
  <div class="eyebrow">OPEN_BETA · ABOUT</div>
  <h1>주식회사 목소리네트워크</h1>
  <p class="lead">묻다.ai OPEN_BETA 뉴스 표면을 운영합니다.</p>
</div>
<section class="page">
  <div class="prose">
    <p><strong>운영</strong> — 주식회사 목소리네트워크</p>
    <p><strong>MKM LAB</strong> — secondary / footer · research assist (본 사이트 Final Action·제품 완료 선언 없음)</p>
    <p>Ask·클리닉 제품 표면은 각각 jema-ai.com / baekje.jema-ai.com 등 별도 호스트입니다.</p>
  </div>
</section>
"""
    write(
        "about/index.html",
        _shell("About — 묻다.ai", "주식회사 목소리네트워크", "/about/", about_body, nav_current="about"),
    )

    robots = f"""User-agent: *
Allow: /

Sitemap: {SITE_ORIGIN}/sitemap.xml
"""
    write("robots.txt", robots)

    sitemap = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>{SITE_ORIGIN}/</loc></url>
  <url><loc>{SITE_ORIGIN}/news/</loc></url>
  <url><loc>{SITE_ORIGIN}/news/ep01/</loc></url>
  <url><loc>{SITE_ORIGIN}/bible/</loc></url>
  <url><loc>{SITE_ORIGIN}/ask/</loc></url>
  <url><loc>{SITE_ORIGIN}/about/</loc></url>
</urlset>
"""
    write("sitemap.xml", sitemap)

    manifest = {
        "schema": "mutda.news.open_beta.site_build.v1",
        "PRODUCT_DONE": False,
        "FRIEND_READY": False,
        "status": "OPEN_BETA_STATIC_BUILT",
        "surfaces": {
            "/news": "뉴스 묻다 OPEN_BETA",
            "/bible": "성경 묻다 — Beta (local stub adapter)",
        },
        "logos_jema_ai_com_keep": True,
        "sources": {
            "ep01": PROVENANCE_EP01,
            "format": PROVENANCE_FORMAT,
            "mutda_logos_role_pin": "docs/final/artifacts/mkm_mutda_logos_surface_role_pin_v1_latest.json",
        },
        "files": written,
        "tagline_ko": tagline,
        "episode_id": ep01.get("episode_id"),
    }
    write("build_manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    return written


def main() -> int:
    if not EP01_PATH.is_file():
        print(f"FAIL missing EP01: {EP01_PATH}")
        return 2
    if not FORMAT_PATH.is_file():
        print(f"FAIL missing format: {FORMAT_PATH}")
        return 2
    files = build()
    print(f"OK built {len(files)} files under {OUT_DIR.relative_to(ROOT)}")
    for f in files:
        print(f"  {f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
