"""Historical warning evaluation: time-ordered, close-only, no future labels in features.

Risk event: forward close-to-close drawdown >=8% within 10 sessions.
Signals are evaluated at close, and event window starts next session.
Research-only; overlapping windows and cross-stock dependence limit inference.
"""
import numpy as np
import pandas as pd
from market_regime_v22 import classify_market_state

def evaluate_warning_history(frame, benchmark_close, horizon=10, drop_pct=8.0, min_history=330):
    d=frame[["Close","Volume"]].dropna().copy()
    if len(d)<min_history+horizon+1:
        return {"status":"insufficient_data","observations":0}
    close=d["Close"].astype(float)
    volume=d["Volume"].astype(float)
    ma50=close.rolling(50).mean()
    ma100=close.rolling(100).mean()
    r20=close.pct_change(20)
    ema12=close.ewm(span=12,adjust=False).mean()
    ema26=close.ewm(span=26,adjust=False).mean()
    macd=ema12-ema26
    hist=macd-macd.ewm(span=9,adjust=False).mean()
    delta=close.diff()
    up=delta.clip(lower=0).ewm(alpha=1/14,adjust=False,min_periods=14).mean()
    down=(-delta.clip(upper=0)).ewm(alpha=1/14,adjust=False,min_periods=14).mean()
    rsi=100-100/(1+up/down.replace(0,np.nan))
    rsi=rsi.mask((down==0)&(up>0),100).mask((down==0)&(up==0),50)
    ma20=close.rolling(20).mean()
    dollar=(close*volume).rolling(20).mean()
    v20=volume.rolling(20).mean().shift(1)
    spy=None
    if benchmark_close is not None:
        spy=benchmark_close.reindex(d.index).ffill()
    rel=r20-spy.pct_change(20) if spy is not None else None
    factors=[
        (close>ma50)&(ma50>ma100),
        (r20>0)&(hist>hist.shift(3)),
        (rel>0) if rel is not None else pd.Series(False,index=d.index),
        (close>ma50)&(close<ma20*1.05)&(rsi>=40)&(rsi<=70),
        (close>close.shift(1))&(volume>v20)
    ]
    score=sum(x.astype(int) for x in factors)/(5 if spy is not None else 4)*100
    eligible=(close>=5)&(dollar>=10e6)
    # Baseline: deterioration from original five-factor score below 60.
    # Compare using the same eligibility universe and same evaluation dates.
    start=max(min_history,int(len(d)*0.7))
    end=len(d)-horizon
    observations=[]
    for i in range(start,end):
        if not eligible.iloc[i]:continue
        if spy is not None and (pd.isna(spy.iloc[i]) or pd.isna(spy.iloc[i-20])):continue
        state=classify_market_state(d.iloc[:i+1],spy.iloc[:i+1] if spy is not None else None)["state"]
        risk=state=="高風險拋售"
        baseline=bool(score.iloc[i]<60)
        future=close.iloc[i+1:i+horizon+1]
        if len(future)!=horizon:continue
        max_loss=(float(future.min())/float(close.iloc[i])-1)*100
        event=max_loss<=-drop_pct
        observations.append({"date":str(d.index[i].date()),"risk":risk,"baseline":baseline,
                             "event":event,"max_forward_loss_pct":round(max_loss,3)})
    if not observations:return {"status":"insufficient_data","observations":0}
    def metrics(key):
        flagged=[x for x in observations if x[key]]
        tp=sum(x["event"] for x in flagged)
        events=sum(x["event"] for x in observations)
        fp=len(flagged)-tp
        return {"alerts":len(flagged),"true_positive":tp,"false_positive":fp,
                "false_alert_rate_pct":round(100*fp/len(flagged),2) if flagged else None,
                "event_recall_pct":round(100*tp/events,2) if events else None,
                "precision_pct":round(100*tp/len(flagged),2) if flagged else None}
    # First warning lead-time for each distinct event onset (non-overlapping events).
    event_starts=[]
    last_event=-horizon
    for i,x in enumerate(observations):
        if x["event"] and i-last_event>=horizon:
            event_starts.append(i)
            last_event=i
    lead={}
    for key in ("risk","baseline"):
        lead_days=[]
        for i in event_starts:
            prior=[j for j in range(max(0,i-horizon),i+1) if observations[j][key]]
            if prior:lead_days.append(i-prior[0])
        lead[key]={"events_with_warning":len(lead_days),
                   "mean_advance_sessions":round(float(np.mean(lead_days)),2) if lead_days else None}
    return {"status":"research_only","horizon_days":horizon,"drop_threshold_pct":drop_pct,
            "start":observations[0]["date"],"end":observations[-1]["date"],
            "observations":len(observations),"downside_events":sum(x["event"] for x in observations),
            "risk_classifier":metrics("risk"),"five_factor_baseline":metrics("baseline"),
            "event_lead_time":lead,
            "method":"Chronological last 30%; daily close signals; future 10-session minimum close <= -8% from signal close; baseline original five-factor score <60; only liquid/eligible days; overlapping future windows; event lead time exploratory, not causal.",
            "limitations":"Overlapping daily windows, selected ticker universe, correlated securities, adjusted prices and fixed ex-post thresholds; no statistically validated incremental edge."}
