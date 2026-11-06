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

def backtest_plans(df, days=15, benchmark_close=None):
    """Held-out 30% only; every 'days' trading sessions, no overlapping positions.
    Signal at close: close > 50d MA, 20d return >0, dollar volume >=10m.
    Does not optimize rules or select winners using future outcomes.
    """
    d=df[["Open","High","Low","Close","Volume"]].dropna()
    if len(d)<330:raise ValueError("至少需要330個交易日")
    close=d.Close.astype(float)
    ma50=close.rolling(50).mean()
    momentum=close.pct_change(20)
    liquid=(close*d.Volume).rolling(20).mean()>=1e7
    start=max(200,int(len(d)*.4))
    trades=[];excess=[];regimes=[];last_exit=-1
    spy=benchmark_close.reindex(d.index).ffill() if benchmark_close is not None else None
    for i in range(start,len(d)-days):
        if i<=last_exit:continue
        if not (close.iloc[i]>ma50.iloc[i] and momentum.iloc[i]>0 and liquid.iloc[i]):continue
        plan=make_plan(d.iloc[:i+1])
        trade=simulate_plan(d,i,plan,days=days)
        if trade is None:continue
        exit_loc=d.index.get_loc(pd.Timestamp(trade["exit_date"]))
        last_exit=exit_loc
        if spy is not None and i>=200 and pd.notna(spy.iloc[i]) and pd.notna(spy.iloc[i-200]):
            regime="SPY上升趨勢" if spy.iloc[i]>spy.iloc[i-200] else "SPY下降趨勢"
        else:
            regime="市場狀態未知"
        regimes.append(regime)
        trades.append(trade)
        if spy is not None:
            entry_spy=spy.iloc[i+1]
            # Benchmark exits on the same day as the simulated stock exit.
            exit_loc=d.index.get_loc(pd.Timestamp(trade["exit_date"]))
            exit_spy=spy.iloc[exit_loc]
            if pd.notna(entry_spy) and pd.notna(exit_spy) and entry_spy>0:
                excess.append(trade["net_return_pct"]-(float(exit_spy/entry_spy)-1)*100)
    out=summarize_trades(trades)
    out["mean_excess_spy_pct"]=round(float(np.mean(excess)),2) if excess else None
    vals=np.array([t["net_return_pct"] for t in trades],dtype=float)
    if len(vals)>=2:
        rng=np.random.default_rng(20261106)
        sampled=rng.choice(vals,size=(2000,len(vals)),replace=True).mean(axis=1)
        out["mean_net_bootstrap_ci95_pct"]=[round(float(v),2) for v in np.percentile(sampled,[2.5,97.5])]
    else:
        out["mean_net_bootstrap_ci95_pct"]=None
    out["ci_note"]="固定種子2000次逐筆bootstrap；未校正序列相關及跨股票相關；僅描述性區間，非未來報酬保證"
    out["regime_results"]={name:summarize_trades([t for t,g in zip(trades,regimes) if g==name]) for name in ("SPY上升趨勢","SPY下降趨勢","市場狀態未知")}
    out["regime_note"]="以訊號當日SPY相對200交易日前收盤分組；小樣本不應比較優劣"
    boundaries=[start,max(start+1,int(len(d)*.6)),max(start+2,int(len(d)*.8)),len(d)]
    fold_results=[]
    for j in range(3):
        a,b=boundaries[j:j+2]
        subset=[t for t in trades if a<=d.index.get_loc(pd.Timestamp(t["signal_date"]))<b]
        fold_results.append({"fold":j+1,"train_end":str(d.index[a-1].date()),
                             "validation_start":str(d.index[a].date()),
                             "validation_end":str(d.index[b-1].date()),
                             **summarize_trades(subset)})
    out["walk_forward"]={"folds":fold_results,"total_unique_trades":len(trades),
                         "method":"expanding-history chronological forward evaluation; fixed predeclared rules, no fitted parameters",
                         "trade_reuse":False}
    out["validation_start_fraction"]=0.4
    out["horizon_days"]=days
    out["method"]="歷史前40%作為固定規則暖機，後60%逐日驗證（非完整walk-forward）；逐日尋找候選並按實際出場日排除重疊；收盤趨勢及流動性篩選；下一日開盤買入；ATR計劃固定於訊號日；假設成本與滑價"
    return out
