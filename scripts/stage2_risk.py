"""Stage 2: risk-budgeted 2–4 week swing trade plans and causal OHLC exits.
Research only. All plan levels use information available at signal close.
"""
import math
import numpy as np
import pandas as pd

def make_plan(df, capital=10000, risk_fraction=.005, max_position_fraction=.15):
    d=df[["Open","High","Low","Close","Volume"]].dropna()
    if len(d)<100:raise ValueError("至少需要100個交易日")
    c=d.Close.astype(float);h=d.High.astype(float);l=d.Low.astype(float)
    prev=c.shift(1)
    tr=pd.concat([h-l,(h-prev).abs(),(l-prev).abs()],axis=1).max(axis=1)
    atr=tr.ewm(alpha=1/14,adjust=False,min_periods=14).mean().iloc[-1]
    price=float(c.iloc[-1])
    if not all(np.isfinite(x) and x>0 for x in (atr,price,capital)):raise ValueError("價格、ATR或資金無效")
    if not (0<risk_fraction<=.05 and 0<max_position_fraction<=1):raise ValueError("風險參數無效")
    # No assumption that next open will fill at reference price.
    entry=price
    stop=max(.01,entry-2*float(atr))
    risk=entry-stop
    target=entry+2*risk
    qty=int(min(capital*risk_fraction/risk,capital*max_position_fraction/entry))
    return {"reference_entry":round(entry,2),"stop":round(stop,2),
            "target":round(target,2),"atr14":round(float(atr),2),
            "reward_risk":2.0,"shares":qty,"max_risk_budget":round(capital*risk_fraction,2),
            "position_capital":round(qty*entry,2),"holding_days":[10,15,20],
            "note":"收盤價作參考入場價，不保證成交；下一日跳空可能超出預設風險；2 ATR止損、2R目標；單筆風險預算0.5%、持倉上限15%（可調）"}

def simulate_plan(df, signal_idx, plan, days=15, cost_bps=15, slippage_bps=10):
    if days not in (10,15,20):raise ValueError("持有期必須為10、15或20日")
    if signal_idx<0 or signal_idx+days>=len(df):return None
    d=df.iloc[signal_idx+1:signal_idx+days+1]
    entry=float(d.Open.iloc[0]);stop=float(plan["stop"]);target=float(plan["target"])
    if not np.isfinite(entry) or entry<=0 or not (0<stop<target):return None
    reason="到期平倉";exit_price=float(d.Close.iloc[-1]);exit_date=d.index[-1]
    for idx,row in d.iterrows():
        op,hi,lo=float(row.Open),float(row.High),float(row.Low)
        if not all(np.isfinite(x) for x in (op,hi,lo)):return None
        if op<=stop:exit_price=op;reason="跳空止損";exit_date=idx;break
        if op>=target:exit_price=op;reason="跳空止盈";exit_date=idx;break
        if lo<=stop:exit_price=stop;reason="止損優先（同日雙觸亦按止損）";exit_date=idx;break
        if hi>=target:exit_price=target;reason="止盈";exit_date=idx;break
    friction=(cost_bps+slippage_bps)/10000
    gross=exit_price/entry-1
    net=exit_price*(1-friction)/(entry*(1+friction))-1
    return {"signal_date":str(df.index[signal_idx].date()),"entry_date":str(d.index[0].date()),
            "exit_date":str(exit_date.date()),"entry_price":round(entry,4),
            "exit_price":round(exit_price,4),"exit_reason":reason,
            "gross_return_pct":round(gross*100,3),"net_return_pct":round(net*100,3),
            "cost_bps_per_side":cost_bps,"slippage_bps_per_side":slippage_bps}

def summarize_trades(trades):
    t=[x for x in trades if x is not None]
    if not t:return {"n":0,"mean_net_pct":None,"win_rate_pct":None,"profit_factor":None,"max_sequential_drawdown_pct":None}
    x=np.array([v["net_return_pct"]/100 for v in t],dtype=float)
    wins=x[x>0].sum();losses=-x[x<0].sum()
    equity=np.cumprod(1+x);peaks=np.maximum.accumulate(np.r_[1.,equity])[1:]
    return {"n":len(x),"mean_net_pct":round(float(x.mean()*100),2),
            "win_rate_pct":round(float((x>0).mean()*100),1),
            "profit_factor":round(float(wins/losses),2) if losses>0 else None,
            "max_sequential_drawdown_pct":round(float(((equity/peaks)-1).min()*100),2),
            "note":"逐筆非重疊交易權益曲線，不是多股票組合回撤；含假設交易成本與滑價"}
