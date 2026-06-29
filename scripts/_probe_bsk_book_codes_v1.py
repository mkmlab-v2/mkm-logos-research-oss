import re
import urllib.request
from html import unescape

TAG = re.compile(r"<[^>]+>")
CHUNK = re.compile(
    r'<span(?: style="color:#376BCB;")?><span class="number">(\d+)&nbsp;&nbsp;&nbsp;</span>(.*?)</span><br',
    re.S,
)

candidates = [
    ("joh", 1), ("john", 1), ("jn", 1), ("jhn", 1), ("john1", 1),
    ("eze", 1), ("ezk", 1), ("ezek", 1),
    ("mar", 1), ("mk", 1), ("mark", 1), ("mrk", 1),
    ("sos", 1), ("song", 1), ("sol", 1), ("ss", 1),
    ("1jo", 1), ("1jn", 1), ("2jo", 1), ("2jn", 1), ("3jo", 1), ("3jn", 1),
    ("jas", 1), ("jam", 1),
    ("sng", 1), ("son", 1), ("so", 1), ("cant", 1), ("sg", 1),
]
for book, ch in candidates:
    url = f"https://www.bskorea.or.kr/bible/korbibReadpage.php?version=GAE&book={book}&chap={ch}"
    try:
        html = urllib.request.urlopen(url, timeout=30).read().decode("utf-8", "replace")
        m = CHUNK.findall(html)
        first = unescape(TAG.sub("", m[0][1])).strip()[:50] if m else ""
        print(book, "verses", len(m), first)
    except Exception as exc:
        print(book, "ERR", exc)
