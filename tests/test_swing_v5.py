"""Offline regression test for 2–4 week swing research."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import numpy as np,pandas as pd
from swing_v5 import swing_research
n=700;rng=np.random.default_rng(4)
dates=pd.bdate_range("2021-01-04",periods=n)
close=100+np.cumsum(rng.normal(.05,1.4,n))
open_=close+rng.normal(0,.3,n)
high=np.maximum(open_,close)+.5;low=np.minimum(open_,close)-.5
df=pd.DataFrame({"Open":open_,"High":high,"Low":low,"Close":close,"Volume":np.full(n,2000000)},index=dates)
s=swing_research(df,df.Close*.98)
assert s["holding_trading_days"]==[10,15,20]
assert s["factor_count"]==5 and len(s["factors"])==5
assert s["score"] is not None and 0<=s["score"]<=100
assert set(s["holdout"])=={"10","15","20"}
for h in s["holdout"].values():
    assert h["n"]>=0
    if h["n"]:assert -100<=h["positive_net_pct"]<=100
s2=swing_research(df)
assert s2["factor_count"]==4 and s2["factors"]["相對市場強度"] is None
print("swing research tests passed")
