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
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--fusion-report-json', required=True); ap.add_argument('--output-json', required=True)
    ap.add_argument('--multi-symbol-json', default='docs/final/artifacts/multi_symbol_resonance_4d_latest.json')
    ap.add_argument('--multi-symbol-selector-json', default='docs/final/artifacts/multi_symbol_candidate_selector_latest.json')
    ap.add_argument('--gematria-ablation-json', default='docs/final/artifacts/gematria_4d_ablation_latest.json')
    a=ap.parse_args()
    fp,op=Path(a.fusion_report_json),Path(a.output_json)
    mp=Path(a.multi_symbol_json); sp=Path(a.multi_symbol_selector_json); gp=Path(a.gematria_ablation_json)
    if not fp.is_absolute(): fp=ROOT/fp
    if not op.is_absolute(): op=ROOT/op
    if not mp.is_absolute(): mp=ROOT/mp
    if not sp.is_absolute(): sp=ROOT/sp
    if not gp.is_absolute(): gp=ROOT/gp
    f=load(fp)
    m=load(mp) if mp.is_file() else {}
    s=load(sp) if sp.is_file() else {}
    g=load(gp) if gp.is_file() else {}
    k=((f.get('tracks') or {}).get('K') or {})
    t=((f.get('tracks') or {}).get('T') or {})
    selected=list(s.get('selected') or []) if isinstance(s.get('selected'),list) else []
    top1=selected[0] if selected else {}
    top2=selected[1] if len(selected)>1 else {}
    ms_summary=(m.get('summary') or {}) if isinstance(m.get('summary'),dict) else {}
    ab_snapshot=(g.get('snapshot') or {}) if isinstance(g.get('snapshot'),dict) else {}
    out={'schema':'two_track_fusion_brief_v1','generated_at_utc':now(),'research_only':True,'promotion_required':True,'source_track':'K','headline':'Two-track fusion status',
         'cards':[{'id':'k_summary','value':k.get('summary',{})},
                  {'id':'shift_score','value':t.get('shift_score',0.0)},
                  {'id':'survivor_count','value':t.get('survivor_count',0)},
                  {'id':'top_symbol_by_coupling','value':ms_summary.get('top_symbol_by_coupling')},
                  {'id':'top2_symbols','value':[top1.get('seed_symbol'), top2.get('seed_symbol')]},
                  {'id':'gematria_4d_delta_with_minus_without','value':ab_snapshot.get('delta_with_minus_without')}],
         'storylines':['K-track narrative is isolated from trade trigger',
                       'T-track applies survivor filter and rollback gates',
                       'Multi-symbol ranking highlights top symbolic hubs for explanation quality',
                       '4D gematria ablation delta quantifies incremental structure, non-trigger only'],
         'guardrail':'not_for_direct_trading_signal',
         'sources':{'multi_symbol_json':str(mp) if mp.is_file() else None,'multi_symbol_selector_json':str(sp) if sp.is_file() else None,'gematria_ablation_json':str(gp) if gp.is_file() else None}}
    op.parent.mkdir(parents=True, exist_ok=True); op.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n', encoding='utf-8'); print(str(op)); return 0
if __name__=='__main__': raise SystemExit(main())
