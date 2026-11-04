"""Deterministic smoke tests: no network required."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import numpy as np
import pandas as pd
from rebound_v3 import analyze_frame,wilson

assert wilson(0,0)==[None,None]
assert wilson(50,100)[0]<50<wilson(50,100)[1]
n=700
rng=np.random.default_rng(42)
dates=pd.bdate_range("2022-01-03",periods=n)
close=70+np.cumsum(rng.normal(0,2.5,n))
close=np.maximum(close,7)
open_=close+rng.normal(0,.5,n)
high=np.maximum(close,open_)+rng.uniform(.1,2,n)
low=np.minimum(close,open_)-rng.uniform(.1,2,n)
df=pd.DataFrame({"Open":open_,"High":high,"Low":low,"Close":close,"Volume":np.full(n,20000000)},index=dates)
r=analyze_frame(df)
assert len(r["conditions"])==6
assert r["matched"]==sum(r["conditions"].values())
assert r["signal"] in ("反彈觀察","未達條件")
assert set(r["backtest"]["horizons"])=={"5","10","20"}
for horizon,stats in r["backtest"]["horizons"].items():
    for group in ("train","test","baseline_test"):
        s=stats[group]
        assert 0<=s["wins"]<=s["n"]
        if s["n"]:assert 0<=s["prob_pct"]<=100
    for score in ("4","5","6"):
        assert score in stats["test_by_score"]
print("v3 smoke tests passed")
