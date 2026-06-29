#!/usr/bin/env python3
import re
from pathlib import Path
from zipfile import ZipFile

p = Path("reports/kstartup_startup_package_ai_filled/doyak_plan_filled_v5.docx")
xml = ZipFile(p).read("word/document.xml").decode("utf-8")
for m in re.finditer("개발하고자", xml):
    chunk = xml[max(0, m.start() - 600) : m.end() + 120]
    colors = re.findall(r'w:color w:val="([^"]+)"', chunk)
    themes = re.findall(r'w:themeColor w:val="([^"]+)"', chunk)
    texts = [t for t in re.findall(r"<w:t[^>]*>([^<]*)</w:t>", chunk) if t.strip()]
    print("---")
    print("colors", colors[-4:])
    print("themes", themes[-4:])
    print("texts", texts[-5:])
