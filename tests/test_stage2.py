"""Stage 2 deterministic tests: no external data."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import numpy as np,pandas as pd
from stage2_risk import make_plan,simulate_plan,summarize_trades,backtest_plans
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
print("stage2 tests passed")
