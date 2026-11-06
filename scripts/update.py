import json, datetime as dt
from pathlib import Path
import numpy as np
import pandas as pd
import yfinance as yf
from rebound_v3 import analyze_frame
from swing_v5 import swing_research
from phase1 import validate_prices, market_context, earnings_event, risk_context

TICKERS = ["NVDA","AMD","TSLA","PLTR","COIN","MSTR","HOOD","SOFI","ROKU","AFRM","MARA","RIOT","UPST","SMCI","GME","APP","CRWD","IONQ","RKLB","HIMS"]
OUT = Path(__file__).resolve().parents[1] / "site" / "data" / "report.json"

def analyze(ticker, spy_close=None):
    df=yf.download(ticker,start="2016-01-01",auto_adjust=True,progress=False,threads=False)
    if df.empty: raise ValueError("no data")
    if isinstance(df.columns,pd.MultiIndex): df.columns=df.columns.get_level_values(0)
    quality=validate_prices(df,ticker)
    if quality["status"]=="blocked":raise ValueError("行情品質檢查不通過："+", ".join(quality["issues"]))
    result=analyze_frame(df)
    result["data_quality"]=quality
    result['swing']=swing_research(df,spy_close)
    try:
        calendar=yf.Ticker(ticker).calendar
        earnings=earnings_event(calendar)
    except Exception as exc:
        earnings=earnings_event(None)
        earnings['note']+='；日曆查詢失敗：'+str(exc)[:120]
    result['earnings']=earnings
    result['phase1_risk']=risk_context(quality,earnings)
    if spy_close is not None:
        aligned=spy_close.reindex(df.index).ffill()
        stock_return=float(df["Close"].iloc[-1]/df["Close"].iloc[-21]-1) if len(df)>21 else None
        spy_return=float(aligned.iloc[-1]/aligned.iloc[-21]-1) if len(df)>21 and pd.notna(aligned.iloc[-21]) and aligned.iloc[-21]>0 else None
        relative=round(100*(stock_return-spy_return),2) if stock_return is not None and spy_return is not None else None
    else:
        relative=None
    result["extra_indicators"]["相對 SPY 20日強弱"]={"value":relative,"observed":relative is not None and relative>0,"unit":"百分點；正值代表跑贏 SPY"}
    result["composite_score_12"]=round(100*(sum(result["conditions"].values())+sum(bool(x["observed"]) for x in result["extra_indicators"].values()))/12,1) if relative is not None else None
    result["composite_note"]="12項等權觀察分數（非反彈機率）；SPY資料不足時不提供12項分數"
    result["ticker"]=ticker
    return result

def main():
    rows=[];errors={}
    try:
        spy=yf.download("SPY",start="2016-01-01",auto_adjust=True,progress=False,threads=False)
        if isinstance(spy.columns,pd.MultiIndex):spy.columns=spy.columns.get_level_values(0)
        spy_close=spy["Close"] if not spy.empty else None
    except Exception as exc:
        spy_close=None
        errors["SPY benchmark"]=str(exc)
    market_data={}
    for symbol in ('SPY','QQQ','^VIX'):
        try:
            market_data[symbol]=spy if symbol=='SPY' else yf.download(symbol,period='2y',auto_adjust=True,progress=False,threads=False)
            if isinstance(market_data[symbol].columns,pd.MultiIndex):market_data[symbol].columns=market_data[symbol].columns.get_level_values(0)
        except Exception as exc:
            market_data[symbol]=None
            errors[symbol+' market']=str(exc)
    market=market_context(market_data['SPY'],market_data['QQQ'],market_data['^VIX'])
    for t in TICKERS:
        try:
            rows.append(analyze(t,spy_close));print("OK",t)
        except Exception as e:
            errors[t]=str(e);print("ERROR",t,e)
    if not rows: raise RuntimeError("No successful downloads; existing report preserved")
    # Publish verified rows only; never reuse stale prices as current observations.
    # Fail closed when coverage is too low, rather than masking a systemic outage.
    minimum_coverage=0.90
    coverage=len(rows)/len(TICKERS)
    if coverage<minimum_coverage:
        raise RuntimeError(f"Insufficient validated coverage ({len(rows)}/{len(TICKERS)}); previous report preserved. Errors: {errors}")
    rows.sort(key=lambda r:(not r["swing"]["eligible"],-(r["swing"]["score"] or 0),-r["swing"]["liquidity_dollar_m"],r["ticker"]))
    payload={"updated_utc":dt.datetime.now(dt.timezone.utc).isoformat(),"universe":"20 隻預選觀察股票，並非全美股","rows":rows,"errors":errors,"method":"六項技術條件至少4項符合；5/10/20交易日內觸及+8%目標；先觸及-5%停損視為失敗；20日非重疊事件；70/30時間切分；Wilson 95%信賴區間。觸價機率不等於實際淨報酬。","model_version":"HVCR-10 rebound v3","model_revision":"v5 swing research preview","investment_horizon":"2–4星期（10/15/20交易日）","ranking_basis":"5維波段投資觀察分數，非預測機率；不以高波動率作硬性篩選","phase1":{"market":market,"earnings_window_days":30,"quality_policy":"blocked股票排除於排行榜；不使用過期數據；缺少財報日期標記unknown"},"coverage":{"expected":len(TICKERS),"validated":len(rows),"pct":round(coverage*100,1),"minimum_pct":minimum_coverage*100,"excluded":[{"ticker":t,"reason":errors[t]} for t in TICKERS if t in errors]}}
    OUT.parent.mkdir(parents=True,exist_ok=True)
    tmp=OUT.with_suffix(".tmp");tmp.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding="utf-8");tmp.replace(OUT)
if __name__=="__main__":main()
