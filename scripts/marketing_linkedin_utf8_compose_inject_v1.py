#!/usr/bin/env python3
"""Generate CDP Runtime.evaluate JS for LinkedIn compose — UTF-8 safe via paste event."""
from __future__ import annotations

import argparse
import base64
import json
import sys
from pathlib import Path


def build_paste_inject_js(text: str, *, submit: bool = True) -> str:
    """Build JS that injects plain text via ClipboardEvent paste (Quill-safe UTF-8)."""
    b64 = base64.b64encode(text.encode("utf-8")).decode("ascii")
    submit_block = ""
    if submit:
        submit_block = """
  const pub = [...document.querySelectorAll('button')].find(
    b => (b.innerText || '').trim() === '업데이트' && (b.className || '').includes('share-actions') && !b.disabled
  );
  if (pub) { pub.click(); return 'submitted'; }
  return 'filled';
"""
    else:
        submit_block = "  return 'filled';"

    return f"""(() => {{
  const text = new TextDecoder('utf-8').decode(Uint8Array.from(atob('{b64}'), c => c.charCodeAt(0)));
  const ed = document.querySelector('.share-creation-state .ql-editor') || document.querySelector('.share-box .ql-editor');
  if (!ed) return 'no-editor';
  ed.focus();
  ed.innerHTML = '';
  const dt = new DataTransfer();
  dt.setData('text/plain', text);
  const ev = new ClipboardEvent('paste', {{ bubbles: true, cancelable: true, clipboardData: dt }});
  ed.dispatchEvent(ev);
  if (!ed.innerText.trim()) {{
    ed.textContent = text;
    ed.dispatchEvent(new InputEvent('input', {{ bubbles: true, inputType: 'insertFromPaste' }}));
  }}
{submit_block}
}})()"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--text-file", type=Path, help="UTF-8 file with post body")
    parser.add_argument("--text", help="Post body inline")
    parser.add_argument("--json-batch", type=Path, help="ip_safe_batch_publish_today_v1.json path")
    parser.add_argument("--item-id", help="Item id when using --json-batch")
    parser.add_argument("--no-submit", action="store_true")
    parser.add_argument("--out", type=Path, default=Path("reports/marketing/_linkedin_utf8_inject_latest.js"))
    args = parser.parse_args()

    if args.json_batch and args.item_id:
        batch = json.loads(args.json_batch.read_text(encoding="utf-8"))
        row = next((r for r in batch if r["id"] == args.item_id), None)
        if not row:
            print(f"item not found: {args.item_id}", file=sys.stderr)
            return 1
        text = row["post"]
    elif args.text_file:
        text = args.text_file.read_text(encoding="utf-8")
    elif args.text:
        text = args.text
    else:
        parser.error("provide --text, --text-file, or --json-batch + --item-id")

    js = build_paste_inject_js(text, submit=not args.no_submit)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(js, encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(args.out), "chars": len(text)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
