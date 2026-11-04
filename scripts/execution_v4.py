"""Daily-bar, next-open execution research; conservative intrabar tie handling."""
import math

def simulate_ohlc_trade(o,h,l,c,entry_index,horizon=10,target_pct=.08,stop_pct=.05,
                        cost_bps_per_side=15,slippage_bps_per_side=10):
    n=len(o)
    if not 0<=entry_index<n: return None
    entry=float(o[entry_index])
    if not math.isfinite(entry) or entry<=0:return None
    target=entry*(1+target_pct);stop=entry*(1-stop_pct)
    end=min(n-1,entry_index+horizon-1)
    exit_price=None;reason=None;exit_index=None
    for j in range(entry_index,end+1):
        oj,hj,lj=map(float,(o[j],h[j],l[j]))
        if not all(map(math.isfinite,(oj,hj,lj))):return None
        # Stop gaps execute at opening price, not at the unattainable stop.
        if j>entry_index and oj<=stop:
            exit_price=oj;reason="gap_stop";exit_index=j;break
        if j>entry_index and oj>=target:
            exit_price=oj;reason="gap_target";exit_index=j;break
        hit_stop=lj<=stop;hit_target=hj>=target
        if hit_stop:
            exit_price=stop;reason="ambiguous_stop" if hit_target else "stop";exit_index=j;break
        if hit_target:
            exit_price=target;reason="target";exit_index=j;break
    if exit_price is None:
        exit_index=end;exit_price=float(c[end]);reason="time_exit"
    if not math.isfinite(exit_price) or exit_price<=0:return None
    friction=(cost_bps_per_side+slippage_bps_per_side)/10000
    actual_entry=entry*(1+friction);actual_exit=exit_price*(1-friction)
    return {"entry_index":entry_index,"exit_index":exit_index,"entry":round(entry,4),
            "exit":round(exit_price,4),"reason":reason,
            "gross_pct":round(100*(exit_price/entry-1),3),
            "net_pct":round(100*(actual_exit/actual_entry-1),3),
            "holding_days":exit_index-entry_index+1}

def summarize(trades):
    if not trades:return {"n":0,"avg_net_pct":None,"win_rate_pct":None,"profit_factor":None,"max_drawdown_pct":None}
    returns=[t["net_pct"]/100 for t in trades]
    equity=1.;peak=1.;dd=0.
    gains=losses=0.
    for r in returns:
        equity*=1+r;peak=max(peak,equity);dd=max(dd,1-equity/peak)
        gains+=max(r,0);losses+=max(-r,0)
    return {"n":len(trades),"avg_net_pct":round(100*sum(returns)/len(returns),3),
            "win_rate_pct":round(100*sum(x>0 for x in returns)/len(returns),1),
            "profit_factor":round(gains/losses,3) if losses>0 else None,
            "max_drawdown_pct":round(100*dd,2),
            "note":"單一股票逐筆交易複利序列；非多股票投資組合回撤"}
