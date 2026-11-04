"""HVCR-10 2–4 week swing investment research (not day trading).
All features are observable at signal close; no forward labels used for ranking.
Historical holdout is descriptive, not a calibrated probability or causal alpha.
"""
import math
import numpy as np
import pandas as pd

HORIZONS=(10,15,20)
COST_BPS=15
SLIPPAGE_BPS=10

def swing_research(df, benchmark_close=None):
    d=df[["Open","High","Low","Close","Volume"]].dropna().copy()
    if len(d)<330:raise ValueError("至少需要330個交易日")
    c=d.Close.astype(float);v=d.Volume.astype(float);o=d.Open.astype(float)
    ma20=c.rolling(20).mean();ma50=c.rolling(50).mean();ma100=c.rolling(100).mean()
    r20=c.pct_change(20);r60=c.pct_change(60)
    dollar=(c*v).rolling(20).mean()
    delta=c.diff();up=delta.clip(lower=0).ewm(alpha=1/14,adjust=False,min_periods=14).mean()
    down=(-delta.clip(upper=0)).ewm(alpha=1/14,adjust=False,min_periods=14).mean()
    rsi=100-100/(1+up/down.replace(0,np.nan))
    rsi=rsi.mask((down==0)&(up>0),100).mask((down==0)&(up==0),50)
    ema12=c.ewm(span=12,adjust=False).mean();ema26=c.ewm(span=26,adjust=False).mean()
    macd=ema12-ema26;hist=macd-macd.ewm(span=9,adjust=False).mean()
    rel=None
    if benchmark_close is not None:
        spy=benchmark_close.reindex(d.index).ffill()
        rel=r20-spy.pct_change(20)
    # Five independently interpretable dimensions; no high-volatility eligibility.
    factors={
        "中期趨勢":(c>ma50)&(ma50>ma100),
        "短期動能":(r20>0)&(hist>hist.shift(3)),
        "相對市場強度":(rel>0) if rel is not None else pd.Series(False,index=d.index),
        "健康回調":(c>ma50)&(c<ma20*1.05)&(rsi>=40)&(rsi<=70),
        "量價確認":(c>c.shift(1))&(v>v.rolling(20).mean().shift(1))
    }
    # Missing benchmark must not be silently treated as a failed factor.
    available=4+int(rel is not None)
    factor_frame=pd.DataFrame(factors,index=d.index).fillna(False)
    score=(factor_frame.sum(axis=1)/available*100).round(1)
    eligible=(c>=5)&(dollar>=10e6)
    latest=int(len(d)-1)
    latest_flags={k:(bool(s.iloc[-1]) if k!="相對市場強度" or rel is not None else None) for k,s in factors.items()}
    current_score=float(score.iloc[-1]) if pd.notna(score.iloc[-1]) else None
    signal=("優先研究" if eligible.iloc[-1] and current_score>=80 else
            "觀察名單" if eligible.iloc[-1] and current_score>=60 else "暫不優先")
    # 70/30 chronological split, disjoint event entries, no horizon overlap.
    split=int(len(d)*.7)
    start=max(150,split)
    outcomes={}
    for days in HORIZONS:
        indices=list(range(start,len(d)-days-1,days))
        # Held-out dates are chosen independently of today's score and use only known-at-date features.
        indices=[i for i in indices if eligible.iloc[i] and score.iloc[i]>=60]
        net=[];excess=[]
        for i in indices:
            entry=float(o.iloc[i+1]);exit_=float(c.iloc[i+days])
            if not np.isfinite(entry*exit_) or entry<=0:continue
            friction=(COST_BPS+SLIPPAGE_BPS)/10000
            net_return=(exit_*(1-friction))/(entry*(1+friction))-1
            net.append(net_return)
            if benchmark_close is not None:
                sp=benchmark_close.reindex(d.index).ffill()
                if pd.notna(sp.iloc[i+1]) and pd.notna(sp.iloc[i+days]) and sp.iloc[i+1]>0:
                    excess.append(net_return-(float(sp.iloc[i+days])/float(sp.iloc[i+1])-1))
        n=len(net)
        outcomes[str(days)]={
            "n":n,"mean_net_pct":round(100*float(np.mean(net)),2) if n else None,
            "positive_net_pct":round(100*sum(x>0 for x in net)/n,1) if n else None,
            "mean_excess_spy_pct":round(100*float(np.mean(excess)),2) if excess else None,
            "min_net_pct":round(100*min(net),2) if n else None,
            "note":"70/30時間切分；測試期每隔持有期抽取非重疊候選日；訊號分數>=60；下一交易日開盤買入、期限末收盤賣出；雙邊假設成本與滑價；不是校準機率"
        }
    return {
        "strategy":"2–4星期波段投資","holding_trading_days":[10,15,20],
        "score":current_score,"factors":latest_flags,"factor_count":available,
        "eligible":bool(eligible.iloc[-1]),"signal":signal,
        "liquidity_dollar_m":round(float(dollar.iloc[-1])/1e6,1),
        "momentum_20d_pct":round(float(r20.iloc[-1])*100,2),
        "momentum_60d_pct":round(float(r60.iloc[-1])*100,2),
        "relative_spy_20d_pct":round(float(rel.iloc[-1])*100,2) if rel is not None and pd.notna(rel.iloc[-1]) else None,
        "ma20":round(float(ma20.iloc[-1]),2),"ma50":round(float(ma50.iloc[-1]),2),
        "rsi14":round(float(rsi.iloc[-1]),1) if pd.notna(rsi.iloc[-1]) else None,
        "holdout":outcomes,"cost_bps_per_side":COST_BPS,"slippage_bps_per_side":SLIPPAGE_BPS,
        "score_note":"5維等權觀察分數，不是成功機率；未經校準或證實有超額報酬",
        "selection_note":"收盤價>=5美元、20日平均成交金額>=1000萬美元；不以高波動率為必要條件"
    }
