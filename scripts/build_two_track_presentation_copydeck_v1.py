#!/usr/bin/env python3
from __future__ import annotations
import argparse, json
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
def now(): return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
def load(p):
    o=json.loads(p.read_text(encoding='utf-8'))
    return o if isinstance(o,dict) else {}
def card_value(cards, card_id, default=None):
    for c in cards:
        if isinstance(c, dict) and c.get('id') == card_id:
            return c.get('value')
    return default
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--presentation-brief-json', required=True); ap.add_argument('--output-json', required=True); a=ap.parse_args()
    ip,op=Path(a.presentation_brief_json),Path(a.output_json)
    if not ip.is_absolute(): ip=ROOT/ip
    if not op.is_absolute(): op=ROOT/op
    b=load(ip)
    cards=list(b.get('priority_cards') or [])
    top_symbol=card_value(cards,'top_symbol_by_coupling','n/a')
    top2=card_value(cards,'top2_symbols',[])
    ab_delta=card_value(cards,'gematria_4d_delta_with_minus_without','n/a')
    out={'schema':'two_track_presentation_copydeck_v1','generated_at_utc':now(),'research_only':True,'promotion_required':True,'source_track':'K',
         'one_page':{'title':b.get('headline','Two-track'),
                     'key_points':['K-track for knowledge IP','T-track for survivorship gating','Public-safe disclosure boundary',
                                   f'Top symbol by coupling: {top_symbol}',
                                   f'4D ablation delta (with-without): {ab_delta}']},
         'three_page':[{'section':'Problem','bullets':['Narrative-rich signals can overfit when directly promoted']},
                       {'section':'Method','bullets':['Two-track split','Falsification + benchmark + significance',
                                                     f'Multi-symbol top2: {top2}']},
                       {'section':'Governance','bullets':['Rollback contract','Public-safe redaction',
                                                         'Symbolic layer is analysis-only (non-trigger)']}]}
    op.parent.mkdir(parents=True, exist_ok=True); op.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n', encoding='utf-8'); print(str(op)); return 0
if __name__=='__main__': raise SystemExit(main())
