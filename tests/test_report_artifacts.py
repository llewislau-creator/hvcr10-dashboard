"""Verify generated dashboard, trade audit, and block bootstrap artifacts."""
import json
from pathlib import Path
root=Path(__file__).resolve().parents[1]/'site'/'data'
report=json.loads((root/'report.json').read_text(encoding='utf-8'))
audit=json.loads((root/'trade_audit.json').read_text(encoding='utf-8'))
summary=json.loads((root/'bootstrap_summary.json').read_text(encoding='utf-8'))
portfolio=json.loads((root/'portfolio_risk.json').read_text(encoding='utf-8'))
diagnostics=json.loads((root/'price_diagnostics.json').read_text(encoding='utf-8'))
assert report['updated_utc']==audit['updated_utc']==summary['updated_utc']==diagnostics['updated_utc']
assert len(summary['groups'])==3*len(report['rows'])
assert portfolio['updated_utc']==report['updated_utc']
assert set(portfolio['portfolios'])=={'10','15','20'}
for p in portfolio['portfolios'].values():
    if p['status']!='no_trades':
        assert p['max_exposure_pct']<=100.00001
        assert p['max_concurrent_positions']<=len(report['rows'])
assert 'GME' in diagnostics['excluded_diagnostics']
keys=set()
for row in report['rows']:
    for h in (10,15,20):
        bt=row['stage2']['backtests'][str(h)]
        wf=bt['walk_forward']
        key=f"{row['ticker']}:{h}"
        keys.add(key)
        assert 'trade_audit' not in wf
        assert wf['audit_file']=='trade_audit.json' and wf['audit_key']==key
        record=audit['trades'][key]
        trades=record['trades']
        assert len(trades)==bt['n']==wf['total_unique_trades']
        if trades:
            assert abs(sum(t['net_return_pct'] for t in trades)/len(trades)-bt['mean_net_pct'])<.011
        for t in trades:
            assert all(k in t for k in ('entry_price','exit_price','exit_reason','gross_return_pct','net_return_pct','cost_bps_per_side','slippage_bps_per_side'))
        assert sum(f['n'] for f in record['folds'])==len(trades)
        assert len({(t['signal_date'],t['entry_date'],t['exit_date']) for t in trades})==len(trades)
        for i,t in enumerate(trades):
            fold=record['folds'][t['fold']-1]
            assert fold['validation_start']<=t['signal_date']<t['entry_date']<=t['exit_date']<=fold['validation_end']
            if i:assert trades[i-1]['exit_date']<t['entry_date']
        mb=bt['moving_block_bootstrap']
        for method in ('moving_diagnostics','circular_diagnostics'):
            assert set(mb[method])=={'5','10','20'}
            for k,v in mb[method].items():
                if v is not None:
                    assert v['ci95_pct'][0]<=v['ci95_pct'][1]
                    assert abs(v['center_shift_pct']-(v['bootstrap_mean_pct']-v['original_mean_pct']))<.0002
        assert set(mb['circular_seed_sensitivity'])=={'5','10','20'}
        for s in mb['circular_seed_sensitivity'].values():
            if s is not None:
                assert len(s['seeds'])==len(s['ci_width_pct_by_seed'])==len(s['center_shift_pct_by_seed'])==5
                assert 0<=s['positive_lower_count']<=5
        assert mb['repeats']==2000 and mb['block_lengths']==[5,10,20]
        assert mb['iid_ci95_pct']==bt['mean_net_bootstrap_ci95_pct']
        for k in (5,10,20):
            ci=mb['ci95_pct'][str(k)]
            assert (ci is None) if bt['n']<k else (len(ci)==2 and ci[0]<=ci[1])
assert set(audit['trades'])==keys
assert {g['audit_key'] for g in summary['groups']}==keys
for g in summary['groups']:
    assert g['n']==len(audit['trades'][g['audit_key']]['trades'])
    assert set(g['block_ci95_pct'])=={'5','10','20'}
    assert set(g['moving_diagnostics'])==set(g['circular_diagnostics'])=={'5','10','20'}
    iid=g['iid_ci95_pct']
    assert g['iid_positive']==(iid is not None and iid[0]>0)
    assert g['weakens_vs_iid']==(g['iid_positive'] and any(v is None or v[0]<=0 for v in g['block_ci95_pct'].values()))
    for k,v in g['block_ci95_pct'].items():
        assert g['block_positive'][k]==(v is not None and v[0]>0)
print('report artifact tests passed')
