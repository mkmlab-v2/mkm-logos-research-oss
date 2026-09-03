#!/usr/bin/env python3
"""Build the MUTDA OPEN_BETA static surface.

Visual Baseline v1 is presentation-only:
- consumer/editorial language on public pages
- internal governance syntax stays out of ordinary UI
- sealed EP01 content remains the source
- no Logos API, deploy, DNS, or authorization changes
"""
from __future__ import annotations

import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EP01_PATH = ROOT / "docs/final/artifacts/mkm_mutda_series_ep01_v1_latest.json"
FORMAT_PATH = ROOT / "docs/final/artifacts/mkm_mutda_series_format_v1_latest.json"
OUT_DIR = ROOT / "projects/mutda-news-open-beta-v1/public"
SITE_ORIGIN = "https://mutda.ai"

CSS = r"""
:root{--paper:#f6f3ed;--paper2:#fbfaf7;--ink:#171918;--soft:#424946;--muted:#777e7a;--line:#d9d6cf;--line2:#c5c0b6;--accent:#0d5d55;--accent2:#e4efec;--max:1040px;--read:720px}
*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:var(--paper);color:var(--ink);font-family:"IBM Plex Sans KR",system-ui,sans-serif;-webkit-font-smoothing:antialiased}a{color:inherit}
.top{max-width:var(--max);margin:auto;min-height:76px;padding:0 24px;display:flex;align-items:center;justify-content:space-between;gap:24px;border-bottom:1px solid var(--line)}
.brand{text-decoration:none;font:700 25px "Noto Serif KR",serif;letter-spacing:-.04em}.nav{display:flex;gap:22px;flex-wrap:wrap}.nav a{text-decoration:none;color:var(--muted);font-size:13px;font-weight:600;padding:8px 0;border-bottom:1px solid transparent}.nav a:hover,.nav a[aria-current="page"]{color:var(--ink);border-color:var(--ink)}
.beta-note{max-width:var(--max);margin:auto;padding:13px 24px 0;color:var(--muted);font-size:12px;line-height:1.6}.beta-note strong,.eyebrow,.kicker{color:var(--accent)}
.hero{max-width:var(--max);margin:auto;padding:88px 24px 52px}.kicker,.eyebrow{font-size:12px;font-weight:700;letter-spacing:.08em}.hero h1{margin:16px 0 0;max-width:780px;font:700 clamp(38px,7vw,72px)/1.12 "Noto Serif KR",serif;letter-spacing:-.055em}.hero .sub{margin:22px 0 0;max-width:610px;color:var(--soft);font-size:17px;line-height:1.8}
.surface-grid{max-width:var(--max);margin:auto;padding:0 24px 72px;display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px}.surface-card{min-height:230px;padding:28px;border:1px solid var(--line2);border-radius:18px;background:var(--paper2);text-decoration:none;display:flex;flex-direction:column;justify-content:space-between;transition:.16s}.surface-card:hover{transform:translateY(-2px);border-color:#aaa69d;background:#fff}.surface-card .type{font-size:12px;color:var(--accent);font-weight:700;letter-spacing:.06em}.surface-card h2{margin:34px 0 8px;font:700 28px "Noto Serif KR",serif;letter-spacing:-.035em}.surface-card p{margin:0;color:var(--soft);font-size:14px;line-height:1.7;max-width:35ch}.arrow{margin-top:22px;color:var(--accent);font-size:13px;font-weight:700}.coming{max-width:var(--max);margin:-44px auto 72px;padding:0 24px;color:var(--muted);font-size:12px}
.brief-head{max-width:var(--max);margin:auto;padding:72px 24px 28px}.brief-head h1{margin:13px 0 0;max-width:820px;font:700 clamp(32px,5vw,50px)/1.25 "Noto Serif KR",serif;letter-spacing:-.045em}.lead{max-width:660px;margin:16px 0 0;color:var(--soft);font-size:15px;line-height:1.75}.page{max-width:var(--max);margin:auto;padding:0 24px 72px}
.issue-list{border-top:1px solid var(--line2)}.issue-row{padding:26px 0;border-bottom:1px solid var(--line);display:grid;grid-template-columns:92px minmax(0,1fr) auto;gap:22px}.issue-id{font-size:12px;color:var(--muted);padding-top:5px}.issue-main h2{margin:0;font:600 22px/1.45 "Noto Serif KR",serif;letter-spacing:-.025em}.issue-main h2 a{text-decoration:none}.issue-main p{margin:9px 0 0;color:var(--soft);font-size:14px;line-height:1.7}.link-action{text-decoration:none;color:var(--accent);font-size:13px;font-weight:700;white-space:nowrap;padding-top:4px}
.article{max-width:var(--read);margin:auto;padding:6px 24px 72px}.section{padding:34px 0;border-top:1px solid var(--line)}.section:first-child{border-color:var(--line2)}.section .num{font-size:12px;color:var(--accent);font-weight:700;letter-spacing:.06em}.section h2{margin:8px 0 10px;font:700 27px "Noto Serif KR",serif;letter-spacing:-.035em}.purpose{margin:0 0 20px;color:var(--muted);font-size:13px;line-height:1.65}.prose{color:var(--soft);font-size:16px;line-height:1.9}.prose p{margin:0 0 18px}.prose ul{margin:0 0 18px;padding-left:1.25em}.prose li{margin:6px 0}.prose h3{margin:22px 0 10px;font:600 19px/1.5 "Noto Serif KR",serif;color:var(--ink)}.view-note{margin:18px 0 0;padding:15px 16px;border-left:3px solid var(--accent);background:var(--accent2);color:var(--soft);font-size:14px;line-height:1.75}
.decision-list{border-top:1px solid var(--line)}.decision-item{padding:17px 0;border-bottom:1px solid var(--line);font-size:14px;line-height:1.7;color:var(--soft)}.decision-item strong{display:block;color:var(--ink);margin-bottom:3px}.actions{display:flex;gap:10px;flex-wrap:wrap;margin-top:24px}.btn{min-height:46px;padding:0 17px;border-radius:12px;border:1px solid var(--line2);background:transparent;color:var(--ink);text-decoration:none;font:600 13px "IBM Plex Sans KR",sans-serif;display:inline-flex;align-items:center;justify-content:center;cursor:pointer}.btn-primary{background:var(--ink);border-color:var(--ink);color:#fff}.btn-accent{background:var(--accent);border-color:var(--accent);color:#fff}
.trust{max-width:var(--read);margin:0 auto 34px;padding:0 24px;color:var(--muted);font-size:12px;line-height:1.7}.ask-card{max-width:var(--read);padding:24px;border:1px solid var(--line2);border-radius:18px;background:var(--paper2)}.ask-card p{margin:0;color:var(--soft);font-size:14px;line-height:1.75}.ask-prompt{margin-top:18px;padding:18px 0;border-top:1px solid var(--line);border-bottom:1px solid var(--line);font-size:15px;line-height:1.8;white-space:pre-wrap}
.ask-box{max-width:var(--read)}.ask-box label{display:block;font-size:12px;font-weight:700;color:var(--muted);margin-bottom:8px}.ask-box textarea{width:100%;min-height:118px;padding:15px 16px;border:1px solid var(--line2);border-radius:14px;background:var(--paper2);color:var(--ink);resize:vertical;font:400 15px/1.7 "IBM Plex Sans KR",sans-serif}.preview-note{margin:12px 0 0;color:var(--muted);font-size:12px;line-height:1.65}.slots{max-width:var(--read);margin-top:30px;border-top:1px solid var(--line2)}.slot{padding:24px 0;border-bottom:1px solid var(--line)}.slot h3{margin:0 0 8px;font:600 20px "Noto Serif KR",serif}.slot p{margin:0;color:var(--soft);font-size:14px;line-height:1.8}
.about{max-width:var(--read);display:grid;gap:28px}.about-block{padding-top:22px;border-top:1px solid var(--line)}.about-block h2{margin:0 0 8px;font:600 20px "Noto Serif KR",serif}.about-block p{margin:0;color:var(--soft);font-size:14px;line-height:1.8}.footer{max-width:var(--max);margin:auto;padding:30px 24px 48px;border-top:1px solid var(--line);display:flex;justify-content:space-between;gap:20px;flex-wrap:wrap;color:var(--muted);font-size:12px;line-height:1.6}.footer a{text-decoration:none}
@media(max-width:760px){.top{min-height:auto;padding-top:20px;padding-bottom:18px;align-items:flex-start;flex-direction:column;gap:13px}.nav{gap:16px}.hero{padding-top:62px;padding-bottom:38px}.hero h1{font-size:44px}.surface-grid{grid-template-columns:1fr}.surface-card{min-height:190px;padding:24px}.brief-head{padding-top:54px}.issue-row{grid-template-columns:1fr;gap:9px}.issue-id,.link-action{padding-top:0}}
@media(max-width:420px){.top,.beta-note,.hero,.surface-grid,.coming,.brief-head,.page,.article,.trust,.footer{padding-left:18px;padding-right:18px}.hero{padding-top:48px}.hero h1{font-size:39px}.surface-card h2{font-size:25px}.brief-head h1{font-size:34px}}
"""


def esc(value: object) -> str:
    return html.escape(str(value if value is not None else ""), quote=True)


def public_text(value: object) -> str:
    return str(value if value is not None else "").replace("怖い", "걱정되는")


def inline_markdown(text: str) -> str:
    """Render only **bold**; escape every other inline token."""
    parts = public_text(text).split("**")
    rendered: list[str] = []
    for i, part in enumerate(parts):
        value = esc(part)
        rendered.append(f"<strong>{value}</strong>" if i % 2 else value)
    return "".join(rendered)


def rich_text(text: str) -> str:
    """Render the small Markdown subset used by the sealed EP01 body.

    This intentionally supports only headings, simple lists, paragraphs and
    bold spans so authoring syntax cannot leak literally into the public page.
    """
    lines = public_text(text).replace("\r\n", "\n").split("\n")
    out: list[str] = []
    para: list[str] = []
    i = 0

    def flush_para() -> None:
        nonlocal para
        if para:
            out.append("<p>" + " ".join(inline_markdown(x.strip()) for x in para) + "</p>")
            para = []

    while i < len(lines):
        stripped = lines[i].strip()
        if not stripped:
            flush_para()
            i += 1
            continue

        if stripped.startswith("#### ") or stripped.startswith("### "):
            flush_para()
            label = stripped.lstrip("#").strip()
            out.append(f"<h3>{inline_markdown(label)}</h3>")
            i += 1
            continue

        if stripped.startswith(("- ", "* ", "+ ")):
            flush_para()
            items: list[str] = []
            while i < len(lines):
                candidate = lines[i].strip()
                if not candidate.startswith(("- ", "* ", "+ ")):
                    break
                items.append(f"<li>{inline_markdown(candidate[2:].strip())}</li>")
                i += 1
            out.append("<ul>" + "".join(items) + "</ul>")
            continue

        ordered_prefix = stripped.split(". ", 1)
        if len(ordered_prefix) == 2 and ordered_prefix[0].isdigit():
            flush_para()
            items = []
            while i < len(lines):
                candidate = lines[i].strip()
                prefix = candidate.split(". ", 1)
                if len(prefix) != 2 or not prefix[0].isdigit():
                    break
                items.append(f"<li>{inline_markdown(prefix[1].strip())}</li>")
                i += 1
            out.append("<ul>" + "".join(items) + "</ul>")
            continue

        para.append(stripped)
        i += 1

    flush_para()
    return "".join(out)


def shell(title: str, description: str, path: str, body: str, current: str = "", og: bool = False) -> str:
    def aria(key: str) -> str:
        return ' aria-current="page"' if current == key else ""

    og_html = ""
    if og:
        og_html = f"""
<meta property="og:type" content="website" />
<meta property="og:url" content="{SITE_ORIGIN}{path}" />
<meta property="og:title" content="{esc(title)}" />
<meta property="og:description" content="{esc(description)}" />
<meta property="og:locale" content="ko_KR" />
<meta name="twitter:card" content="summary" />
"""
    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>{esc(title)}</title>
<meta name="description" content="{esc(description)}" />
<meta name="robots" content="index,follow" />
{og_html}<link rel="canonical" href="{SITE_ORIGIN}{path}" />
<link rel="preconnect" href="https://fonts.googleapis.com" />
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+KR:wght@400;500;600;700&family=Noto+Serif+KR:wght@500;600;700&display=swap" rel="stylesheet" />
<link rel="stylesheet" href="/assets/site.css" />
</head>
<body>
<header class="top"><a class="brand" href="/">묻다</a><nav class="nav" aria-label="주요"><a href="/news/"{aria("news")}>뉴스 묻다</a><a href="/bible/"{aria("bible")}>성경 묻다 · Beta</a><a href="/about/"{aria("about")}>소개</a></nav></header>
<div class="beta-note"><strong>Beta</strong> · 사실과 해석을 구분하고, 근거와 한계를 함께 표시합니다.</div>
{body}
<footer class="footer"><div>주식회사 목소리네트워크</div><div><a href="/about/">묻다 소개</a> · <a href="/news/">뉴스</a> · <a href="/bible/">성경 Beta</a></div></footer>
</body>
</html>
"""


def build() -> list[str]:
    ep01 = json.loads(EP01_PATH.read_text(encoding="utf-8"))
    fmt = json.loads(FORMAT_PATH.read_text(encoding="utf-8"))

    title = public_text(ep01.get("title_ko"))
    hook = public_text(ep01.get("news_hook_ko"))
    education = public_text(ep01.get("education_body_ko"))
    observations = [public_text(x) for x in (ep01.get("observe_3") or [])]
    ask_prompt = public_text(ep01.get("ask_prompt_ko"))
    disclaimer = public_text(ep01.get("disclaimer_ko") or fmt.get("disclaimer_ko") or "")
    ask_cta = ep01.get("ask_cta") or {}
    clinic_cta = ep01.get("clinic_cta") or {}
    ask_url = str(ask_cta.get("url") or (fmt.get("host_surface") or {}).get("ask_url") or "https://jema-ai.com/ask")
    ask_label = public_text(ask_cta.get("label_ko") or "이 질문 이어가기")
    clinic_label = public_text(clinic_cta.get("label_ko") or "전문가와 상담하기")
    clinic_url = str(clinic_cta.get("url") or "https://baekje.jema-ai.com/")
    clinic_phone = str(clinic_cta.get("phone") or "02-2688-7700")

    written: list[str] = []

    def write(rel: str, content: str) -> None:
        path = OUT_DIR / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8", newline="\n")
        written.append(path.relative_to(ROOT).as_posix())

    write("assets/site.css", CSS.strip() + "\n")

    home = """
<section class="hero"><div class="kicker">MUTDA · OPEN BETA</div><h1>무엇을 묻고 싶으세요?</h1><p class="sub">묻다는 답을 서두르기보다, 사실과 맥락을 먼저 정리합니다. 질문의 종류에 맞는 공간에서 시작하세요.</p></section>
<section class="surface-grid" aria-label="묻다 서비스">
<a class="surface-card" href="/news/"><div class="type">NEWS</div><div><h2>뉴스 묻다</h2><p>지금 벌어진 일을 사실부터 정리하고, 왜 그런지와 다른 관점을 차례로 봅니다.</p></div><div class="arrow">뉴스에서 시작하기 →</div></a>
<a class="surface-card" href="/bible/"><div class="type">BIBLE · BETA</div><div><h2>성경 묻다</h2><p>본문과 문맥에서 질문을 시작하고, 해석과 다른 관점, 근거를 나누어 봅니다.</p></div><div class="arrow">성경에서 시작하기 →</div></a>
</section><div class="coming">시장 묻다 · 연구 묻다는 준비 중입니다.</div>
"""
    write("index.html", shell("묻다 — 질문에서 시작합니다", "뉴스와 성경을 사실·문맥·근거로 나누어 묻습니다.", "/", home, og=True))

    news = f"""
<div class="brief-head"><div class="eyebrow">NEWS MUTDA</div><h1>뉴스를 읽기 전에,<br/>먼저 무엇이 사실인지 묻습니다.</h1><p class="lead">많은 이슈를 늘어놓기보다 지금 확인할 질문을 하나씩 다룹니다.</p></div>
<section class="page"><div class="issue-list"><article class="issue-row"><div class="issue-id">EP01</div><div class="issue-main"><h2><a href="/news/ep01/">{esc(title)}</a></h2><p>{esc(hook[:180])}{'…' if len(hook)>180 else ''}</p></div><a class="link-action" href="/news/ep01/">읽기 →</a></article></div></section>
"""
    write("news/index.html", shell("뉴스 묻다 — 묻다", "뉴스를 사실, 맥락, 다른 관점, 다음 확인점으로 나눕니다.", "/news/", news, current="news"))

    observation_items = "".join(f"<li>{esc(x)}</li>" for x in observations)
    fact = f'<div class="prose"><p>{esc(hook)}</p></div>'
    why = f'<div class="prose"><p>뉴스에서 수치나 건강 이야기를 들었을 때 바로 결론부터 내리지 않고, 먼저 무엇을 관찰해야 하는지 정리합니다.</p><ul>{observation_items}</ul>{rich_text(education)}</div>'
    perspective = '<div class="prose"><p>같은 사실도 질문의 목적과 맥락에 따라 다르게 읽힐 수 있습니다. 여기서는 한 관점을 정답으로 고정하지 않습니다.</p><div class="view-note">해석은 사실과 구분해서 읽으세요. 개인의 증상·검사값·복약 판단에는 별도의 전문 평가가 필요할 수 있습니다.</div></div>'
    next_step = f'<div class="decision-list"><div class="decision-item"><strong>개념을 더 묻고 싶다면</strong>일반 질문은 Ask에서 이어갈 수 있습니다.</div><div class="decision-item"><strong>내 증상·검사값·복약과 연결된다면</strong>{esc(clinic_label)} 또는 적절한 의료전문가와 상담하세요. {esc(clinic_phone)}</div><div class="decision-item"><strong>응급 증상이 있다면</strong>온라인 답변보다 119 또는 응급의료기관을 우선하세요.</div></div><div class="actions"><a class="btn btn-accent" href="/ask/">이 뉴스 더 묻기</a><a class="btn" href="{esc(clinic_url)}" rel="noopener">상담 경로 보기</a></div>'

    episode = f"""
<div class="brief-head"><div class="eyebrow">NEWS · EP01</div><h1>{esc(title)}</h1><p class="lead">사실과 해석을 섞지 않고, 다음에 무엇을 확인할지까지 차례로 봅니다.</p></div>
<main class="article">
<section class="section"><div class="num">01</div><h2>사실</h2><p class="purpose">무슨 이야기가 나왔나</p>{fact}</section>
<section class="section"><div class="num">02</div><h2>왜</h2><p class="purpose">어떤 맥락에서 봐야 하나</p>{why}</section>
<section class="section"><div class="num">03</div><h2>다른 관점</h2><p class="purpose">다르게 읽을 수 있는 지점</p>{perspective}</section>
<section class="section"><div class="num">04</div><h2>그래서 무엇을 볼까</h2><p class="purpose">지금 결론보다 다음 확인점</p>{next_step}</section>
</main><div class="trust"><strong>안내</strong> · {esc(disclaimer)}</div>
"""
    write("news/ep01/index.html", shell(f"{title} — 뉴스 묻다", hook[:120], "/news/ep01/", episode, current="news", og=True))

    bible = """
<div class="brief-head"><div class="eyebrow">BIBLE MUTDA · BETA</div><h1>성경 묻다</h1><p class="lead">본문을 먼저 붙잡고, 문맥과 해석을 나눈 뒤 다른 관점과 근거를 확인하는 Beta입니다.</p></div>
<section class="page"><div class="ask-box"><label for="bible-q">성경에 대해 무엇이 궁금한가요?</label><textarea id="bible-q" maxlength="800" placeholder="예: 시편 23편이 말하는 신뢰는 무엇인가요?"></textarea><div class="actions"><button class="btn btn-primary" type="button" id="bible-ask-btn">미리보기</button><button class="btn" type="button" id="bible-more-btn" hidden>더 묻기</button></div><p class="preview-note">현재는 답변 구조를 확인하는 Beta 미리보기입니다. Logos 연구엔진의 라이브 답변 연결은 아직 공개하지 않습니다.</p></div>
<div class="slots" id="bible-slots" hidden aria-live="polite"><article class="slot"><h3>본문</h3><p id="slot-passage">—</p></article><article class="slot"><h3>문맥</h3><p id="slot-context">—</p></article><article class="slot"><h3>해석</h3><p id="slot-reading">—</p></article><article class="slot"><h3>다른 관점</h3><p id="slot-alt">—</p></article><article class="slot"><h3>근거</h3><p id="slot-evidence">—</p></article></div></section><script src="/assets/bible_ask_stub_v1.js" defer></script>
"""
    write("bible/index.html", shell("성경 묻다 — Beta", "본문 · 문맥 · 해석 · 다른 관점 · 근거", "/bible/", bible, current="bible"))

    bible_js = r'''(function(){var c={passage:"현재는 화면 구조 미리보기입니다. 실제 본문 잠금과 구절 인용은 라이브 연결 전까지 제공하지 않습니다.",context:"문학적·역사적 문맥을 확인하는 자리입니다.",reading:"해석은 본문과 구분해 제시하고, 한 독법을 자동으로 정답 처리하지 않습니다.",alt:"주요한 다른 독법이 있을 때 함께 보여주는 자리입니다.",evidence:"근거 구절과 출처를 표시하는 자리입니다. 현재 미리보기에서는 실제 citation을 생성하지 않습니다."};function fill(q){var t=(q||"").trim();document.getElementById("slot-passage").textContent=(t?("질문: "+t.slice(0,120)+" · "):"")+c.passage;document.getElementById("slot-context").textContent=c.context;document.getElementById("slot-reading").textContent=c.reading;document.getElementById("slot-alt").textContent=c.alt;document.getElementById("slot-evidence").textContent=c.evidence;document.getElementById("bible-slots").hidden=false;document.getElementById("bible-more-btn").hidden=false}document.addEventListener("DOMContentLoaded",function(){var a=document.getElementById("bible-ask-btn"),m=document.getElementById("bible-more-btn"),t=document.getElementById("bible-q");if(a)a.addEventListener("click",function(){fill(t?t.value:"")});if(m)m.addEventListener("click",function(){if(t)t.focus()})})})();'''
    write("assets/bible_ask_stub_v1.js", bible_js + "\n")

    ask = f"""
<div class="brief-head"><div class="eyebrow">ASK</div><h1>이 질문을 조금 더 이어가 볼까요?</h1><p class="lead">묻다 뉴스에서 시작한 질문을 Ask에서 더 좁혀볼 수 있습니다.</p></div>
<section class="page"><div class="ask-card"><p>EP01에서 이어지는 질문</p><div class="ask-prompt">{esc(ask_prompt)}</div><div class="actions"><a class="btn btn-accent" href="{esc(ask_url)}" rel="noopener">{esc(ask_label)}</a><a class="btn" href="/news/ep01/">뉴스로 돌아가기</a></div></div></section>
"""
    write("ask/index.html", shell("더 묻기 — 묻다", "뉴스에서 시작한 질문을 이어갑니다.", "/ask/", ask))

    about = """
<div class="brief-head"><div class="eyebrow">ABOUT MUTDA</div><h1>묻다는 질문의 속도를 조금 늦춥니다.</h1><p class="lead">먼저 사실을 나누고, 맥락과 해석을 구분한 뒤, 무엇을 더 확인해야 하는지 보여주려는 작은 Beta입니다.</p></div>
<section class="page"><div class="about"><div class="about-block"><h2>운영</h2><p>주식회사 목소리네트워크가 운영합니다.</p></div><div class="about-block"><h2>MKM LAB</h2><p>묻다의 연구·개발을 지원합니다. 연구용 작업공간과 소비자용 화면은 역할을 나누어 운영합니다.</p></div><div class="about-block"><h2>Beta 원칙</h2><p>과장된 완성 선언보다 근거와 한계를 함께 표시합니다. 뉴스와 AI 답변은 중요한 판단을 대신하지 않습니다.</p></div></div></section>
"""
    write("about/index.html", shell("소개 — 묻다", "묻다와 운영 원칙을 소개합니다.", "/about/", about, current="about"))

    write("robots.txt", f"User-agent: *\nAllow: /\n\nSitemap: {SITE_ORIGIN}/sitemap.xml\n")
    write("sitemap.xml", f'''<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><url><loc>{SITE_ORIGIN}/</loc></url><url><loc>{SITE_ORIGIN}/news/</loc></url><url><loc>{SITE_ORIGIN}/news/ep01/</loc></url><url><loc>{SITE_ORIGIN}/bible/</loc></url><url><loc>{SITE_ORIGIN}/ask/</loc></url><url><loc>{SITE_ORIGIN}/about/</loc></url></urlset>\n''')

    manifest = {"schema":"mutda.news.open_beta.site_build.v1","visual_baseline":"MUTDA_DESIGN_SSOT_V1","status":"OPEN_BETA_STATIC_BUILT","PRODUCT_DONE":False,"FRIEND_READY":False,"logos_research_workspace_keep":True,"source_ids":["MUTDA_EP01_SEALED","MUTDA_SERIES_FORMAT_SEALED"],"files":written,"episode_id":ep01.get("episode_id")}
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
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
