"""HVCR-10 v3: transparent, non-overlapping conditional rebound research."""
import math
import numpy as np
import pandas as pd
from execution_v4 import simulate_ohlc_trade, summarize

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
    rsi=rsi.mask((down==0)&(up>0),100).mask((down==0)&(up==0),50)
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
            "train":stats([i for i in events if i+days+1<split],days),
            "test":stats([i for i in events if i>=split],days),
            "baseline_test":stats([i for i in baseline if i>=split],days),
            "test_by_score":{str(k):stats([i for i in events if i>=split and int(count.iloc[i])==k],days) for k in (4,5,6)}
        }
    # v4 execution diagnostics: held-out signals only; 10-day horizon, next-day open.
    heldout=[i for i in events if i>=split and i+10<len(df)]
    trades=[simulate_ohlc_trade(o.to_numpy(),h.to_numpy(),l.to_numpy(),c.to_numpy(),i+1,horizon=10) for i in heldout]
    execution_summary=summarize([t for t in trades if t is not None])
    execution_summary["cost_bps_per_side"]=COST_BPS
    execution_summary["slippage_bps_per_side"]=10
    execution_summary["research_only"]=True
    # Additional research indicators: display only; do not alter v3 signal gates.
    bb_mid=c.rolling(20).mean()
    bb_std=c.rolling(20).std()
    bb_lower=bb_mid-2*bb_std
    bb_reclaim=(c>bb_lower)&(c.shift(1)<=(bb_mid.shift(1)-2*bb_std.shift(1)))
    obv=(np.sign(c.diff()).fillna(0)*v).cumsum()
    obv_ema=obv.ewm(span=10,adjust=False).mean()
    obv_improve=(obv>obv_ema)&(obv.diff(5)>0)
    plus_dm=h.diff().where((h.diff()>-l.diff())&(h.diff()>0),0)
    minus_dm=(-l.diff()).where((-l.diff()>h.diff())&(-l.diff()>0),0)
    atr_safe=atr.replace(0,np.nan)
    plus_di=100*plus_dm.ewm(alpha=1/14,adjust=False,min_periods=14).mean()/atr_safe
    minus_di=100*minus_dm.ewm(alpha=1/14,adjust=False,min_periods=14).mean()/atr_safe
    dx=100*(plus_di-minus_di).abs()/(plus_di+minus_di).replace(0,np.nan)
    adx=dx.ewm(alpha=1/14,adjust=False,min_periods=14).mean()
    vwap20=(c*v).rolling(20).sum()/v.rolling(20).sum().replace(0,np.nan)
    # RSI bullish divergence: current 5-day low versus preceding 5-day window.
    prior_price_low=c.shift(5).rolling(5).min()
    prior_rsi_low=rsi.shift(5).rolling(5).min()
    bullish_divergence=(c.rolling(5).min()<prior_price_low)&(rsi.rolling(5).min()>prior_rsi_low)
    def val(s):
        x=s.iloc[-1]
        return round(float(x),2) if pd.notna(x) and np.isfinite(x) else None
    extra={
        "RSI 多頭背離（5日窗口）":{"value":val(rsi),"observed":bool(bullish_divergence.iloc[-1]),"unit":"RSI"},
        "布林通道下軌收復":{"value":val(bb_lower),"observed":bool(bb_reclaim.iloc[-1]),"unit":"美元"},
        "OBV 資金量能改善":{"value":val(obv),"observed":bool(obv_improve.iloc[-1]),"unit":"累計量"},
        "ADX 趨勢強度":{"value":val(adx),"observed":bool(pd.notna(adx.iloc[-1]) and adx.iloc[-1]<25),"unit":"ADX（低於25視為趨勢較弱）"},
        "20日收盤價成交量加權均價（非盤中VWAP）":{"value":val(vwap20),"observed":bool(c.iloc[-1]>vwap20.iloc[-1]),"unit":"美元"}
    }
    # v3.1: transparent 12-condition score, not itself a probability.
    extra_flags=[bool(x["observed"]) for x in extra.values()]
    # SPY relative strength is attached by update.py; missing SPY is explicitly unavailable.
    extra_count=sum(extra_flags)
    composite_score=round(100*(int(count.iloc[-1])+extra_count)/11,1)
    latest_count=int(count.iloc[-1])
    latest_eligible=bool(eligible.iloc[-1])
    test=comparisons["10"]["test"];base=comparisons["10"]["baseline_test"]
    # Current score is descriptive only; probability is measured on held-out events.
    return {"ticker":None,"close":round(float(c.iloc[-1]),2),
            "last_price_date":str(df.index[-1].date()),"data_start_date":str(df.index[0].date()),
            "rv20":round(float(rv.iloc[-1])*100,1),"z20":round(float(z.iloc[-1]),2),
            "atr14":round(float(atr.iloc[-1]),2),"dollar_m":round(float(dollar.iloc[-1])/1e6,1),
            "rsi14":round(float(rsi.iloc[-1]),1) if pd.notna(rsi.iloc[-1]) else None,
            "matched":latest_count,"eligible":latest_eligible,"extra_indicators":extra,
            "composite_score_11":composite_score,"composite_note":"11項等權觀察分數（6核心+5輔助）；SPY另列，不等於機率",
            "conditions":{k:bool(val) for k,val in conditions.iloc[-1].items()},
            "signal":"反彈觀察" if latest_eligible and latest_count>=4 else "未達條件",
            "probability":test["prob_pct"] if test["n"]>=30 else None,
            "probability_note":"樣本外事件不足30筆，不提供可用機率" if test["n"]<30 else "樣本外歷史頻率，非校準的個別預測",
            "execution_v4":execution_summary,
            "backtest":{"model":"v3","target_pct":8,"stop_pct":5,"horizons":comparisons,
                "train_end":str(df.index[split-1].date()),
                "test_start":str(df.index[split].date()),
                "signal_events":len(events),"baseline_events":len(baseline),
                "latest_signal_date":str(df.index[-1].date()),
                "entry_rule":"訊號後下一交易日開盤",
                "cost_bps_per_side":COST_BPS,
                "method_note":"事件間至少20個交易日；先停損則失敗，同日同時觸及目標與停損保守視為停損；樣本外以時間70/30切分。機率為觸價頻率，不是扣成本淨獲利機率。"}}
