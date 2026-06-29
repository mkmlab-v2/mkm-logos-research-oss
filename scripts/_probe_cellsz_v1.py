#!/usr/bin/env python3
import re, zipfile, sys
from pathlib import Path
p = Path(sys.argv[1])
s = zipfile.ZipFile(p).read("Contents/section0.xml").decode("utf-8", errors="replace")
# sample tc with cellSz
for m in re.finditer(r"<hp:tc[^>]*>[\s\S]{0,800}?</hp:tc>", s):
    block = m.group(0)
    if "※" in block or len(block) > 600:
        continue
    t = re.findall(r"<hp:t>([^<]*)</hp:t>", block)
    sz = re.search(r'cellSz[^>]*height="(\d+)"', block) or re.search(r'height="(\d+)"', block)
    if t and sz:
        print("text:", "".join(t)[:60], "height:", sz.group(1))
        break
# count cellSz heights > 2000
big = len(re.findall(r'height="([3-9]\d{3}|\d{5,})"', s))
print("large heights count:", big)
