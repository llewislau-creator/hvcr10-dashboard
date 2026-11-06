"""Offline invariants for AlphaLens v2.2 market state diagnostics."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import numpy as np
import pandas as pd
from market_regime_v22 import classify_market_state

dates=pd.bdate_range("2025-01-01",periods=160)
base=np.linspace(100,140,160)
df=pd.DataFrame({"Close":base,"Volume":np.full(160,1000000)},index=dates)
ref=pd.Series(np.linspace(100,140,160),index=dates)
a=classify_market_state(df,ref)
assert a["status"]=="research_only"
assert a["benchmark_available"]
assert a["as_of"]==str(dates[-1].date())
assert a["bollinger"]["window"]==20
assert a["state"] in {"正常回調","上升趨勢","趨勢轉弱","高風險拋售","超賣後企穩"}
assert classify_market_state(df,ref)==a
# Future observations must not affect a previously computed classification.
future=pd.DataFrame({"Close":[1.],"Volume":[99999999.]},index=[dates[-1]+pd.Timedelta(days=3)])
assert classify_market_state(pd.concat([df,future]).iloc[:-1],ref)==a
assert classify_market_state(df.iloc[:50])["status"]=="insufficient_data"
# Price collapse on high volume, relative to a stable benchmark, triggers selloff.
shock=df.copy()
shock.loc[dates[-2:],"Close"]=[110,90]
shock.loc[dates[-2:],"Volume"]=[3000000,4000000]
stable=pd.Series(100.,index=dates)
b=classify_market_state(shock,stable)
assert b["state"]=="高風險拋售",b
print("market regime v2.2 offline checks passed")
