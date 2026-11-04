"""HVCR-10 v3: transparent, non-overlapping conditional rebound research."""
import math
import numpy as np
import pandas as pd

HORIZONS=(5,10,20)
TARGET=.08
STOP=.05
COST_BPS=15
GAP=20

def wilson(k,n):
    if not n:return [None,None]
    z=1.96;p=k/n;den=1+z*z/n
    mid=(p+z*z/(2*n))/den
    half=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/den
    return [round(100*(mid-half),1),round(100*(mid+half),1)]

def analyze_frame(df):
    df=df[["Open","High","Low","Close","Volume"]].dropna().copy()
    if len(df)<330:raise ValueError("至少需要330個交易日")
    o,h,l,c,v=[df[k].astype(float) for k in ("Open","High","Low","Close","Volume")]
    delta=c.diff();up=delta.clip(lower=0).ewm(alpha=1/14,adjust=False,min_periods=14).mean()
    down=(-delta.clip(upper=0)).ewm(alpha=1/14,adjust=False,min_periods=14).mean()
    rsi=100-100/(1+up/down.replace(0,np.nan))
    rsi=rsi.where(down.ne(0),100)
    z=(c-c.rolling(20).mean())/c.rolling(20).std().replace(0,np.nan)
    vol_ratio=v/v.rolling(20).mean().shift(1).replace(0,np.nan)
    ema12=c.ewm(span=12,adjust=False).mean();ema26=c.ewm(span=26,adjust=False).mean()
    macd=ema12-ema26;hist=macd-macd.ewm(span=9,adjust=False).mean()
    prev=c.shift();tr=pd.concat([h-l,(h-prev).abs(),(l-prev).abs()],axis=1).max(axis=1)
    atr=tr.ewm(alpha=1/14,adjust=False,min_periods=14).mean()
    atr_pct=atr/c
    rv=np.log(c/prev).rolling(20).std()*np.sqrt(252)
    dollar=(c*v).rolling(20).mean()
    conditions=pd.DataFrame({
        "RSI14 ≤ 35":rsi<=35,
        "Z20 ≤ -1.5":z<=-1.5,
        "成交量 ≥ 1.3倍":vol_ratio>=1.3,
        "MACD動能連續改善":(hist>hist.shift(1))&(hist.shift(1)>hist.shift(2)),
        "ATR佔股價 ≥ 3%":atr_pct>=.03,
        "收盤突破前日高點":c>h.shift(1)
    },index=df.index).fillna(False)
    count=conditions.sum(axis=1)
    # Eligibility is determined at signal close, without future data.
    eligible=(c>=5)&(dollar>=20e6)&(rv>=.5)
    split=int(len(df)*.7)
    start=252;last=len(df)-max(HORIZONS)-2
    def select(mask):
        out=[];prev_idx=-GAP
        for i in range(start,last+1):
            if i-prev_idx<GAP:continue
            if bool(mask.iloc[i]):
                out.append(i);prev_idx=i
        return out
    baseline=select(eligible)
    events=select(eligible&(count>=4))
    # For an unbiased reference, compute unconditional eligible baseline independently.
    def outcome(i,days):
        entry=float(o.iloc[i+1])
        if not np.isfinite(entry) or entry<=0:return None
        target=entry*(1+TARGET);stop=entry*(1-STOP)
        hit=False;stopped=False;ambiguous=False
        for j in range(i+1,i+days+1):
            if float(o.iloc[j])<=stop:stopped=True;break
            if float(o.iloc[j])>=target:hit=True;break
            hit_high=float(h.iloc[j])>=target
            hit_low=float(l.iloc[j])<=stop
            if hit_high and hit_low:ambiguous=True;stopped=True;break
            if hit_low:stopped=True;break
            if hit_high:hit=True;break
        return {"success":hit,"stop_first":stopped,"ambiguous":ambiguous,"entry_date":str(df.index[i+1].date()),"signal_date":str(df.index[i].date())}
    def stats(indices,days):
        results=[outcome(i,days) for i in indices]
        results=[x for x in results if x is not None]
        n=len(results);wins=sum(x["success"] for x in results);stops=sum(x["stop_first"] for x in results)
        return {"n":n,"wins":wins,"prob_pct":round(wins/n*100,1) if n else None,
                "ci95_pct":wilson(wins,n),"stop_first_pct":round(stops/n*100,1) if n else None,
                "ambiguous_bars":sum(x["ambiguous"] for x in results)}
    comparisons={}
    for days in HORIZONS:
        comparisons[str(days)]={
            "train":stats([i for i in events if i<split],days),
            "test":stats([i for i in events if i>=split],days),
            "baseline_test":stats([i for i in baseline if i>=split],days),
            "test_by_score":{str(k):stats([i for i in events if i>=split and int(count.iloc[i])==k],days) for k in (4,5,6)}
        }
    latest_count=int(count.iloc[-1])
    latest_eligible=bool(eligible.iloc[-1])
    test=comparisons["10"]["test"];base=comparisons["10"]["baseline_test"]
    # Current score is descriptive only; probability is measured on held-out events.
    return {"ticker":None,"close":round(float(c.iloc[-1]),2),
            "last_price_date":str(df.index[-1].date()),"data_start_date":str(df.index[0].date()),
            "rv20":round(float(rv.iloc[-1])*100,1),"z20":round(float(z.iloc[-1]),2),
            "atr14":round(float(atr.iloc[-1]),2),"dollar_m":round(float(dollar.iloc[-1])/1e6,1),
            "rsi14":round(float(rsi.iloc[-1]),1) if pd.notna(rsi.iloc[-1]) else None,
            "matched":latest_count,"eligible":latest_eligible,
            "conditions":{k:bool(val) for k,val in conditions.iloc[-1].items()},
            "signal":"反彈觀察" if latest_eligible and latest_count>=4 else "未達條件",
            "probability":test["prob_pct"] if test["n"]>=30 else None,
            "probability_note":"樣本外事件不足30筆，不提供可用機率" if test["n"]<30 else "樣本外歷史頻率，非校準的個別預測",
            "backtest":{"model":"v3","target_pct":8,"stop_pct":5,"horizons":comparisons,
                "train_end":str(df.index[split-1].date()),
                "test_start":str(df.index[split].date()),
                "signal_events":len(events),"baseline_events":len(baseline),
                "latest_signal_date":str(df.index[-1].date()),
                "entry_rule":"訊號後下一交易日開盤",
                "cost_bps_per_side":COST_BPS,
                "method_note":"事件間至少20個交易日；先停損則失敗，同日同時觸及目標與停損保守視為停損；樣本外以時間70/30切分。機率為觸價頻率，不是扣成本淨獲利機率。"}}
