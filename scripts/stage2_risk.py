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

def moving_block_bootstrap_ci(values, block_length, repeats=2000, seed=20261106):
    x=np.asarray(values,dtype=float)
    if x.ndim!=1 or not np.all(np.isfinite(x)):raise ValueError('報酬序列無效')
    if block_length<1 or repeats<1:raise ValueError('區塊長度及重抽樣次數必須為正')
    n=len(x)
    if n<block_length or n<2:return None
    rng=np.random.default_rng(seed+block_length)
    k=int(math.ceil(n/block_length))
    starts=rng.integers(0,n-block_length+1,size=(repeats,k))
    offsets=np.arange(block_length)
    idx=(starts[:,:,None]+offsets).reshape(repeats,-1)[:,:n]
    means=x[idx].mean(axis=1)
    return [round(float(v),2) for v in np.percentile(means,[2.5,97.5])]

def block_bootstrap_diagnostic(values, block_length, circular=False, repeats=2000, seed=20261106):
    x=np.asarray(values,dtype=float)
    n=len(x)
    if n<max(2,block_length):return None
    rng=np.random.default_rng(seed+block_length+(1000 if circular else 0))
    count=int(math.ceil(n/block_length))
    starts=rng.integers(0,n if circular else n-block_length+1,size=(repeats,count))
    idx=starts[:,:,None]+np.arange(block_length)
    if circular:idx=idx%n
    means=x[idx.reshape(repeats,-1)[:,:n]].mean(axis=1)
    return {"ci95_pct":[round(float(v),2) for v in np.percentile(means,[2.5,97.5])],
            "bootstrap_mean_pct":round(float(means.mean()),4),
            "original_mean_pct":round(float(x.mean()),4),
            "center_shift_pct":round(float(means.mean()-x.mean()),4)}

def circular_seed_sensitivity(values, block_lengths=(5,10,20), seeds=(20261106,20261107,20261108,20261109,20261110)):
    result={}
    for length in block_lengths:
        runs=[block_bootstrap_diagnostic(values,length,circular=True,seed=seed) for seed in seeds]
        if any(run is None for run in runs):
            result[str(length)]=None
            continue
        widths=[round(run["ci95_pct"][1]-run["ci95_pct"][0],4) for run in runs]
        shifts=[run["center_shift_pct"] for run in runs]
        result[str(length)]={
            "seeds":list(seeds),"ci95_pct_by_seed":[run["ci95_pct"] for run in runs],
            "ci_width_pct_by_seed":widths,"center_shift_pct_by_seed":shifts,
            "positive_lower_count":sum(run["ci95_pct"][0]>0 for run in runs),
            "mean_width_pct":round(float(np.mean(widths)),4),
            "mean_abs_center_shift_pct":round(float(np.mean(np.abs(shifts))),4)}
    return result

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
    boundaries=[start,max(start+1,int(len(d)*.6)),max(start+2,int(len(d)*.8)),len(d)]
    trades=[];excess=[];regimes=[];last_exit=-1
    spy=benchmark_close.reindex(d.index).ffill() if benchmark_close is not None else None
    for i in range(start,len(d)-days):
        if i<=last_exit:continue
        if not (close.iloc[i]>ma50.iloc[i] and momentum.iloc[i]>0 and liquid.iloc[i]):continue
        plan=make_plan(d.iloc[:i+1])
        trade=simulate_plan(d,i,plan,days=days)
        if trade is None:continue
        exit_loc=d.index.get_loc(pd.Timestamp(trade["exit_date"]))
        fold_start=next(a for a,b in zip(boundaries[:-1],boundaries[1:]) if a<=i<b)
        fold_end=next(b for a,b in zip(boundaries[:-1],boundaries[1:]) if a<=i<b)
        entry_loc=d.index.get_loc(pd.Timestamp(trade['entry_date']))
        if not (fold_start<=i<entry_loc<=exit_loc<fold_end):
            continue
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
    out['moving_block_bootstrap']={
        'method':'moving non-circular contiguous trade blocks; percentile CI of mean net return',
        'repeats':2000,'seed':20261106,'block_lengths':[5,10,20],
        'moving_diagnostics':{str(k):block_bootstrap_diagnostic(vals,k) for k in (5,10,20)},
        'circular_diagnostics':{str(k):block_bootstrap_diagnostic(vals,k,circular=True) for k in (5,10,20)},
        'circular_seed_sensitivity':circular_seed_sensitivity(vals),
        'ci95_pct':{str(k):moving_block_bootstrap_ci(vals,k) for k in (5,10,20)},
        'iid_ci95_pct':out['mean_net_bootstrap_ci95_pct'],
        'note':'按單一股票及持有期內的交易時間順序重抽樣；不校正跨股票相關；樣本不足區塊長度時回傳null；區間僅供描述性比較'
    }
    out["regime_results"]={name:summarize_trades([t for t,g in zip(trades,regimes) if g==name]) for name in ("SPY上升趨勢","SPY下降趨勢","市場狀態未知")}
    bear_n=out["regime_results"]["SPY下降趨勢"]["n"]
    out["bear_market_robustness"]={"sample_threshold":30,"sample_adequate":bear_n>=30,
                                   "label":"熊市樣本數達標（績效仍需驗證）" if bear_n>=30 else "熊市穩健性未驗證"}
    out["regime_note"]="以訊號當日SPY相對200交易日前收盤分組；小樣本不應比較優劣"
    trade_keys=[(t['signal_date'],t['entry_date'],t['exit_date']) for t in trades]
    unique_trades=len(set(trade_keys))==len(trade_keys)
    no_overlap=all(pd.Timestamp(a['exit_date'])<pd.Timestamp(b['entry_date']) for a,b in zip(trades,trades[1:]))
    if not unique_trades or not no_overlap:
        raise AssertionError('重複交易或持倉重疊')
    trade_audit=[{"signal_date":t["signal_date"],"entry_date":t["entry_date"],"exit_date":t["exit_date"],
                  "fold":next(j+1 for j,(a,b) in enumerate(zip(boundaries[:-1],boundaries[1:]))
                              if a<=d.index.get_loc(pd.Timestamp(t["signal_date"]))<b)}
                 for t in trades]
    fold_results=[]
    for j in range(3):
        a,b=boundaries[j:j+2]
        subset=[t for t in trades if a<=d.index.get_loc(pd.Timestamp(t["signal_date"]))<b]
        fold_results.append({"fold":j+1,"train_end":str(d.index[a-1].date()),
                             "validation_start":str(d.index[a].date()),
                             "validation_end":str(d.index[b-1].date()),
                             **summarize_trades(subset)})
    out["walk_forward"]={"folds":fold_results,"trade_audit":trade_audit,"total_unique_trades":len(trades),
                         "method":"expanding-history chronological forward evaluation; fixed predeclared rules, no fitted parameters",
                         "trade_reuse":not unique_trades,"no_overlapping_positions":no_overlap}
    out["validation_start_fraction"]=0.4
    out["horizon_days"]=days
    out["method"]="歷史前40%作為固定規則暖機，後60%逐日驗證（非完整walk-forward）；逐日尋找候選並按實際出場日排除重疊；收盤趨勢及流動性篩選；下一日開盤買入；ATR計劃固定於訊號日；假設成本與滑價"
    return out
