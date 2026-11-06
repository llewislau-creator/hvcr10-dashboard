"""AlphaLens v2.2: observable-at-close market state diagnostics.

Research classification only; thresholds are hypotheses, not validated forecasts.
"""
import numpy as np
import pandas as pd

def classify_market_state(frame, benchmark_close=None):
    d=frame[["Close","Volume"]].dropna().copy()
    if len(d)<120:
        return {"state":"資料不足","status":"insufficient_data","reason":["至少需要120個完整交易日"]}
    close=d["Close"].astype(float)
    volume=d["Volume"].astype(float)
    mid=close.rolling(20).mean()
    sigma=close.rolling(20).std(ddof=0)
    upper=mid+2*sigma
    lower=mid-2*sigma
    ma50=close.rolling(50).mean()
    ma100=close.rolling(100).mean()
    v20=volume.rolling(20).mean().shift(1)
    down_volume=(close<close.shift(1)) & (volume>1.5*v20)
    relative=None
    if benchmark_close is not None:
        ref=benchmark_close.reindex(d.index).ffill()
        if pd.notna(ref.iloc[-1]) and pd.notna(ref.iloc[-6]) and ref.iloc[-6]>0:
            relative=100*((close.iloc[-1]/close.iloc[-6]-1)-(ref.iloc[-1]/ref.iloc[-6]-1))
    c=float(close.iloc[-1]); m=float(mid.iloc[-1]); lo=float(lower.iloc[-1]); hi=float(upper.iloc[-1])
    band_position=(c-lo)/(hi-lo) if hi>lo else None
    below_mid=c<m
    above_trend=c>float(ma50.iloc[-1])>float(ma100.iloc[-1])
    near_lower=band_position is not None and band_position<=0.15
    heavy_down=bool(down_volume.iloc[-1])
    recent_heavy=int(down_volume.tail(5).sum())
    relative_weak=relative is not None and relative<-2
    previous_inside=bool(close.iloc[-2]<lower.iloc[-2])
    recovered=previous_inside and c>lo
    reasons=[]
    if near_lower:reasons.append("收盤接近或跌穿布林帶下軌")
    if heavy_down:reasons.append("下跌日成交量超過前20日均量1.5倍")
    if recent_heavy>=2:reasons.append("最近5日有至少2次放量下跌")
    if relative_weak:reasons.append("最近5日跑輸基準超過2個百分點")
    if below_mid:reasons.append("收盤低於布林帶中軌")
    # Classification order is explicit and mutually exclusive.
    if near_lower and (heavy_down or recent_heavy>=2) and (relative_weak or c<float(ma50.iloc[-1])):
        state="高風險拋售"
    elif recovered and not heavy_down:
        state="超賣後企穩"
        reasons.append("由下軌外重新收回帶內；尚非底部確認")
    elif above_trend and not relative_weak and not heavy_down:
        state="正常回調" if below_mid else "上升趨勢"
    else:
        state="趨勢轉弱"
    return {"state":state,"status":"research_only","as_of":str(d.index[-1].date()),
        "bollinger":{"window":20,"std":2,"mid":round(m,3),"upper":round(hi,3),
                     "lower":round(lo,3),"position":round(band_position,3) if band_position is not None else None},
        "volume":{"down_day_1_5x":heavy_down,"heavy_down_days_5":recent_heavy,
                  "ratio_to_prior_20d":round(float(volume.iloc[-1]/v20.iloc[-1]),3) if v20.iloc[-1]>0 else None},
        "relative_5d_pct_points":round(float(relative),3) if relative is not None else None,
        "benchmark_available":relative is not None,
        "reasons":reasons or ["未觸發預設弱勢診斷條件"],
        "method":"Daily adjusted close and volume; thresholds provisional; no lookahead; no calibrated predictive claim."}
