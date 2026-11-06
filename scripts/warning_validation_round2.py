"""Second-round historical risk-warning comparison (research-only).

Events: first close <= 92% of previous 20-session closing high, with a 10-session
refractory period. Warnings are evaluated only if emitted 1..10 sessions BEFORE
event onset. Same maximum alert budget for every model: 2 per 21 sessions.
No forward returns are used to generate signals.
"""
import numpy as np
import pandas as pd
from market_regime_v22 import classify_market_state

LOOKBACK=10
EVENT_DROP=0.08
COOLDOWN=10
BUDGET_WINDOW=21
BUDGET_MAX=2

def _budget(raw, eligible):
    chosen=[]
    for i,flag in enumerate(raw):
        if not flag or not eligible[i]:continue
        if sum(i-BUDGET_WINDOW<j<=i for j in chosen)>=BUDGET_MAX:continue
        chosen.append(i)
    return chosen

def _metrics(alerts, events, n):
    hits=set()
    lead=[]
    for event in events:
        valid=[a for a in alerts if 1<=event-a<=LOOKBACK]
        if valid:
            hits.update(valid)
            lead.append(event-max(valid))
    # Alert success: an event within the next 10 sessions.
    success=[a for a in alerts if any(1<=e-a<=LOOKBACK for e in events)]
    return {"alerts":len(alerts),"successful_alerts":len(success),
            "false_alerts":len(alerts)-len(success),
            "false_alert_rate_pct":round(100*(len(alerts)-len(success))/len(alerts),2) if alerts else None,
            "independent_events":len(events),"events_warned":len(lead),
            "event_recall_pct":round(100*len(lead)/len(events),2) if events else None,
            "median_lead_sessions":float(np.median(lead)) if lead else None,
            "precision_pct":round(100*len(success)/len(alerts),2) if alerts else None}

def evaluate_second_round(frame, benchmark_close, min_history=330):
    d=frame[["Close","Volume"]].dropna().copy()
    if len(d)<min_history+LOOKBACK+30:return {"status":"insufficient_data"}
    c=d.Close.astype(float)
    v=d.Volume.astype(float)
    spy=benchmark_close.reindex(d.index).ffill()
    ma20=c.rolling(20).mean()
    ma50=c.rolling(50).mean()
    ma100=c.rolling(100).mean()
    r20=c.pct_change(20)
    hist=(c.ewm(span=12,adjust=False).mean()-c.ewm(span=26,adjust=False).mean())
    hist=hist-hist.ewm(span=9,adjust=False).mean()
    delta=c.diff()
    up=delta.clip(lower=0).ewm(alpha=1/14,adjust=False,min_periods=14).mean()
    down=(-delta.clip(upper=0)).ewm(alpha=1/14,adjust=False,min_periods=14).mean()
    rsi=100-100/(1+up/down.replace(0,np.nan))
    rsi=rsi.mask((down==0)&(up>0),100).mask((down==0)&(up==0),50)
    rel=r20-spy.pct_change(20)
    volume20=v.rolling(20).mean().shift(1)
    factors=[(c>ma50)&(ma50>ma100),(r20>0)&(hist>hist.shift(3)),
             rel>0,(c>ma50)&(c<ma20*1.05)&(rsi>=40)&(rsi<=70),
             (c>c.shift(1))&(v>volume20)]
    score=sum(x.astype(int) for x in factors)*20
    eligible=(c>=5)&((c*v).rolling(20).mean()>=10e6)&spy.notna()
    # Holdout: last 30%; signal indicators use only the past.
    start=max(min_history,int(len(d)*0.7))
    end=len(d)
    states=[]
    for i in range(start,end):
        states.append(classify_market_state(d.iloc[:i+1],spy.iloc[:i+1])["state"])
    # Onset of first 8% drawdown from prior 20-day high; do not label
    # ongoing below-threshold days as new independent events.
    prior_peak=c.rolling(20).max().shift(1)
    underwater=(c<=prior_peak*(1-EVENT_DROP)).fillna(False)
    events=[]
    last=-COOLDOWN-1
    for i in range(start+LOOKBACK,end):
        if underwater.iloc[i] and not underwater.iloc[i-1] and i-last>COOLDOWN:
            events.append(i-start)
            last=i
    raw={
        "early_weakness":[s=="趨勢轉弱" for s in states],
        "high_risk_selloff":[s=="高風險拋售" for s in states],
        "weakness_or_selloff":[s in ("趨勢轉弱","高風險拋售") for s in states],
        "five_factor_below_60":[bool(score.iloc[start+i]<60) for i in range(len(states))]
    }
    valid=eligible.iloc[start:end].tolist()
    results={}
    for key,flags in raw.items():
        # Transition-only warning: no repeat every day in same state.
        transitions=[f and (i==0 or not flags[i-1]) for i,f in enumerate(flags)]
        alerts=_budget(transitions,valid)
        results[key]=_metrics(alerts,events,len(states))
    return {"status":"preliminary_research","start":str(d.index[start].date()),
            "end":str(d.index[-1].date()),"observations":len(states),
            "events":len(events),"models":results,
            "rules":{"event":"First crossing below 92% of previous 20-session closing high; cooldown 10 sessions",
                     "warning":"Only transition into state; signals at close; warning must precede event by 1..10 sessions",
                     "budget":"Each model at most 2 alerts per 21 sessions, not necessarily identical realized alert counts",
                     "split":"Chronological last 30% of each ticker; fixed provisional rules"},
            "limitations":"Event defined by drawdown from recent high, not future -8% from warning close. Same cap but unequal actual alert counts. Cross-stock dependence and survivorship bias remain. No parameter search or independent prospective validation."}
