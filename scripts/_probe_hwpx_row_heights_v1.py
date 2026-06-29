#!/usr/bin/env python3
import re
import sys
import zipfile
from pathlib import Path

p = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(r"C:\workspace\reports\opendata_327_official_filled_v4_g5.hwpx")
s = zipfile.ZipFile(p).read("Contents/section0.xml").decode("utf-8", errors="replace")
heights = re.findall(r'height="(\d+)"', s)
print("unique heights (hwpx units):", sorted({int(h) for h in heights})[:30])
print("tbl tags:", s.count("<hp:tbl"))
# sample rowSz / cellSz
for pat in ("rowAddr", "cellSz", "cellSpan", "vertAlign"):
    print(pat, s.count(pat))
