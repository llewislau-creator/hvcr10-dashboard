"""Phase 1: market context, earnings event risk, and data-quality gates.
No paid APIs. Missing external data stays unknown, never a fabricated safe status.
"""
import datetime as dt
import math
import pandas as pd
import numpy as np

def clean_price_history(df, recent_bars=5):
    """Remove isolated historical incomplete bars; never mask incomplete latest bars.
    Reject recent gaps and retain audit metadata. No forward filling.
    """
    required=["Open","High","Low","Close","Volume"]
    if df is None or df.empty:raise ValueError("沒有行情資料")
    if not set(required).issubset(df.columns):raise ValueError("缺少OHLCV欄位")
    d=df.copy()
    d[required]=d[required].apply(pd.to_numeric,errors="coerce")
    finite=pd.DataFrame(np.isfinite(d[required].to_numpy()),index=d.index,columns=required)
    complete=finite.all(axis=1)
    if not complete.tail(recent_bars).all():
        raise ValueError("最近5個交易日存在缺失或非有限OHLCV資料，不可填補")
    removed=int((~complete).sum())
    cleaned=d.loc[complete].copy()
    if len(cleaned)<330:raise ValueError("清理後不足330個交易日")
    return cleaned,{"historical_incomplete_rows_removed":removed,
                    "raw_rows":len(d),"validated_rows":len(cleaned),
                    "cleaning":"僅刪除較舊不完整交易日；最近5個交易日必須完整；不前向填補"}

def validate_prices(df, ticker="", max_age_calendar_days=7, today=None):
    issues=[]
    if df is None or df.empty:return {"status":"blocked","issues":["沒有行情資料"],"latest_date":None}
    required={"Open","High","Low","Close","Volume"}
    if not required.issubset(df.columns):return {"status":"blocked","issues":["缺少OHLCV欄位"],"latest_date":None}
    d=df[list(required)].copy()
    if d.isna().any().any():issues.append("存在缺失OHLCV資料")
    values=d.apply(pd.to_numeric,errors="coerce")
    if not np.isfinite(values.to_numpy()).all():issues.append("存在非有限數值")
    if ((values[["Open","High","Low","Close"]] <= 0).any().any() or (values["Volume"]<0).any()):
        issues.append("存在非正價格或負成交量")
    if ((values.High<values[["Open","Close","Low"]].max(axis=1))|(values.Low>values[["Open","Close","High"]].min(axis=1))).any():
        issues.append("OHLC價格邏輯不一致")
    idx=pd.to_datetime(df.index)
    if idx.has_duplicates or not idx.is_monotonic_increasing:issues.append("日期重複或未依序排列")
    latest=idx.max().date()
    now=today or dt.datetime.now(dt.timezone.utc).date()
    age=(now-latest).days
    if age>max_age_calendar_days:issues.append(f"資料過期：{age}個日曆日")
    if age<0:issues.append("行情日期在未來")
    # Major jumps are flagged for review, not automatically rejected (splits/news).
    jumps=values.Close.pct_change(fill_method=None).abs()
    if (jumps>.5).any():issues.append("存在單日超過50%價格變動；需核對企業行動")
    blocked=any(("OHLC" in x or "非有限" in x or "非正" in x or "重複" in x or "過期" in x or "未來" in x) for x in issues)
    return {"status":"blocked" if blocked else "warning" if issues else "ok","issues":issues,
            "latest_date":latest.isoformat(),"age_calendar_days":age,"ticker":ticker}

def market_context(spy,qqq,vix):
    def stats(d):
        if d is None or len(d)<210:return None
        c=d["Close"].dropna().astype(float)
        if len(c)<210:return None
        return {"last":round(float(c.iloc[-1]),2),
                "above_ma50":bool(c.iloc[-1]>c.rolling(50).mean().iloc[-1]),
                "above_ma200":bool(c.iloc[-1]>c.rolling(200).mean().iloc[-1]),
                "return_20d_pct":round(float(c.iloc[-1]/c.iloc[-21]-1)*100,2),
                "date":str(c.index[-1].date())}
    s=stats(spy);q=stats(qqq)
    vol=None
    if vix is not None and not vix.empty:
        c=vix["Close"].dropna()
        if len(c):vol={"value":round(float(c.iloc[-1]),2),"date":str(c.index[-1].date())}
    if not s or not q:
        regime="資料不足"
    elif s["above_ma200"] and q["above_ma200"] and s["above_ma50"] and q["above_ma50"]:
        regime="趨勢偏強"
    elif not s["above_ma200"] and not q["above_ma200"]:
        regime="趨勢偏弱"
    else:regime="趨勢分歧"
    return {"regime":regime,"SPY":s,"QQQ":q,"VIX":vol,
            "note":"市場狀態只根據SPY/QQQ均線；VIX顯示風險背景，不直接產生買賣指令"}

def earnings_event(calendar, today=None, window_days=30):
    now=today or dt.datetime.now(dt.timezone.utc).date()
    dates=[]
    if isinstance(calendar,dict):
        for key in ("Earnings Date","EarningsDate","earningsDate"):
            x=calendar.get(key)
            if x is not None:dates=x if isinstance(x,(list,tuple)) else [x];break
    elif isinstance(calendar,pd.DataFrame) and not calendar.empty:
        for key in ("Earnings Date","EarningsDate"):
            if key in calendar.index:
                x=calendar.loc[key]
                dates=list(x.dropna()) if isinstance(x,pd.Series) else [x]
                break
    valid=[]
    for x in dates:
        try:
            t=pd.Timestamp(x)
            if pd.isna(t):continue
            day=t.date()
            if now<=day<=now+dt.timedelta(days=window_days):valid.append(day)
        except (ValueError,TypeError,OverflowError):continue
    if valid:
        d=min(valid)
        return {"status":"upcoming","date":d.isoformat(),"days_until":(d-now).days,
                "note":"來源為Yahoo Finance日曆；日期可能變動，應向公司IR核實"}
    return {"status":"unknown","date":None,"days_until":None,
            "note":"未取得可確認的未來30日財報日期；不代表期間沒有財報"}

def risk_context(quality,earnings):
    if quality["status"]=="blocked":return "資料不合格"
    if earnings["status"]=="upcoming" and earnings["days_until"]<=20:return "持有期內可能有財報"
    if earnings["status"]=="unknown":return "財報日期待確認"
    return "未發現已知近期財報（不保證無其他事件）"
