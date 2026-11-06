"""Five-factor research-only backtest; identical scoring to scripts/swing_v5.py."""
import numpy as np
import pandas as pd
FRICTION=.0025
def factors(df,spy):
 c=df.Close;v=df.Volume
 ma20=c.rolling(20).mean();ma50=c.rolling(50).mean();ma100=c.rolling(100).mean()
 r20=c.pct_change(20);delta=c.diff()
 up=delta.clip(lower=0).ewm(alpha=1/14,adjust=False,min_periods=14).mean()
 down=(-delta.clip(upper=0)).ewm(alpha=1/14,adjust=False,min_periods=14).mean()
 rsi=100-100/(1+up/down.replace(0,np.nan))
 rsi=rsi.mask((down==0)&(up>0),100).mask((down==0)&(up==0),50)
 macd=c.ewm(span=12,adjust=False).mean()-c.ewm(span=26,adjust=False).mean()
 hist=macd-macd.ewm(span=9,adjust=False).mean()
 bench=spy.reindex(df.index).ffill()
 if bench.isna().any():raise ValueError("SPY missing at stock dates")
 ff=pd.DataFrame({"trend":(c>ma50)&(ma50>ma100),"momentum":(r20>0)&(hist>hist.shift(3)),"relative_spy":r20>bench.pct_change(20),"pullback":(c>ma50)&(c<ma20*1.05)&(rsi>=40)&(rsi<=70),"price_volume":(c>c.shift(1))&(v>v.rolling(20).mean().shift(1))})
 return ff.fillna(False).sum(axis=1)*20,(c>=5)&((c*v).rolling(20).mean()>=1e7),ma50
def simulate(df,spy,horizon,mode):
 if horizon not in (10,15,20) or mode not in ("legacy_fixed","fixed","signal"):raise ValueError("bad mode")
 d=df[["Open","High","Low","Close","Volume"]].dropna().sort_index()
 if len(d)<330 or not d.index.is_unique:raise ValueError("invalid bars")
 score,eligible,ma50=factors(d,spy)
 benchmark=spy.reindex(d.index).ffill()
 i=max(150,int(len(d)*.7));trades=[]
 while i+horizon<len(d):
  if not (eligible.iloc[i] and (score.iloc[i]>=60 if mode=="legacy_fixed" else score.iloc[i]>=80 and d.Close.iloc[i]>ma50.iloc[i])):
   i+=1;continue
  entry_idx=i+1;exit_idx=i+horizon;reason="horizon_close";exit_price=float(d.Close.iloc[exit_idx])
  if mode=="signal":
   for j in range(entry_idx,i+horizon):
    weak=score.iloc[j]<60
    below_two=j>=1 and d.Close.iloc[j]<ma50.iloc[j] and d.Close.iloc[j-1]<ma50.iloc[j-1]
    if weak or below_two:
     exit_idx=j+1;exit_price=float(d.Open.iloc[exit_idx]);reason="score_below_60" if weak else "two_closes_below_ma50";break
  entry=float(d.Open.iloc[entry_idx])
  if not np.isfinite(entry*exit_price) or min(entry,exit_price)<=0:raise ValueError("bad fill")
  net=exit_price*(1-FRICTION)/(entry*(1+FRICTION))-1
  spy_ret=float(benchmark.iloc[exit_idx]/benchmark.iloc[entry_idx]-1)
  trades.append({"ticker_signal_date":str(d.index[i].date()),"entry_date":str(d.index[entry_idx].date()),"exit_date":str(d.index[exit_idx].date()),"entry":entry,"exit":exit_price,"reason":reason,"net_return_pct":100*net,"spy_return_pct":100*spy_ret,"excess_spy_pct":100*(net-spy_ret)})
  i=exit_idx+1
 return trades
def metrics(trades):
 if not trades:return {"n":0,"mean_net_pct":None,"win_rate_pct":None,"max_sequential_drawdown_pct":None,"mean_excess_spy_pct":None,"cost_bps_per_side":25}
 r=np.array([t["net_return_pct"]/100 for t in trades])
 # Across stocks, this is only an arithmetic sequence diagnostic; not portfolio drawdown.
 equity=np.cumprod(1+r);peaks=np.maximum.accumulate(np.r_[1.,equity])[1:]
 return {"n":len(trades),"mean_net_pct":round(float(r.mean()*100),3),"win_rate_pct":round(float((r>0).mean()*100),2),"max_sequential_drawdown_pct":round(float((equity/peaks-1).min()*100),3),"mean_excess_spy_pct":round(float(np.mean([t["excess_spy_pct"] for t in trades])),3),"cost_bps_per_side":25}
