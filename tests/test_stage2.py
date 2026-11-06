"""Stage 2 deterministic tests: no external data."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import numpy as np,pandas as pd
from stage2_risk import make_plan,simulate_plan,summarize_trades,backtest_plans,moving_block_bootstrap_ci,block_bootstrap_diagnostic
n=700
dates=pd.bdate_range("2022-01-03",periods=n)
close=100+np.arange(n)*.07
df=pd.DataFrame({"Open":close,"High":close+1,"Low":close-1,"Close":close,"Volume":np.full(n,2e6)},index=dates)
plan=make_plan(df)
assert 0<plan["stop"]<plan["reference_entry"]<plan["target"]
assert plan["shares"]*plan["reference_entry"]<=1500+1e-8
assert plan["shares"]*(plan["reference_entry"]-plan["stop"])<=50+1
for days in (10,15,20):
    x=simulate_plan(df,350,make_plan(df.iloc[:351]),days=days)
    assert x is not None and x["net_return_pct"]<=x["gross_return_pct"]
    y=backtest_plans(df,days=days,benchmark_close=df.Close)
    assert y["n"]>=0
    mb=y['moving_block_bootstrap']
    assert mb['repeats']==2000 and mb['block_lengths']==[5,10,20]
    assert mb['iid_ci95_pct']==y['mean_net_bootstrap_ci95_pct']
    for k in (5,10,20):
        ci=mb['ci95_pct'][str(k)]
        assert (ci is None) if y['n']<k else (len(ci)==2 and ci[0]<=ci[1])
    audit=y['walk_forward']['trade_audit']
    assert len(audit)==y['n']
    assert len({(t['signal_date'],t['entry_date'],t['exit_date']) for t in audit})==len(audit)
    for i,t in enumerate(audit):
        fold=y['walk_forward']['folds'][t['fold']-1]
        assert fold['validation_start']<=t['signal_date']<t['entry_date']<=t['exit_date']<=fold['validation_end']
        if i: assert audit[i-1]['exit_date']<t['entry_date']
    assert all(sum(t['fold']==j for t in audit)==y['walk_forward']['folds'][j-1]['n'] for j in (1,2,3))
    assert y['walk_forward']['trade_reuse'] is False
    assert y['walk_forward']['no_overlapping_positions'] is True
    assert y['bear_market_robustness']['sample_threshold']==30
    assert y['bear_market_robustness']['sample_adequate'] is False
    assert y['bear_market_robustness']['label']=='熊市穩健性未驗證'
    for fold in y['walk_forward']['folds']:
        assert fold['validation_start']<=fold['validation_end']
    assert all(y['walk_forward']['folds'][j]['validation_end']<y['walk_forward']['folds'][j+1]['validation_start'] for j in range(2))
    assert len(y["walk_forward"]["folds"])==3
    assert sum(f["n"] for f in y["walk_forward"]["folds"])==y["n"]
    assert "mean_net_bootstrap_ci95_pct" in y
    assert sum(z["n"] for z in y["regime_results"].values())==y["n"]
    if y["n"]>=2:
        assert y["mean_net_bootstrap_ci95_pct"][0]<=y["mean_net_bootstrap_ci95_pct"][1]
# Same-bar ambiguous stop takes precedence.
short=df.iloc[:110].copy()
p=make_plan(short)
short.iloc[-1,short.columns.get_loc("Close")]=p["reference_entry"]
future=pd.concat([short,df.iloc[110:121].copy()])
future.iloc[110,future.columns.get_loc("Open")]=p["reference_entry"]
future.iloc[110,future.columns.get_loc("High")]=p["target"]+1
future.iloc[110,future.columns.get_loc("Low")]=p["stop"]-1
t=simulate_plan(future,109,p,days=10)
assert t["exit_reason"].startswith("止損優先")
assert summarize_trades([t])["n"]==1
# Moving blocks preserve adjacent observations and are reproducible.
sequence=np.array([0.,0.,0.,0.,0.,10.,10.,10.,10.,10.])
for k in (5,10):
    ci=moving_block_bootstrap_ci(sequence,k)
    assert ci==moving_block_bootstrap_ci(sequence,k)
    assert ci[0]<=sequence.mean()<=ci[1]
for k in (5,10):
    moving=block_bootstrap_diagnostic(sequence,k)
    circular=block_bootstrap_diagnostic(sequence,k,circular=True)
    assert moving==block_bootstrap_diagnostic(sequence,k)
    assert circular==block_bootstrap_diagnostic(sequence,k,circular=True)
    assert moving["ci95_pct"][0]<=moving["ci95_pct"][1]
    assert circular["ci95_pct"][0]<=circular["ci95_pct"][1]
    assert abs(circular["center_shift_pct"])<2
assert block_bootstrap_diagnostic(sequence,20,circular=True) is None
assert moving_block_bootstrap_ci(sequence,20) is None
assert moving_block_bootstrap_ci([1.],1) is None
try:
    moving_block_bootstrap_ci([1.,float('nan')],1)
    raise AssertionError('expected invalid sequence rejection')
except ValueError:
    pass
print("stage2 tests passed")
