#!/usr/bin/env python3
import re, sys, zipfile
from pathlib import Path

p = Path(sys.argv[1])
s = zipfile.ZipFile(p).read("Contents/section0.xml").decode("utf-8", errors="replace")
count = 0
for m in re.finditer(r"<hp:tc[^>]*>[\s\S]*?</hp:tc>", s):
    b = m.group(0)
    t = "".join(re.findall(r"<hp:t>([^<]*)</hp:t>", b))
    t = re.sub(r"\s+", " ", t).strip()
    hm = re.search(r'cellSz[^>]*height="(\d+)"', b)
    if not hm:
        continue
    h = int(hm.group(1))
    if h > 2500 and len(t) < 100:
        print(f"h={h} len={len(t)} text={t[:70]!r}")
        count += 1
        if count >= 20:
            break
print("total tall+short (sample cap 20 shown):", count)
