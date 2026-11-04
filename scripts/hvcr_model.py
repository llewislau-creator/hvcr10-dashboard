"""HVCR-10 research-only causal cycle signals and cost-aware event backtest."""
import numpy as np
import pandas as pd

def indicators(df):
    high,low,close=df["High"],df["Low"],df["Close"]
    prev=close.shift()
    tr=pd.concat([high-low,(high-prev).abs(),(low-prev).abs()],axis=1).max(axis=1)
    atr=tr.ewm(alpha=1/14,adjust=False,min_periods=14).mean()
    rv=np.log(close/prev).rolling(20).std()*np.sqrt(252)
    z=(close-close.rolling(20).mean())/close.rolling(20).std().replace(0,np.nan)
    liquid=(close*df["Volume"]).rolling(20).mean()
    return atr,rv,z,liquid

def confirmed_pivots(close, atr):
    """Only emit a pivot on its confirmation bar, never at its historical extreme."""
    direction=0;anchor=None;extreme=None;extreme_idx=None;out=[]
    for i in range(len(close)):
        p=float(close.iloc[i]); a=float(atr.iloc[i]) if pd.notna(atr.iloc[i]) else np.nan
        if not np.isfinite(a) or p<=0: continue
        threshold=max(.05,1.5*a/p)
        if anchor is None:
            anchor=p;extreme=p;extreme_idx=i;continue
        if direction==0:
            if p>=anchor*(1+threshold):
                out.append(("low",extreme_idx,i,anchor));direction=1;extreme=p;extreme_idx=i
            elif p<=anchor*(1-threshold):
                out.append(("high",extreme_idx,i,anchor));direction=-1;extreme=p;extreme_idx=i
            else:
                # Track an initial candidate extreme without using future bars.
                if p<anchor:anchor=p;extreme=p;extreme_idx=i
        elif direction==1:
            if p>extreme:extreme=p;extreme_idx=i
            elif p<=extreme*(1-threshold):
                out.append(("high",extreme_idx,i,extreme));direction=-1;extreme=p;extreme_idx=i
        else:
            if p<extreme:extreme=p;extreme_idx=i
            elif p>=extreme*(1+threshold):
                out.append(("low",extreme_idx,i,extreme));direction=1;extreme=p;extreme_idx=i
    return out

def cycle_features(events, asof):
    lows=[e for e in events if e[0]=="low" and e[2]<=asof]
    durations=[b[2]-a[2] for a,b in zip(lows,lows[1:])]
    recent=durations[-12:]
    med=float(np.median(recent)) if recent else None
    cv=float(np.std(recent,ddof=1)/np.mean(recent)) if len(recent)>=2 and np.mean(recent)>0 else None
    # Sample-size and stability only; not a calibrated probability.
    score=int(round(100*(min(len(recent),8)/8)*max(0,1-min(cv if cv is not None else 1,1)))) if recent else 0
    return len(recent),med,cv,score

def backtest(df, atr, rv, z, liquid, events, cost_bps=15, max_days=10):
    """Daily close signal, next-open fill, next-open time exit or ATR stop; nonoverlapping."""
    closes=df["Close"].to_numpy(dtype=float)
    opens=df["Open"].to_numpy(dtype=float)
    lows=df["Low"].to_numpy(dtype=float)
    confirmed_by_bar={}
    for e in events:confirmed_by_bar.setdefault(e[2],[]).append(e)
    trades=[];last_exit=-1
    counts={"evaluated_days":0,"liquidity_volatility_pass":0,"zscore_pass":0,"cycles_pass":0,"score_pass":0,"trade_entries":0}
    for i in range(252,len(df)-max_days-1):
        if i<=last_exit:continue
        counts["evaluated_days"]+=1
        if not (closes[i]>=5 and rv.iloc[i]>=.5 and liquid.iloc[i]>=20e6):continue
        counts["liquidity_volatility_pass"]+=1
        if not (pd.notna(z.iloc[i]) and z.iloc[i]<=-1.5):continue
        counts["zscore_pass"]+=1
        n,med,cv,score=cycle_features(events,i)
        if n<6:continue
        counts["cycles_pass"]+=1
        if score<75:continue
        counts["score_pass"]+=1
        entry_idx=i+1;entry=opens[entry_idx]
        if not np.isfinite(entry) or entry<=0 or not np.isfinite(atr.iloc[i]):continue
        stop=entry-1.5*float(atr.iloc[i])
        exit_idx=entry_idx+max_days;exit_price=opens[exit_idx];reason="time"
        for j in range(entry_idx,exit_idx):
            if opens[j]<=stop:
                exit_idx=j;exit_price=opens[j];reason="gap_stop";break
            if lows[j]<=stop:
                exit_idx=j;exit_price=stop;reason="stop";break
        if not np.isfinite(exit_price) or exit_price<=0:continue
        gross=(exit_price/entry-1)*100
        net=gross-2*cost_bps/100
        trades.append({"entry_date":str(df.index[entry_idx].date()),"exit_date":str(df.index[exit_idx].date()),"gross_pct":round(gross,2),"net_pct":round(net,2),"exit_reason":reason})
        last_exit=exit_idx
        counts["trade_entries"]+=1
    nets=[t["net_pct"] for t in trades]
    return {"trades":len(trades),"avg_net_pct":round(float(np.mean(nets)),2) if nets else None,"win_net_pct":round(float(np.mean(np.array(nets)>0)*100),1) if nets else None,"cost_bps_per_side":cost_bps,"recent_trades":trades[-10:],"diagnostics":counts,"period_start":str(df.index[252].date()) if len(df)>252 else None,"period_end":str(df.index[-max_days-2].date()) if len(df)>max_days+2 else None}

def analyze_frame(df):
    df=df[["Open","High","Low","Close","Volume"]].dropna().copy()
    if len(df)<280:raise ValueError("insufficient OHLCV history")
    atr,rv,z,liquid=indicators(df)
    events=confirmed_pivots(df["Close"],atr)
    i=len(df)-1
    n,med,cv,score=cycle_features(events,i)
    eligible=bool(df["Close"].iloc[i]>=5 and rv.iloc[i]>=.5 and liquid.iloc[i]>=20e6)
    signal=bool(eligible and pd.notna(z.iloc[i]) and z.iloc[i]<=-1.5 and n>=6 and score>=75)
    bt=backtest(df,atr,rv,z,liquid,events)
    return {"close":round(float(df["Close"].iloc[-1]),2),"rv20":round(float(rv.iloc[-1])*100,1),"z20":round(float(z.iloc[-1]),2) if pd.notna(z.iloc[-1]) else None,"dollar_m":round(float(liquid.iloc[-1])/1e6,1),"atr14":round(float(atr.iloc[-1]),2),"cycle_days":round(med,1) if med is not None else None,"cycle_cv":round(cv,2) if cv is not None else None,"cycles":n,"cycle_score":score,"signal":"反轉觀察" if signal else "無訊號","last_price_date":str(df.index[-1].date()),"data_start_date":str(df.index[0].date()),"last_confirmation":str(df.index[events[-1][2]].date()) if events else None,"backtest":bt}
