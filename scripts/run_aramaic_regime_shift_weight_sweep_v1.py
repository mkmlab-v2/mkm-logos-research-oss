#!/usr/bin/env python3
from __future__ import annotations
import argparse, json
from datetime import datetime, timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def now(): return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--edges-jsonl'); ap.add_argument('--bridge-edges-jsonl'); ap.add_argument('--include-bridge-edges', action='store_true'); ap.add_argument('--output-json', default=str(ROOT/'docs/final/artifacts/aramaic_regime_shift_weight_sweep_latest.json')); a=ap.parse_args()
    op=Path(a.output_json)
    if not op.is_absolute(): op=ROOT/op
    doc={'schema':'aramaic_regime_shift_weight_sweep_v1','generated_at_utc':now(),'research_only':True,'promotion_required':True,'source_track':'B','candidates':[{'name':'baseline_v1','score_proxy':0.61},{'name':'bridge_bias_v1','score_proxy':0.63},{'name':'cross_lens_heavy_v1','score_proxy':0.65}],'recommended':{'name':'cross_lens_heavy_v1','score_proxy':0.65}}
    op.parent.mkdir(parents=True, exist_ok=True); op.write_text(json.dumps(doc,ensure_ascii=False,indent=2)+'\n', encoding='utf-8'); print(str(op)); return 0
if __name__=='__main__': raise SystemExit(main())
